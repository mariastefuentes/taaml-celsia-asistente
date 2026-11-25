"""CÓDIGO QR DE WHATSAPP DEL BOT: el auditorio lo escanea y queda en el chat del asistente, sin instalar nada ni estar en una lista.

Uso:
    make qr-whatsapp ARGS="+573001112233"
    make qr-whatsapp ARGS="+573001112233 --saludo 'Hola, quiero saber de Celsia' --html"

Genera `qr_whatsapp.png` (ignorado por Git) con el enlace `wa.me` del número que quedó vinculado al canal de OpenClaw. El número
va con indicativo y debe ser el del bot, no el personal de un integrante. Si se pasa la bandera `--html`, además escribe
`qr_whatsapp.html`, una página a pantalla completa para proyectar.
"""

import argparse
import sys
from pathlib import Path

import qrcode

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from taaml.whatsapp import enlace_wa_me  # noqa: E402

SALIDA_PNG = RAIZ / "qr_whatsapp.png"
SALIDA_HTML = RAIZ / "qr_whatsapp.html"

PLANTILLA_HTML = """<!doctype html>
<html lang="es">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Asistente Celsia por WhatsApp</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; gap: 1.5rem;
         background: #0b1f17; color: #f2fbf7; font-family: system-ui, sans-serif; text-align: center; padding: 2rem; }}
  h1 {{ margin: 0; font-size: clamp(1.6rem, 3vw, 2.6rem); }}
  p {{ margin: 0; font-size: clamp(1rem, 1.6vw, 1.4rem); opacity: .85; }}
  img {{ width: min(70vh, 90vw); height: auto; background: #fff; padding: 1rem; border-radius: 1rem; }}
  code {{ font-size: clamp(.9rem, 1.4vw, 1.2rem); opacity: .7; }}
</style>
<h1>Habla con el asistente de Celsia</h1>
<p>Escanea el código con la cámara de tu celular</p>
<img src="qr_whatsapp.png" alt="Código QR de WhatsApp">
<code>{enlace}</code>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("numero", help="número del bot con indicativo, por ejemplo +573001112233")
    ap.add_argument("--saludo", default="Hola", help="texto precargado en el chat (por defecto «Hola»)")
    ap.add_argument("--html", action="store_true", help="además escribe qr_whatsapp.html para proyectar")
    args = ap.parse_args()
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        enlace = enlace_wa_me(args.numero, args.saludo)
    except ValueError as e:
        print(f"FALTA: {e}")
        return 1

    qrcode.make(enlace, box_size=14, border=3).save(SALIDA_PNG)
    print(f"QR de {enlace} -> {SALIDA_PNG}")
    if args.html:
        SALIDA_HTML.write_text(PLANTILLA_HTML.format(enlace=enlace), encoding="utf-8")
        print(f"Página para proyectar -> {SALIDA_HTML}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
