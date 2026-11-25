"""Enviar al cliente, por el WhatsApp de OpenClaw, la respuesta que llega después de que una persona decide.

El puente (`puente_mcp.py`) solo contesta cuando el cliente escribe. La decisión sobre un reclamo llega más tarde, así que la API la
manda con `openclaw message send`. Está apagado salvo que el `.env` del equipo del bot diga `OPENCLAW_AVISOS=1` **y** tenga
`CHAT_TOKEN`: sin esa clave `/chat` queda abierto y cualquiera podría crear un pendiente con el número de otra persona para que el
bot le escriba.
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger("taaml.avisos_openclaw")
TIEMPO_MAXIMO = 60  # segundos: arrancar el comando de OpenClaw toma varios
LIMITE_TEXTO = 4096


def activos() -> bool:
    return os.environ.get("OPENCLAW_AVISOS", "").strip() == "1" and bool(os.environ.get("CHAT_TOKEN"))


def comando() -> list[str] | None:
    """Cómo llamar a OpenClaw sin pasar por una consola, o None si no está instalado.

    En Windows `openclaw` es un archivo .cmd: pasarle el texto del mensaje dejaría que la consola interpretara sus caracteres, así que
    se llama a Node directamente con el programa que ese .cmd ejecuta.
    """
    ejecutable = shutil.which("openclaw")
    if not ejecutable:
        return None
    if os.name != "nt":
        return [ejecutable]
    programa = Path(ejecutable).parent / "node_modules" / "openclaw" / "openclaw.mjs"
    nodo = shutil.which("node")
    return [nodo, str(programa)] if nodo and programa.is_file() else None


def enviar(telefono: str, texto: str, simular: bool = False) -> bool:
    """Envía `texto` al teléfono por el canal de WhatsApp de OpenClaw. Devuelve si el comando terminó bien; nunca lanza.

    Con `simular` OpenClaw muestra lo que mandaría y no envía nada. El registro no guarda ni el número ni el texto.
    """
    base = comando()
    digitos = "".join(c for c in telefono if c.isdigit())
    if not base or not digitos or not texto.strip():
        log.warning("no se pudo preparar el aviso por OpenClaw (¿está instalado?)")
        return False
    orden = [*base, "message", "send", "--channel", "whatsapp", f"--target=+{digitos}", f"--message={texto[:LIMITE_TEXTO]}", "--json"]
    if simular:
        orden.append("--dry-run")
    try:
        resultado = subprocess.run(orden, capture_output=True, timeout=TIEMPO_MAXIMO, check=False)
    except (OSError, subprocess.SubprocessError) as error:
        log.warning("falló el aviso por OpenClaw (%s)", type(error).__name__)  # el detalle traería el número y el texto
        return False
    if resultado.returncode != 0:
        log.warning("OpenClaw no envió el aviso (código %s); revisa `openclaw channels status --probe`", resultado.returncode)
        return False
    return True
