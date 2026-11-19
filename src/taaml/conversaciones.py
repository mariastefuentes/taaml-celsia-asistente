"""Conversaciones completas que ya guarda la API, listas para analizarlas (clústeres con t-SNE).

La API no necesita una tabla de registro aparte: el checkpointer (PostgresSaver o SqliteSaver) guarda cada conversación completa bajo su
`thread_id`, que es un hash del teléfono (el número nunca se guarda). Este módulo lee esos hilos y deja, por conversación, los turnos
visibles (cliente y asistente), las herramientas usadas y si terminó mal. No llama al modelo ni a la red.
"""

from typing import Any

from taaml.agente import MENSAJE_EN_REVISION

MARCAS_DE_FALLO = ("no tengo esa información", "no pude", "no está disponible", "no puedo escribirte código")
MAX_CARACTERES = 2000  # el modelo de embeddings tiene contexto limitado; una conversación típica mide unos cientos de caracteres


def _texto(mensaje: Any) -> str:
    return (getattr(mensaje, "text", None) or "").strip()


def es_fallida(turnos: list[dict], herramientas_con_error: int = 0) -> bool:
    """Una conversación falló si alguna herramienta dio error o si el asistente tuvo que decir que no sabía o no pudo."""
    if herramientas_con_error:
        return True
    return any(
        t["rol"] == "asistente" and any(marca in t["texto"].lower() for marca in MARCAS_DE_FALLO) for t in turnos
    )


def conversacion_de(hilo: str, mensajes: list) -> dict:
    """Una conversación lista para analizar: turnos visibles, herramientas usadas, estado y el texto que se va a convertir en vector."""
    turnos, herramientas, errores = [], [], 0
    for m in mensajes:
        if m.type == "human" and _texto(m):
            turnos.append({"rol": "cliente", "texto": _texto(m)})
        elif m.type == "ai":
            herramientas += [c["name"] for c in (m.tool_calls or [])]
            if _texto(m):
                turnos.append({"rol": "asistente", "texto": _texto(m)})
        elif m.type == "tool" and getattr(m, "status", "success") == "error":
            errores += 1
    texto = "\n".join(f"{'Cliente' if t['rol'] == 'cliente' else 'Asistente'}: {t['texto']}" for t in turnos)
    return {
        "hilo": hilo,
        "turnos": turnos,
        "herramientas": herramientas,
        "fallida": es_fallida(turnos, errores),
        "en_revision": any(t["texto"] == MENSAJE_EN_REVISION for t in turnos),
        "texto": texto[:MAX_CARACTERES],
    }


def leer_conversaciones(checkpointer: Any) -> list[dict]:
    """Todas las conversaciones guardadas en el checkpointer, ordenadas por hilo. Las que no tienen ningún turno visible se omiten."""
    hilos = sorted({c.config["configurable"]["thread_id"] for c in checkpointer.list(None)})
    salida = []
    for hilo in hilos:
        guardado = checkpointer.get_tuple({"configurable": {"thread_id": hilo}})
        mensajes = (guardado.checkpoint["channel_values"].get("messages") if guardado else None) or []
        conversacion = conversacion_de(hilo, mensajes)
        if conversacion["turnos"]:
            salida.append(conversacion)
    return salida
