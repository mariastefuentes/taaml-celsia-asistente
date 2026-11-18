"""PostgreSQL local para la memoria del agente (checkpointer y Store), sin Docker ni instalación aparte.

Usa `pgserver` (ya en las dependencias de desarrollo). Los datos quedan en `data/memoria/postgres/` y sobreviven entre arranques.
  uv run python scripts/32_postgres_local.py            # arranca (o reutiliza) el servidor y escribe su DATABASE_URL en la salida
  uv run python scripts/32_postgres_local.py --detener  # lo apaga

El puerto lo elige pgserver y puede cambiar en cada arranque, por eso `make api-pg` toma la dirección de aquí en vez de fijarla en el `.env`.
"""

import argparse
import sys
from pathlib import Path

import pgserver

RUTA = Path(__file__).resolve().parents[1] / "data" / "memoria" / "postgres"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--detener", action="store_true", help="apaga el servidor")
    args = p.parse_args()
    RUTA.parent.mkdir(parents=True, exist_ok=True)
    if args.detener:
        pgserver.get_server(RUTA).cleanup()
        print("PostgreSQL local detenido", file=sys.stderr)
        return
    servidor = pgserver.get_server(RUTA, cleanup_mode=None)  # None: sigue encendido cuando este script termina
    print(servidor.get_uri())


if __name__ == "__main__":
    main()
