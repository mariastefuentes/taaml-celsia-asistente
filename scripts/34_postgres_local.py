"""PostgreSQL local para la memoria del agente (checkpointer y Store), sin Docker ni instalación aparte.

Usa `pgserver` (ya en las dependencias de desarrollo). Los datos quedan en `data/memoria/postgres/` y sobreviven entre arranques.
  uv run python scripts/34_postgres_local.py            # arranca (o reutiliza) el servidor y escribe su DATABASE_URL en la salida
  uv run python scripts/34_postgres_local.py --detener  # lo apaga

El puerto lo elige pgserver y puede cambiar en cada arranque, por eso `make api-pg` toma la dirección de aquí en vez de fijarla en el `.env`.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

import psycopg
import pgserver
from pgserver.utils import PostmasterInfo

RUTA = Path(__file__).resolve().parents[1] / "data" / "memoria" / "postgres"


def _arrancar():
    """Obtiene el servidor a `pgserver`; si el `pg_ctl -w` que usa pgserver expira (su timeout es 10 s y en
    Windows el arranque se demora por la recuperaci├│n de la base y conflictos con el archivo de log), reintenta:
    al segunda llamada devuelve la instancia ya registrada mientras el servidor sigue subiendo."""
    deadline = time.monotonic() + 120
    while True:
        try:
            # None: sigue encendido cuando este script termina
            return pgserver.get_server(RUTA, cleanup_mode=None)
        except subprocess.TimeoutExpired:
            if time.monotonic() > deadline:
                raise
            time.sleep(2)


def _esperar_listo() -> PostmasterInfo:
    """Espera a que el servidor acepte una consulta de verdad: el archivo `postmaster.pid` dice 'ready'
    antes de que el puerto sirva, y en Windows el arranque se demora m├ís all├í de lo que aguanta el timeout
    de `pg_ctl`, as├¡ que lo comprueba conect├índose."""
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            info = PostmasterInfo.read_from_pgdata(RUTA)
            if info is not None and info.is_running():
                with psycopg.connect(info.get_uri(), autocommit=True) as conn:
                    conn.execute("select 1")
                return info
        except Exception:
            pass  # a├║n no sirve: en Windows la recuperaci├│n del arranque lleva su tiempo
        time.sleep(1)
    raise RuntimeError("el servidor PostgreSQL no qued├│ disponible; revisa el log en data/memoria/postgres/log")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--detener", action="store_true", help="apaga el servidor")
    args = p.parse_args()
    RUTA.parent.mkdir(parents=True, exist_ok=True)
    if args.detener:
        pgserver.get_server(RUTA).cleanup()
        print("PostgreSQL local detenido", file=sys.stderr)
        return
    # El 0xC0000142 en Windows puede matar al servidor poco después de su arranque ("aborting startup
    # due to startup process failure"); reintentamos el ciclo de arranque mientras la ventana de conexión se abre.
    for intento in range(1, 4):
        try:
            _arrancar()
            pinfo = _esperar_listo()
            with psycopg.connect(pinfo.get_uri(), autocommit=True) as conn:
                conn.execute("select 1")
            print(pinfo.get_uri())
            return
        except Exception as e:
            if intento == 3:
                raise
            print(f"intento {intento} sin servidor disponible ({e!r}); reintentando en 2 s", file=sys.stderr)
            time.sleep(2)


if __name__ == "__main__":
    main()
