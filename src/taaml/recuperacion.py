"""Recuperación de fragmentos: de toda la base de conocimiento, solo lo relevante para cada pregunta.

La base completa tiene unos 316.800 tokens: cabe en el contexto de Gemini, pero cuesta unas 80 veces más por pregunta que 12 fragmentos. Cada fragmento (data/4_curaduria/chunks.jsonl) tiene
un embedding (un vector que representa su significado) calculado con nomic-embed-text-v2-moe en Ollama. Para una
pregunta se calcula su embedding y se buscan los fragmentos más parecidos (similitud del coseno) en una base vectorial (Chroma). Esos van al prompt.

Si la carpeta de Chroma no existe o no corresponde a los fragmentos actuales, se busca en la matriz de vectores del .npz (mismo resultado).
Si Ollama no responde, se usa una búsqueda por palabras (menos precisa, pero el asistente sigue funcionando).
"""
import json
import math
import re
import time
import urllib.request
from functools import lru_cache
from pathlib import Path

import chromadb
import numpy as np

from taaml.sinonimos import ampliar_consulta

CURADURIA = Path(__file__).resolve().parents[2] / "data" / "4_curaduria"
CHUNKS = CURADURIA / "chunks.jsonl"
INDICE = CURADURIA / "indice_embeddings.npz"  # caché de vectores y respaldo de Chroma
CHROMA = CURADURIA / "chroma"  # base vectorial persistente; se regenera con scripts/07_construir_indice.py
COLECCION = "celsia"
OLLAMA_EMBED = "http://localhost:11434/api/embed"
MODELO_EMBEDDINGS = "nomic-embed-text-v2-moe"
FRAGMENTOS_POR_DEFECTO = 12  # con 5, 8, 12 y 16 se midió 71, 74, 81 y 81 % de aciertos (scripts/10_evaluar_recuperacion.py)


def embeddings(textos: list[str], tipo: str, timeout: int = 300) -> np.ndarray:
    """Embeddings normalizados. `tipo` es «document» o «query»: el modelo espera ese prefijo."""
    cuerpo = {"model": MODELO_EMBEDDINGS, "input": [f"search_{tipo}: {t}" for t in textos]}
    req = urllib.request.Request(OLLAMA_EMBED, data=json.dumps(cuerpo).encode("utf-8"), headers={"Content-Type": "application/json"})
    vectores = np.array(json.load(urllib.request.urlopen(req, timeout=timeout))["embeddings"], dtype=np.float32)
    return vectores / np.linalg.norm(vectores, axis=1, keepdims=True)


@lru_cache(maxsize=1)
def cargar_fragmentos() -> list[dict]:
    return [json.loads(ln) for ln in CHUNKS.read_text(encoding="utf-8").splitlines()]


@lru_cache(maxsize=1)
def _matriz() -> np.ndarray | None:
    """Vectores del índice, solo si corresponden a los fragmentos actuales (mismo orden e identificadores)."""
    if not INDICE.exists():
        return None
    datos = np.load(INDICE, allow_pickle=False)
    ids = [f["chunk_id"] for f in cargar_fragmentos()]
    return datos["vectores"] if list(datos["ids"]) == ids else None


def _cliente_chroma():
    return chromadb.PersistentClient(path=str(CHROMA), settings=chromadb.Settings(anonymized_telemetry=False))  # sin telemetría: no sale nada a terceros


def construir_chroma(ids: list[str], vectores: np.ndarray, metadatos: list[dict]) -> None:
    """Crea (o reemplaza) la colección de Chroma con los vectores ya calculados; el texto sigue en chunks.jsonl."""
    cliente = _cliente_chroma()
    if COLECCION in [c.name if hasattr(c, "name") else c for c in cliente.list_collections()]:
        cliente.delete_collection(COLECCION)
    coleccion = cliente.create_collection(COLECCION, configuration={"hnsw": {"space": "cosine"}})
    for n in range(0, len(ids), 500):  # Chroma limita el tamaño de cada lote
        coleccion.add(ids=ids[n:n + 500], embeddings=vectores[n:n + 500].tolist(), metadatas=metadatos[n:n + 500])
    _coleccion.cache_clear()


@lru_cache(maxsize=1)
def _coleccion():
    """La colección de Chroma, solo si existe y tiene exactamente los fragmentos actuales (como `_matriz`)."""
    if not CHROMA.exists():
        return None
    try:
        coleccion = _cliente_chroma().get_collection(COLECCION)
        return coleccion if set(coleccion.get(include=[])["ids"]) == {f["chunk_id"] for f in cargar_fragmentos()} else None
    except Exception:  # noqa: BLE001  colección ausente o dañada: se usa la matriz
        return None


def almacen_vectorial() -> str:
    """Dónde se busca por significado hoy: «chroma», «numpy» (matriz del .npz) o «ninguno»."""
    return "chroma" if _coleccion() is not None else "numpy" if _matriz() is not None else "ninguno"


def _similitudes(vector: np.ndarray) -> np.ndarray:
    """Similitud del coseno de la pregunta con cada fragmento, en el orden de chunks.jsonl; usa Chroma si está vigente y si no la matriz."""
    coleccion = _coleccion()
    if coleccion is None:
        return _matriz() @ vector
    respuesta = coleccion.query(query_embeddings=[vector.tolist()], n_results=coleccion.count(), include=["distances"])
    por_id = dict(zip(respuesta["ids"][0], respuesta["distances"][0]))
    return np.array([1.0 - por_id[f["chunk_id"]] for f in cargar_fragmentos()])


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


def _buscar(pregunta: str, k: int, metodo: str) -> tuple[list[dict], str]:
    """Los k fragmentos más relevantes para la pregunta, del más al menos parecido, con su puntaje, y el método con el que se encontraron.

    metodo: «embeddings» (significado), «palabras» (coincidencia de palabras) o «hibrido» (las dos combinadas por posición).
    «auto» usa embeddings (en la medición superó al híbrido); si no hay índice vigente o Ollama no responde, cae a palabras.
    """
    fragmentos, matriz = cargar_fragmentos(), _matriz()
    pregunta = ampliar_consulta(pregunta)  # agrega el vocabulario del sitio a ciertos temas (ver sinonimos.py)
    por_palabras = _puntajes_por_palabras(pregunta) if metodo in ("palabras", "hibrido") else None
    try:
        if metodo == "palabras" or matriz is None:
            raise RuntimeError("sin embeddings")
        por_significado = _similitudes(embeddings([pregunta], "query")[0])
        if metodo in ("embeddings", "auto"):
            puntajes, metodo = por_significado, "embeddings"
        else:
            puntajes, metodo = _por_rango(por_significado) + _por_rango(por_palabras), "hibrido"
    except Exception:  # noqa: BLE001  Ollama apagado, índice desactualizado o método forzado
        if por_palabras is None:
            por_palabras = _puntajes_por_palabras(pregunta)
        puntajes, metodo = por_palabras, "palabras"
    orden = np.argsort(-puntajes)[:k]
    return [{**fragmentos[i], "puntaje": float(puntajes[i]), "metodo": metodo} for i in orden], metodo


def buscar(pregunta: str, k: int = FRAGMENTOS_POR_DEFECTO, metodo: str = "auto") -> list[dict]:
    """Los k fragmentos más relevantes para la pregunta, del más al menos parecido, con su puntaje."""
    fragmentos, _ = _buscar(pregunta, k, metodo)
    return fragmentos


def recuperar(pregunta: str, k: int = FRAGMENTOS_POR_DEFECTO, metodo: str = "auto") -> tuple[list[dict], dict]:
    """Recuperación con métricas para la app: devuelve `(fragmentos, métricas)`.

    Las métricas miden esta misma recuperación: cuántos fragmentos se encontraron (`encontrados`), con qué
    `metodo` y cuánto tardó (`tiempo_ms`, con `time.perf_counter` en la misma pasada: no se vuelve a buscar).
    Si la recuperación falla, el error viaja en `error` y `encontrados` queda en 0; el tiempo se sigue midiendo.
    """
    inicio = time.perf_counter()
    error: Exception | None = None
    fragmentos, metodo = [], "error"
    try:
        fragmentos, metodo = _buscar(pregunta, k, metodo)
    except Exception as e:  # noqa: BLE001  el fallo viaja en las métricas, no se esconde
        error = e
    fin = time.perf_counter()
    metricas: dict = {"k": k, "encontrados": len(fragmentos), "metodo": metodo, "tiempo_ms": round((fin - inicio) * 1000, 2)}
    if error is not None:
        metricas["error"] = f"{type(error).__name__} {error}"
    return fragmentos, metricas


def formatear_contexto(resultados: list[dict]) -> str:
    """Arma el contexto del prompt: cada fragmento con su documento, categoría y fuente."""
    # un fragmento no puede cerrar el bloque <contexto> del prompt (defensa contra inyección indirecta)
    limpio = lambda t: t.replace("</contexto>", "").replace("<contexto>", "")  # noqa: E731
    bloques = [f"=== {r['documento']} | categoría: {r['categoria']} | región: {r['region']} | fuente: {r['fuente']} ===\n{limpio(r['texto'])}"
               for r in resultados]
    return "\n\n".join(bloques)
