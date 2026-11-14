"""Recuperación de fragmentos: de toda la base de conocimiento, solo lo relevante para cada pregunta.

La base completa tiene unos 316.800 tokens: cabe en el contexto de Gemini, pero cuesta unas 80 veces más por pregunta que 12 fragmentos. Cada fragmento (data/4_curaduria/chunks.jsonl) tiene
un embedding (un vector que representa su significado) calculado con nomic-embed-text-v2-moe en Ollama. Para una
pregunta se calcula su embedding y se buscan los fragmentos más parecidos (similitud del coseno) en una base vectorial (Qdrant). Esos van al prompt.

Si la carpeta de Qdrant no existe, está abierta por otro proceso o no corresponde a los fragmentos actuales, se busca en la matriz de vectores del .npz (mismo resultado).
Si Ollama no responde, se usa una búsqueda por palabras (menos precisa, pero el asistente sigue funcionando).
"""

import atexit
import json
import math
import os
import re
import time
import urllib.request
from functools import lru_cache
from uuid import NAMESPACE_URL, uuid5
from pathlib import Path

import numpy as np
from qdrant_client import QdrantClient, models

from taaml.sanitizar import quitar_invisibles
from taaml.sinonimos import ampliar_consulta

CURADURIA = Path(
    os.environ.get("TAAML_CURADURIA") or Path(__file__).resolve().parents[2] / "data" / "4_curaduria"
)  # TAAML_CURADURIA: carpeta alterna para ensayar otro índice sin tocar el vigente
CHUNKS = CURADURIA / "chunks.jsonl"
INDICE = CURADURIA / "indice_embeddings.npz"  # caché de vectores y respaldo de Qdrant
QDRANT = (
    CURADURIA / "qdrant"
)  # base vectorial Qdrant (modo local, archivos en disco, sin servidor); se regenera con scripts/07_construir_indice.py
COLECCION = "celsia"
OLLAMA_EMBED = "http://localhost:11434/api/embed"
MODELO_EMBEDDINGS = "nomic-embed-text-v2-moe"
FRAGMENTOS_POR_DEFECTO = (
    12  # con 5, 8, 12 y 16 se midió 71, 74, 81 y 81 % de aciertos (scripts/10_evaluar_recuperacion.py)
)


def embeddings(textos: list[str], tipo: str, timeout: int = 300) -> np.ndarray:
    """Embeddings normalizados. `tipo` es «document» o «query»: el modelo espera ese prefijo."""
    # keep_alive: Ollama descarga el modelo si pasan 5 minutos sin usarlo y la siguiente búsqueda tarda ~7 s en cargarlo; así queda en memoria
    cuerpo = {"model": MODELO_EMBEDDINGS, "input": [f"search_{tipo}: {t}" for t in textos], "keep_alive": "30m"}
    req = urllib.request.Request(
        OLLAMA_EMBED, data=json.dumps(cuerpo).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    vectores = np.array(json.load(urllib.request.urlopen(req, timeout=timeout))["embeddings"], dtype=np.float32)
    return vectores / np.linalg.norm(vectores, axis=1, keepdims=True)


@lru_cache(maxsize=1)
def cargar_fragmentos() -> list[dict]:
    """Los fragmentos del corpus (`chunks.jsonl`), en su orden, con documento, categoría, región, fuente y texto."""
    return [json.loads(ln) for ln in CHUNKS.read_text(encoding="utf-8").splitlines()]


@lru_cache(maxsize=1)
def _matriz() -> np.ndarray | None:
    """Vectores del índice, solo si corresponden a los fragmentos actuales (mismo orden e identificadores)."""
    if not INDICE.exists():
        return None
    datos = np.load(INDICE, allow_pickle=False)
    ids = [f["chunk_id"] for f in cargar_fragmentos()]
    return datos["vectores"] if list(datos["ids"]) == ids else None


@lru_cache(maxsize=1)
def _cliente_qdrant() -> QdrantClient:
    """Cliente de Qdrant en modo local. Es uno solo por proceso: el modo local bloquea la carpeta, así que un segundo proceso no puede abrirla
    y la búsqueda cae a la matriz (ver `_coleccion`)."""
    cliente = QdrantClient(path=str(QDRANT))
    atexit.register(
        cliente.close
    )  # cierra limpio al salir (si no, su destructor falla al apagar Python y ensucia la terminal)
    return cliente


def _id_punto(chunk_id: str) -> str:
    """Qdrant exige ids numéricos o UUID: el identificador del fragmento se convierte en un UUID estable (y el original va en el payload)."""
    return str(uuid5(NAMESPACE_URL, chunk_id))


def _versiones(cliente: QdrantClient) -> list[int]:
    """Números de versión de las colecciones `celsia_v<n>` que hay en disco, de menor a mayor."""
    nombres = [c.name for c in cliente.get_collections().collections]
    return sorted(
        int(n.removeprefix(f"{COLECCION}_v"))
        for n in nombres
        if n.startswith(f"{COLECCION}_v") and n.removeprefix(f"{COLECCION}_v").isdigit()
    )


def _apuntar_alias(cliente: QdrantClient, coleccion: str) -> None:
    """Cambia el alias `celsia` a `coleccion` en una sola operación: quien consulta ve la versión vieja o la nueva, nunca un estado intermedio."""
    operaciones: list = []
    if any(a.alias_name == COLECCION for a in cliente.get_aliases().aliases):
        operaciones.append(models.DeleteAliasOperation(delete_alias=models.DeleteAlias(alias_name=COLECCION)))
    operaciones.append(
        models.CreateAliasOperation(create_alias=models.CreateAlias(collection_name=coleccion, alias_name=COLECCION))
    )
    cliente.update_collection_aliases(change_aliases_operations=operaciones)


def construir_qdrant(ids: list[str], vectores: np.ndarray, metadatos: list[dict]) -> str:
    """Migración blue/green: carga una colección nueva (`celsia_v<n>`), la valida y solo entonces mueve el alias `celsia` hacia ella.

    La versión en uso (blue) sigue respondiendo mientras la nueva (green) se carga; si la validación falla, la nueva se borra y el alias no se toca.
    Se conserva la versión anterior para poder volver atrás con `revertir_qdrant`; las más viejas se borran. Devuelve el nombre de la colección nueva.
    """
    cliente = _cliente_qdrant()
    versiones = _versiones(cliente)
    nueva = f"{COLECCION}_v{(versiones[-1] if versiones else 0) + 1}"
    cliente.create_collection(
        nueva, vectors_config=models.VectorParams(size=int(vectores.shape[1]), distance=models.Distance.COSINE)
    )
    for n in range(0, len(ids), 500):
        lote = zip(ids[n : n + 500], vectores[n : n + 500], metadatos[n : n + 500])
        cliente.upsert(
            nueva,
            points=[
                models.PointStruct(id=_id_punto(i), vector=v.tolist(), payload={"chunk_id": i, **m}) for i, v, m in lote
            ],
        )
    cuenta = cliente.count(nueva).count
    mejor = (
        cliente.query_points(nueva, query=vectores[0].tolist(), limit=1, with_payload=False).points[0]
        if cuenta
        else None
    )
    if cuenta != len(ids) or (
        mejor is not None and abs(mejor.score - 1.0) > 1e-3
    ):  # tiene todos los puntos y un fragmento se encuentra a sí mismo con similitud 1
        cliente.delete_collection(nueva)
        raise RuntimeError(
            f"La colección {nueva} no pasó la validación ({cuenta} de {len(ids)} puntos); el alias {COLECCION} sigue apuntando a la versión anterior."
        )
    if COLECCION in [
        c.name for c in cliente.get_collections().collections
    ]:  # índice del formato anterior: una colección con el nombre del alias, que no puede convivir con él
        cliente.delete_collection(COLECCION)
    _apuntar_alias(cliente, nueva)
    for viejo in versiones[:-1]:  # se queda la inmediata anterior (para revertir) y se borran las más antiguas
        cliente.delete_collection(f"{COLECCION}_v{viejo}")
    _coleccion.cache_clear()
    return nueva


def revertir_qdrant() -> str:
    """Vuelve a la versión anterior de la colección (el paso de vuelta de la migración blue/green). Devuelve su nombre."""
    cliente = _cliente_qdrant()
    en_uso = next((a.collection_name for a in cliente.get_aliases().aliases if a.alias_name == COLECCION), None)
    anteriores = [v for v in _versiones(cliente) if f"{COLECCION}_v{v}" != en_uso]
    if not anteriores:
        raise RuntimeError("No hay una versión anterior a la que volver.")
    destino = f"{COLECCION}_v{anteriores[-1]}"
    _apuntar_alias(cliente, destino)
    _coleccion.cache_clear()
    return destino


@lru_cache(maxsize=1)
def _coleccion() -> QdrantClient | None:
    """El cliente de Qdrant, solo si la colección existe y tiene exactamente los fragmentos actuales (como `_matriz`)."""
    if not QDRANT.exists():
        return None
    try:
        cliente = _cliente_qdrant()
        if not cliente.collection_exists(COLECCION):
            return None
        puntos, _ = cliente.scroll(COLECCION, limit=100_000, with_payload=["chunk_id"], with_vectors=False)
        return (
            cliente
            if {(p.payload or {})["chunk_id"] for p in puntos} == {f["chunk_id"] for f in cargar_fragmentos()}
            else None
        )
    except Exception:  # noqa: BLE001  colección ausente, dañada o carpeta abierta por otro proceso: se usa la matriz
        return None


def almacen_vectorial() -> str:
    """Dónde se busca por significado hoy: «qdrant», «numpy» (matriz del .npz) o «ninguno»."""
    return "qdrant" if _coleccion() is not None else "numpy" if _matriz() is not None else "ninguno"


CAMPOS_FILTRABLES = ("categoria", "region")  # campos del payload por los que se puede filtrar


def _mascara(filtro: dict | None) -> np.ndarray | None:
    """True para los fragmentos que cumplen el filtro (todos los campos pedidos iguales), en el orden de chunks.jsonl; None si no hay filtro."""
    if not filtro:
        return None
    desconocidos = set(filtro) - set(CAMPOS_FILTRABLES)
    if desconocidos:
        raise ValueError(f"No se puede filtrar por {sorted(desconocidos)}; los campos son {list(CAMPOS_FILTRABLES)}")
    return np.array([all(f[campo] == valor for campo, valor in filtro.items()) for f in cargar_fragmentos()])


def _similitudes(vector: np.ndarray, filtro: dict | None = None) -> np.ndarray:
    """Similitud del coseno de la pregunta con cada fragmento, en el orden de chunks.jsonl; usa Qdrant si está vigente y si no la matriz.

    Con `filtro` (por ejemplo {"categoria": "sedes"}) los fragmentos que no lo cumplen quedan en -inf. En Qdrant el filtro se aplica **antes** de comparar
    (pre-filtrado: solo se comparan los puntos cuyo payload lo cumple), así que `limit` no se gasta en puntos que luego se descartarían.
    """
    mascara = _mascara(filtro)
    cliente = _coleccion()
    if cliente is None:
        puntajes = _matriz() @ vector
        return puntajes if mascara is None else np.where(mascara, puntajes, -np.inf)
    condiciones = [
        models.FieldCondition(key=campo, match=models.MatchValue(value=valor))
        for campo, valor in (filtro or {}).items()
    ]
    cuantos = int(mascara.sum()) if mascara is not None else cliente.count(COLECCION).count
    respuesta = cliente.query_points(
        COLECCION,
        query=vector.tolist(),
        limit=max(cuantos, 1),
        with_payload=["chunk_id"],
        query_filter=models.Filter(must=condiciones) if condiciones else None,
    )
    por_id = {(p.payload or {})["chunk_id"]: p.score for p in respuesta.points}
    return np.array([por_id.get(f["chunk_id"], -np.inf) for f in cargar_fragmentos()])


def _palabras(texto: str) -> list[str]:
    return re.findall(r"[a-záéíóúñü0-9]{3,}", texto.lower())


@lru_cache(maxsize=1)
def _idf() -> dict[str, float]:
    docs = [set(_palabras(f["texto"])) for f in cargar_fragmentos()]
    n = len(docs)
    conteo: dict[str, int] = {}
    for d in docs:
        for p in d:
            conteo[p] = conteo.get(p, 0) + 1
    return {p: math.log(1 + n / c) for p, c in conteo.items()}


def _puntajes_por_palabras(pregunta: str) -> np.ndarray:
    """Respaldo sin embeddings: suma del peso (idf) de las palabras de la pregunta que aparecen en el fragmento."""
    consulta, idf = set(_palabras(pregunta)), _idf()
    return np.array([sum(idf.get(p, 0.0) for p in consulta & set(_palabras(f["texto"]))) for f in cargar_fragmentos()])


def _por_rango(puntajes: np.ndarray) -> np.ndarray:
    """Convierte puntajes en un aporte decreciente por posición (1/(60+posición)), para combinar métodos distintos."""
    rangos = np.empty(len(puntajes))
    rangos[np.argsort(-puntajes)] = np.arange(len(puntajes))
    return 1.0 / (60 + rangos)


def _buscar(pregunta: str, k: int, metodo: str, filtro: dict | None = None) -> tuple[list[dict], str]:
    """Los k fragmentos más relevantes para la pregunta, del más al menos parecido, con su puntaje, y el método con el que se encontraron.

    metodo: «embeddings» (significado), «palabras» (coincidencia de palabras) o «hibrido» (las dos combinadas por posición).
    filtro: opcional, por campos del payload (`categoria`, `region`); solo se devuelven fragmentos que lo cumplen (pueden ser menos de k).
    «auto» usa embeddings (en la medición superó al híbrido); si no hay índice vigente o Ollama no responde, cae a palabras.
    """
    fragmentos, matriz = cargar_fragmentos(), _matriz()
    pregunta = ampliar_consulta(pregunta)  # agrega el vocabulario del sitio a ciertos temas (ver sinonimos.py)
    mascara = _mascara(filtro)
    por_palabras = _puntajes_por_palabras(pregunta) if metodo in ("palabras", "hibrido") else None
    try:
        if metodo == "palabras" or matriz is None:
            raise RuntimeError("sin embeddings")
        por_significado = _similitudes(embeddings([pregunta], "query")[0], filtro)
        if metodo in ("embeddings", "auto"):
            puntajes, metodo = por_significado, "embeddings"
        else:
            lexico = por_palabras if por_palabras is not None else _puntajes_por_palabras(pregunta)
            puntajes, metodo = (
                _por_rango(por_significado)
                + _por_rango(lexico if mascara is None else np.where(mascara, lexico, -np.inf)),
                "hibrido",
            )
            puntajes = puntajes if mascara is None else np.where(mascara, puntajes, -np.inf)
    except Exception:  # noqa: BLE001  Ollama apagado, índice desactualizado o método forzado
        if por_palabras is None:
            por_palabras = _puntajes_por_palabras(pregunta)
        puntajes, metodo = (por_palabras if mascara is None else np.where(mascara, por_palabras, -np.inf)), "palabras"
    orden = [
        i for i in np.argsort(-puntajes)[:k] if np.isfinite(puntajes[i])
    ]  # un fragmento filtrado (-inf) nunca se devuelve
    return [{**fragmentos[i], "puntaje": float(puntajes[i]), "metodo": metodo} for i in orden], metodo


def buscar(
    pregunta: str, k: int = FRAGMENTOS_POR_DEFECTO, metodo: str = "auto", filtro: dict | None = None
) -> list[dict]:
    """Los k fragmentos más relevantes para la pregunta, del más al menos parecido, con su puntaje. `filtro` opcional: {"categoria": ...} y/o {"region": ...}."""
    fragmentos, _ = _buscar(pregunta, k, metodo, filtro)
    return fragmentos


def recuperar(pregunta: str, k: int = FRAGMENTOS_POR_DEFECTO, metodo: str = "auto") -> tuple[list[dict], dict]:
    """Recuperación con métricas para la app: devuelve `(fragmentos, métricas)`.

    Las métricas miden esta misma recuperación: cuántos fragmentos se encontraron (`encontrados`), con qué
    `metodo` y cuánto tardó (`tiempo_ms`, con `time.perf_counter` en la misma pasada: no se vuelve a buscar).
    Si la recuperación falla, el error viaja en `error` y `encontrados` queda en 0; el tiempo se sigue midiendo.
    """
    inicio = time.perf_counter()
    error: Exception | None = None
    fragmentos, usado = [], "error"
    try:
        fragmentos, usado = _buscar(pregunta, k, metodo)
    except Exception as e:  # noqa: BLE001  el fallo viaja en las métricas, no se esconde
        error = e
    fin = time.perf_counter()
    metricas: dict = {
        "k": k,
        "encontrados": len(fragmentos),
        "metodo": usado,
        "tiempo_ms": round((fin - inicio) * 1000, 2),
    }
    if error is not None:
        metricas["error"] = f"{type(error).__name__} {error}"
    return fragmentos, metricas


def formatear_contexto(resultados: list[dict]) -> str:
    """Arma el contexto del prompt: cada fragmento con su documento, categoría y fuente."""
    # un fragmento no puede cerrar el bloque <contexto> del prompt ni esconder órdenes con caracteres invisibles (defensa contra inyección indirecta)
    limpio = lambda t: quitar_invisibles(t).replace("</contexto>", "").replace("<contexto>", "")  # noqa: E731
    bloques = [
        f"=== {r['documento']} | categoría: {r['categoria']} | región: {r['region']} | fuente: {r['fuente']} ===\n{limpio(r['texto'])}"
        for r in resultados
    ]
    return "\n\n".join(bloques)
