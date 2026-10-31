"""Continuidad de la demo (spec 003): si el modelo no responde, se prueba otro; si ninguno responde, se muestra la respuesta ya evaluada.

No cambia lo que dice ningún modelo. Solo decide a quién llamar cuando hay una falla del proveedor (cuota, límite, servidor caído o falta de clave)
y dice siempre qué pasó, para que una respuesta de respaldo nunca parezca una respuesta nueva.
"""
import csv
import os
import re
import unicodedata
from pathlib import Path

from taaml.recuperacion import cargar_fragmentos

ROOT = Path(__file__).resolve().parents[2]
RESULTADOS = ROOT / "docs" / "2 - Conjunto de prueba" / "resultados" / "resultados_gemini-gemini-3.5-flash_rag_v3.csv"
MODELO_DEEPSEEK = "deepseek-flash"
MODELO_LOCAL = "ollama:llama3.2"  # gratis y sin red, pero 3.000 millones de parámetros en CPU: lento y menos preciso
# patrones precisos: un «429» o «falta» suelto dentro de otro mensaje no debe esconder un error de código.
# 401/403 entran porque una clave inválida o sin permisos es una falla del proveedor, no del código:
# sin ellos, la app mostraba el 401 y no probaba DeepSeek ni el modelo local.
MARCAS_DE_FALLA = re.compile(
    r"resource_exhausted|\b(401|403|429|503)\b|unauthenticated|unauthorized|permission[_ ]denied|"
    r"api[_ ]?key[_ ]?(not valid|invalid)|invalid api key|quota|cuota|falta \w+_api_key|"
    r"timed out|timeout|connecterror|connectionerror|overloaded",
    re.I,
)


def es_falla_del_proveedor(error: Exception) -> bool:
    """True si el error viene del proveedor o de la conexión (vale la pena probar otro modelo); False si es un error del código."""
    return bool(MARCAS_DE_FALLA.search(f"{type(error).__name__} {error}"))


def cadena_de_modelos(elegido: str) -> list[str]:
    """El modelo elegido, luego DeepSeek (solo si hay clave) y por último el local."""
    if elegido == MODELO_LOCAL:  # el local es el último recurso: no hay nada después
        return [elegido]
    cadena = [elegido]
    if os.environ.get("DEEPSEEK_API_KEY") and not elegido.startswith("deepseek"):
        cadena.append(MODELO_DEEPSEEK)
    return cadena + [MODELO_LOCAL]


def con_respaldo(funcion, elegido: str):
    """Llama `funcion(modelo)` con cada modelo de la cadena hasta que uno responde.

    Devuelve `(resultado, modelo_usado, avisos)`. Si falla por algo que no es del proveedor, el error se propaga; si fallan todos, se propaga el último.
    """
    avisos, ultimo = [], None
    for modelo in cadena_de_modelos(elegido):
        try:
            resultado = funcion(modelo)
        except Exception as e:  # noqa: BLE001
            if not es_falla_del_proveedor(e):
                raise
            avisos.append(f"{modelo} no respondió ({str(e)[:80]})")
            ultimo = e
            continue
        if avisos:
            avisos.append(f"se usó {modelo}" + (" (modelo local: más lento y menos preciso)" if modelo == MODELO_LOCAL else ""))
        return resultado, modelo, avisos
    raise ultimo


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")).strip()


def preguntas_guardadas() -> list[str]:
    """Las preguntas del conjunto de prueba que tienen respuesta guardada."""
    if not RESULTADOS.exists():
        return []
    return [f["pregunta"] for f in csv.DictReader(RESULTADOS.open(encoding="utf-8-sig", newline="")) if f["respuesta"] and not f["error"]]


def respuesta_guardada(pregunta: str) -> tuple[str, list[dict]] | None:
    """La respuesta de la evaluación (v3) a una pregunta del conjunto de prueba, con los fragmentos que se usaron; None si no hay."""
    if not RESULTADOS.exists():
        return None
    objetivo = _normalizar(pregunta)
    for fila in csv.DictReader(RESULTADOS.open(encoding="utf-8-sig", newline="")):
        if fila["respuesta"] and not fila["error"] and _normalizar(fila["pregunta"]) == objetivo:
            por_id = {f["chunk_id"]: f for f in cargar_fragmentos()}
            return fila["respuesta"], [por_id[i] for i in fila["fragmentos"].split() if i in por_id]
    return None
