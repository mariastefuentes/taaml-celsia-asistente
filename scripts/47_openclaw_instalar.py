"""Instala la configuración versionada de OpenClaw y su workspace en la carpeta del usuario.

Uso:
    uv run python scripts/47_openclaw_instalar.py            # escribe ~/.openclaw/openclaw.json
    uv run python scripts/47_openclaw_instalar.py --forzar   # reemplaza (deja un .bak)
    uv run python scripts/47_openclaw_instalar.py --simular  # solo valida la plantilla, no escribe
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from taaml.openclaw import ConfiguracionInvalida, problemas, configuracion, instalar


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida e instala la configuración de OpenClaw del proyecto.")
    parser.add_argument("--destino", type=Path, default=Path.home() / ".openclaw", help="Carpeta destino (por defecto ~/.openclaw).")
    parser.add_argument("--forzar", action="store_true", help="Reemplaza la configuración existente (deja un respaldo .bak).")
    parser.add_argument("--simular", action="store_true", help="Solo valida la plantilla; no escribe nada.")
    args = parser.parse_args()

    load_dotenv()
    try:
        config = configuracion()
    except ConfiguracionInvalida as e:
        print(f"FALTA: {e}")
        print("Define OPENCLAW_GATEWAY_TOKEN, WHATSAPP_ALLOWLIST (+57…) y REPO_CELSIA en el entorno o en .env.")
        return 1

    fallos = problemas(config)
    if fallos:
        print("La plantilla no cumple el endurecimiento esperado:")
        for fallo in fallos:
            print(f"  - {fallo}")
        return 1
    print("Plantilla válida: bind loopback, sandbox completo, tools.deny, workspaceOnly y allowlist E.164.")
    if args.simular:
        return 0
    try:
        escritos = instalar(args.destino, forzar=args.forzar)
    except ConfiguracionInvalida as e:
        print(f"No se instaló: {e}")
        return 1
    for archivo in escritos:
        print(f"  escrito: {archivo}")
    print("Siguiente paso: con el Gateway apagado, registra el MCP y arranca OpenClaw; después `openclaw security audit`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
