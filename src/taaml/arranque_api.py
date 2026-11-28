"""Arranque idempotente de FastAPI en 127.0.0.1:8000.

Antes de abrir Uvicorn comprueba `/api/salud`. Si Celsia responde bien, no inicia otra
instancia. Si el puerto está ocupado por otro programa o por algo que no es la API, no
mata ningún proceso. Si el puerto está libre, arranca normalmente.
"""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import requests
import uvicorn

HOST = "127.0.0.1"
PORT = 8000
API_URL = f"http://{HOST}:{PORT}"
SALUD_URL = f"{API_URL}/api/salud"
APP = "api.main:app"
RAIZ_REPO = Path(__file__).resolve().parents[2]


def api_activa(timeout: float = 2.0) -> bool:
    """¿Celsia responde en /api/salud con estado ok? No imprime secretos."""
    try:
        respuesta = requests.get(SALUD_URL, timeout=timeout)
    except requests.RequestException:
        return False
    if respuesta.status_code != 200:
        return False
    try:
        datos = respuesta.json()
    except ValueError:
        return False
    return datos.get("estado") == "ok"


def puerto_ocupado(host: str = HOST, port: int = PORT) -> bool:
    """¿No se puede hacer bind en host:port? Compatible con Windows WinError 10048. No mata procesos."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return True
    return False


def iniciar_uvicorn() -> None:
    """Arranca Uvicorn normalmente; el llamador ya comprobó API y puerto."""
    # `make api` ejecuta `scripts/50_arrancar_api.py`, así que `sys.path[0]` no es la raíz.
    # Añadimos la raíz del repo para importar `api.main` también en Windows y con src-layout.
    raiz = str(RAIZ_REPO)
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    uvicorn.run(APP, host=HOST, port=PORT, app_dir=raiz)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    database_url = os.environ.get("DATABASE_URL") or (argv[0].strip() if argv else "")
    if database_url:
        os.environ["DATABASE_URL"] = database_url

    if api_activa():
        print(f"Celsia ya está ejecutándose en {API_URL}; no se inicia otra instancia.")
        return 0

    if puerto_ocupado():
        print(
            f"El puerto {PORT} en {HOST} está ocupado, pero {SALUD_URL} no responde como la API de Celsia. "
            "No se mata ningún proceso ni se inicia Uvicorn. Revisa qué programa usa el puerto.",
            file=sys.stderr,
        )
        return 1

    iniciar_uvicorn()
    return 0


if __name__ == "__main__":
    sys.exit(main())
