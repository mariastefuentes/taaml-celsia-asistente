"""CHEQUEO PREVIO DE LA DEMOSTRACIÓN POR WHATSAPP: dice qué falta antes de empezar. No llama al modelo ni gasta cuota.

  make ensayo-whatsapp                                                       # revisa todo lo local y, si hay claves, el token de Meta
  uv run python scripts/39_chequeo_whatsapp.py --tunel https://algo.trycloudflare.com   # además prueba el camino túnel -> API

Revisa: las claves (solo si existen; nunca se imprimen), Ollama y el índice, la API local (`make api` encendida, memoria, panel),
que el token de Meta siga vivo (el de prueba vence a las 24 horas y es la falla más común) y, con `--tunel`, que la dirección pública
llegue al webhook (se hace la verificación GET de Meta, que no usa el modelo). Termina con código 1 si falta algo imprescindible.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

API = "http://127.0.0.1:8000"
VERSION = os.environ.get("WHATSAPP_API_VERSION") or "v23.0"
resultados: list[tuple[str, str, str]] = []  # (estado, qué se revisó, qué hacer si falla)


def anotar(ok: bool | None, que: str, arreglo: str = "", critico: bool = True) -> None:
    estado = "OK   " if ok else ("AVISO" if ok is None or not critico else "FALTA")
    resultados.append((estado, que, "" if ok else arreglo))


def pedir(url: str, cabeceras: dict | None = None, tiempo: int = 6) -> tuple[int, str]:
    """GET sencillo: devuelve (código HTTP, cuerpo); (0, motivo) si no hay conexión."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=cabeceras or {}), timeout=tiempo) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, type(e).__name__


def revisar_variables() -> None:
    for nombre, para in [
        ("DEEPSEEK_API_KEY", "el modelo del agente"),
        ("WHATSAPP_TOKEN", "enviar mensajes por Meta"),
        ("WHATSAPP_PHONE_NUMBER_ID", "el número desde el que se responde"),
        ("WHATSAPP_APP_SECRET", "comprobar la firma de cada aviso"),
        ("WHATSAPP_VERIFY_TOKEN", "registrar el webhook en Meta"),
        ("APROBADOR_TOKEN", "aprobar reclamos y ver el panel en vivo"),
    ]:
        anotar(bool(os.environ.get(nombre)), f"{nombre} definida ({para})", "agrégala al .env (ver .env.example)")
    anotar(bool(os.environ.get("CHAT_TOKEN")), "CHAT_TOKEN definida (protege POST /chat)", "opcional pero recomendada: sin ella /chat está abierto a quien tenga la URL", critico=False)
    anotar(None, "APROBADOR_WHATSAPP (aprobar con botones, opcional)" if not os.environ.get("APROBADOR_WHATSAPP") else "APROBADOR_WHATSAPP definida", "opcional: sin ella se aprueba con POST /aprobar", critico=False)
    if os.environ.get("APROBADOR_WHATSAPP"):
        resultados[-1] = ("OK   ", "APROBADOR_WHATSAPP definida (aprobar con botones)", "")


def revisar_ollama_e_indice() -> None:
    codigo, cuerpo = pedir("http://localhost:11434/api/tags", tiempo=3)
    modelos = [m["name"] for m in json.loads(cuerpo).get("models", [])] if codigo == 200 else []
    anotar(codigo == 200, "Ollama encendido", "abre Ollama (los embeddings de las preguntas lo necesitan)")
    anotar(any("nomic-embed-text-v2-moe" in m for m in modelos), "modelo nomic-embed-text-v2-moe instalado", "ollama pull nomic-embed-text-v2-moe")
    try:
        from taaml.recuperacion import INDICE

        anotar(Path(INDICE).exists() or (ROOT / "data" / "4_curaduria" / "qdrant").exists(), "índice de vectores presente", "make indice")
    except Exception as e:  # noqa: BLE001
        anotar(False, f"índice de vectores ({type(e).__name__})", "make indice")


def revisar_api() -> None:
    codigo, cuerpo = pedir(f"{API}/api/salud")
    anotar(codigo == 200, "API local encendida en el puerto 8000", "make api")
    if codigo != 200:
        return
    salud = json.loads(cuerpo)
    anotar(salud.get("memoria") == "postgresql", f"memoria en {salud.get('memoria')}", "make api usa PostgreSQL; con make api-sqlite la memoria es SQLite", critico=False)
    anotar(salud.get("almacen") in {"qdrant", "numpy"}, f"búsqueda por significado: {salud.get('almacen')}", "make indice")
    anotar(pedir(f"{API}/panel")[0] == 200, "panel en vivo disponible (/panel)", "revisa que la API sea la versión actual")
    token = os.environ.get("APROBADOR_TOKEN", "")
    if token:
        anotar(pedir(f"{API}/api/actividad", {"X-Aprobador": token})[0] == 200, "panel acepta el token del aprobador", "APROBADOR_TOKEN de .env distinto del de la API en marcha: reinicia make api")
    verificar = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
    if verificar:
        consulta = urllib.parse.urlencode({"hub.mode": "subscribe", "hub.verify_token": verificar, "hub.challenge": "prueba123"})
        codigo, cuerpo = pedir(f"{API}/webhook/whatsapp?{consulta}")
        anotar(codigo == 200 and cuerpo == "prueba123", "verificación del webhook responde (GET como lo hace Meta)", "WHATSAPP_VERIFY_TOKEN / WHATSAPP_APP_SECRET no coinciden con los de la API en marcha")


def revisar_token_de_meta() -> None:
    token, numero = os.environ.get("WHATSAPP_TOKEN", ""), os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    if not (token and numero):
        anotar(False, "token de Meta vivo", "primero define WHATSAPP_TOKEN y WHATSAPP_PHONE_NUMBER_ID")
        return
    codigo, cuerpo = pedir(f"https://graph.facebook.com/{VERSION}/{numero}?fields=display_phone_number,verified_name", {"Authorization": f"Bearer {token}"})
    if codigo == 200:
        anotar(True, f"token de Meta vivo (número {json.loads(cuerpo).get('display_phone_number', '?')})")
    elif codigo in (400, 401, 403):
        anotar(False, f"token de Meta rechazado (HTTP {codigo}): probablemente venció", "genera uno nuevo en developers.facebook.com > WhatsApp > Configuración de la API y cámbialo en .env")
    else:
        anotar(None, f"no se pudo consultar a Meta (HTTP {codigo or 'sin conexión'})", "revisa la conexión a internet", critico=False)


def revisar_tunel(url: str) -> None:
    verificar = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
    consulta = urllib.parse.urlencode({"hub.mode": "subscribe", "hub.verify_token": verificar, "hub.challenge": "tunel123"})
    codigo, cuerpo = pedir(f"{url.rstrip('/')}/webhook/whatsapp?{consulta}", tiempo=10)
    anotar(codigo == 200 and cuerpo == "tunel123", f"el túnel llega al webhook ({url})", "el túnel no apunta a la API o su dirección cambió: regístrala de nuevo en Meta")
    anotar(None, f"dirección para registrar en Meta: {url.rstrip('/')}/webhook/whatsapp", "", critico=False)
    resultados[-1] = ("INFO ", resultados[-1][1], "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tunel", help="dirección pública (https://...) para probar el camino túnel -> API")
    args = ap.parse_args()
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    revisar_variables()
    revisar_ollama_e_indice()
    revisar_api()
    revisar_token_de_meta()
    if args.tunel:
        revisar_tunel(args.tunel)
    for estado, que, arreglo in resultados:
        print(f"{estado}  {que}" + (f"\n         -> {arreglo}" if arreglo else ""))
    faltan = [r for r in resultados if r[0] == "FALTA"]
    print(f"\n{'Todo lo imprescindible está listo.' if not faltan else f'Faltan {len(faltan)} cosas imprescindibles.'}")
    return 1 if faltan else 0


if __name__ == "__main__":
    sys.exit(main())
