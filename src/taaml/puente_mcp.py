"""Puente entre el canal de WhatsApp de OpenClaw y el agente de Celsia (las 20 herramientas, la memoria por cliente y la aprobación humana).

El agente de OpenClaw solo ve las herramientas MCP que se le conectan. Las diez de solo lectura (`servidor_mcp.py`) no incluyen la memoria del
cliente, los reclamos ni la aprobación humana, que viven en el agente propio (`taaml.agente`, servido por `api/main.py`). Este servidor MCP
expone **una sola herramienta**, `atender_cliente_celsia`, que le pasa el mensaje a ese agente por `POST /chat` y devuelve su respuesta tal cual.

Quién escribe lo decide OpenClaw, no el modelo: el plugin `openclaw/plugins/puente-celsia.js` reescribe el argumento `telefono` con el
remitente que OpenClaw verificó en el canal, así que un cliente no puede hacerse pasar por otro pidiéndolo en el chat. Aquí además se
exige que el número esté en `WHATSAPP_ALLOWLIST` y que cumpla el formato E.164.

Transporte stdio (OpenClaw lo lanza como proceso hijo). Variables: `CELSIA_API_URL` (por defecto http://127.0.0.1:8000) y `CHAT_TOKEN`.
"""

import os
import re

import requests
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

from taaml.whatsapp import autorizado

load_dotenv()

E164 = re.compile(r"^\+[1-9][0-9]{7,14}$")
TIEMPO_MAXIMO = 120  # segundos: un turno con herramientas y el modelo puede tardar
MENSAJE_NO_AUTORIZADO = "Este número no está autorizado para usar el asistente."
MENSAJE_DE_FALLO = "No pude consultar el asistente en este momento. Intenta de nuevo en unos minutos o llama a la línea 01 8000 112 115."

servidor = MCPServer("puente")


def atender(mensaje: str, telefono: str) -> str:
    """Un turno del agente de Celsia para ese teléfono; nunca lanza: un fallo vuelve como texto cortés."""
    telefono = telefono.strip()
    if not E164.match(telefono) or not autorizado(telefono):
        return MENSAJE_NO_AUTORIZADO
    cabeceras = {"X-Api-Key": os.environ["CHAT_TOKEN"]} if os.environ.get("CHAT_TOKEN") else {}
    try:
        respuesta = requests.post(
            os.environ.get("CELSIA_API_URL", "http://127.0.0.1:8000").rstrip("/") + "/chat",
            json={"mensaje": mensaje[:1000], "telefono": telefono},  # /chat acepta hasta 1.000 caracteres
            headers=cabeceras,
            timeout=TIEMPO_MAXIMO,
        )
        if respuesta.status_code == 429:
            return str(respuesta.json().get("detail") or MENSAJE_DE_FALLO)
        respuesta.raise_for_status()
        return str(respuesta.json()["respuesta"])
    except Exception:  # noqa: BLE001  al cliente no se le filtra ningún detalle interno
        return MENSAJE_DE_FALLO


@servidor.tool()
def atender_cliente_celsia(mensaje: str, telefono: str) -> str:
    """Pasa el mensaje del cliente al agente de Celsia y devuelve su respuesta, que debe enviarse al cliente sin cambios.

    `telefono` es el número del cliente en formato E.164 (+57…). Lo fija OpenClaw con el remitente real del canal.
    """
    return atender(mensaje, telefono)


if __name__ == "__main__":
    servidor.run()
