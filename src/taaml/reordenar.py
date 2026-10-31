"""Reordenamiento (re-ranking) de fragmentos: se recuperan más candidatos y un modelo elige los mejores.

El buscador por significado (recuperacion.py) deja a veces el fragmento correcto fuera de los k primeros. Aquí se recuperan
`candidatos` (por defecto 30) y se le pide a un modelo barato que los ordene por utilidad para la pregunta; solo los k mejores
van al prompt. Cuesta una llamada más por pregunta, así que es opcional y está apagado por defecto.
Si el modelo falla o responde algo inválido, se devuelve el orden original: reordenar nunca deja sin contexto al asistente.
"""
import json
import re

from langchain_core.messages import HumanMessage

from taaml.prompts import leer_prompt
from taaml.recuperacion import FRAGMENTOS_POR_DEFECTO, recuperar

MODELO_REORDENADOR = "gemini-3.5-flash-lite"  # barato y rápido: solo ordena, no responde
MODELO_REORDENADOR_DEEPSEEK = "deepseek-flash"  # el mismo papel cuando el asistente trabaja con DeepSeek
PROMPT_REORDENADOR = "v1_reordenar.md"  # versionado en prompts/, como los demás
CANDIDATOS_POR_DEFECTO = 30
LARGO_VISTA = 400  # caracteres de cada candidato que ve el reordenador




def parsear_orden(texto: str, total: int) -> list[int]:
    """Posiciones (desde 0) que el modelo eligió, sin repetidas ni fuera de rango. Lista vacía si no se puede leer."""
    try:
        numeros = json.loads(re.search(r"\{.*\}", texto, re.S).group(0))["orden"]
    except Exception:  # noqa: BLE001  cualquier respuesta ilegible equivale a «sin orden»
        return []
    vistos: list[int] = []
    for n in numeros:
        if isinstance(n, int) and 1 <= n <= total and n - 1 not in vistos:
            vistos.append(n - 1)
    return vistos


def modelo_reordenador(modelo_respuesta: str) -> str:
    """El reordenador de la misma familia que el modelo que responde, para no mezclar proveedores."""
    return MODELO_REORDENADOR_DEEPSEEK if modelo_respuesta.startswith("deepseek") else MODELO_REORDENADOR


def reordenar(pregunta: str, candidatos: list[dict], k: int = FRAGMENTOS_POR_DEFECTO, modelo: str = MODELO_REORDENADOR) -> list[dict]:
    """Los k mejores candidatos según el modelo; si falla, los k primeros en su orden original."""
    from taaml.tareas import obtener_modelo  # import tardío: tareas importa recuperacion, no al revés

    sin_etiquetas = pregunta.replace("</user_input>", "").replace("<user_input>", "")  # la plantilla ya delimita la pregunta con esas etiquetas; la pregunta no puede cerrarlas
    vista = "\n\n".join(f"[{i}] {c['texto'][:LARGO_VISTA]}" for i, c in enumerate(candidatos, 1))
    try:
        respuesta = obtener_modelo(modelo).invoke([HumanMessage(leer_prompt(PROMPT_REORDENADOR).format(pregunta=sin_etiquetas, k=k, candidatos=vista))]).text  # AIMessage.text: el texto de la respuesta (langchain-core 1.x)
    except Exception:  # noqa: BLE001  sin red, sin cuota o sin clave: se conserva el orden de la búsqueda
        return candidatos[:k]
    elegidos = parsear_orden(respuesta, len(candidatos))[:k]
    # si el modelo eligió menos de k, se completa con los mejores de la búsqueda que no eligió
    resto = [i for i in range(len(candidatos)) if i not in elegidos]
    return [candidatos[i] for i in (elegidos + resto)[:k]]


def buscar_reordenado(pregunta: str, k: int = FRAGMENTOS_POR_DEFECTO, candidatos: int = CANDIDATOS_POR_DEFECTO,
                      modelo: str = MODELO_REORDENADOR) -> list[dict]:
    """Búsqueda en dos pasos: `candidatos` por significado y luego el reordenamiento a k."""
    return buscar_reordenado_con_metricas(pregunta, k, candidatos, modelo)[0]


def buscar_reordenado_con_metricas(pregunta: str, k: int = FRAGMENTOS_POR_DEFECTO, candidatos: int = CANDIDATOS_POR_DEFECTO,
                                  modelo: str = MODELO_REORDENADOR) -> tuple[list[dict], dict]:
    """Dos pasos con métricas: la recuperación de candidatos mide su tiempo (el reordenamiento no se mide: no es recuperación)."""
    candidatos_encontrados, metricas = recuperar(pregunta, candidatos, "auto")
    return reordenar(pregunta, candidatos_encontrados, k, modelo), metricas
