"""CÓDIGO QR DEL CHAT WEB: el respaldo para el público si WhatsApp no alcanza (el número de prueba de Meta solo habla con 5 personas).

  make qr-chat-web ARGS="https://algo.trycloudflare.com"

Genera `qr_chat_web.png` (ignorado por Git) con la dirección pública del túnel: quien lo escanee abre el chat en su navegador, sin instalar nada
ni estar en la lista de Meta. Necesita la API en marcha (`make api`), el frontend compilado (`make chat-web`) y el túnel (`cloudflared tunnel --url http://localhost:8000`).
"""

import sys
from pathlib import Path

import qrcode

SALIDA = Path(__file__).resolve().parent.parent / "qr_chat_web.png"


def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1].startswith("https://"):
        sys.exit("Uso: make qr-chat-web ARGS=\"https://<tu-tunel>.trycloudflare.com\"")
    direccion = sys.argv[1].rstrip("/") + "/"
    qrcode.make(direccion, box_size=14, border=3).save(SALIDA)
    print(f"QR de {direccion} -> {SALIDA}")


if __name__ == "__main__":
    main()
