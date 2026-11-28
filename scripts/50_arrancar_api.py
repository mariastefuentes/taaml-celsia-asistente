"""Arranca la API de forma idempotente; ver `taaml.arranque_api`."""

import sys
from pathlib import Path

# `python scripts/50_arrancar_api.py` no pone la raíz del repo en sys.path; hace falta para `api.main`.
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from taaml.arranque_api import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
