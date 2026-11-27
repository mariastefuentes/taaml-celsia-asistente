"""PLAN B DE LA DEMOSTRACIÓN: repite en pantalla una conversación real ya grabada, por si Meta, el túnel o la red fallan.

  uv run python scripts/37_demo_plan_b.py --grabar      # habla con el agente REAL (gasta unas 8 a 12 llamadas) y guarda docs/demo_grabada.json
  uv run python scripts/37_demo_plan_b.py               # reproduce lo grabado, con pausas, sin red ni modelo
  uv run python scripts/37_demo_plan_b.py --rapido      # igual, sin pausas (para ensayar)

Es una REPETICIÓN: lo que se ve lo dijo el agente real el día de la grabación, pero no se está generando ahora. La pantalla lo avisa
en cada mensaje y hay que decirlo en voz alta: presentar esto como una conversación en vivo sería engañar al público.
La grabación usa memoria SQLite temporal, así no toca la base de la demostración.
"""

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

ARCHIVO = ROOT / "docs" / "demo_grabada.json"
AVISO = "*** REPETICIÓN GRABADA: no se está generando ahora ***"
# Los mismos casos del guion (docs/guion_demo_whatsapp.md): tabla, conteo, documento, fuera de alcance, datos que faltan y memoria.
MENSAJES = [
    "¿Qué sedes hay en Ibagué?",
    "¿Cuántas tiendas Celsia hay?",
    "¿Qué es una granja solar?",
    "¿Quién ganó el mundial de 2014?",
    "¿Cuánto cuesta un cargador de carro eléctrico?",
    "Me llamo Laura y vivo en Palmira",
    "¿Cómo me llamo y dónde vivo?",
]


def grabar() -> None:
    os.environ["DATABASE_URL"] = ""  # memoria SQLite: no mezcla la grabación con la base de la demostración
    from uuid import uuid4

    from taaml.agente import MODELO_AGENTE, conversar

    hilo, usuario = uuid4().hex, uuid4().hex
    turnos = []
    for mensaje in MENSAJES:
        inicio = time.monotonic()
        texto, llamadas = conversar(mensaje, hilo, usuario=usuario)
        turnos.append(
            {
                "cliente": mensaje,
                "asistente": texto,
                "herramientas": [ll["herramienta"] for ll in llamadas],
                "segundos": round(time.monotonic() - inicio, 1),
            }
        )
        print(f"grabado: {mensaje}")
    ARCHIVO.write_text(
        json.dumps({"grabada_el": date.today().isoformat(), "modelo": MODELO_AGENTE, "turnos": turnos}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Listo: {len(turnos)} turnos en {ARCHIVO}")


def _escribir(texto: str, rapido: bool) -> None:
    """Imprime letra por letra (como si se escribiera) salvo en modo rápido."""
    for letra in texto:
        sys.stdout.write(letra)
        sys.stdout.flush()
        if not rapido:
            time.sleep(0.012)
    sys.stdout.write("\n")


def reproducir(rapido: bool) -> None:
    if not ARCHIVO.exists():
        sys.exit(f"No hay grabación: corre primero `uv run python scripts/37_demo_plan_b.py --grabar` ({ARCHIVO.name}).")
    datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
    print(f"\n{AVISO}\nGrabada el {datos['grabada_el']} con {datos['modelo']}.\n")
    for t in datos["turnos"]:
        print(f"Cliente: {t['cliente']}")
        if not rapido:
            time.sleep(min(t["segundos"], 6))  # lo que tardó de verdad, con tope: el público no espera 25 s en una repetición
        usadas = ", ".join(t["herramientas"]) or "ninguna"
        print(f"  [herramientas: {usadas} · tardó {t['segundos']} s]")
        _escribir(f"Asistente: {t['asistente']}", rapido)
        print(f"  {AVISO}\n")
        if not rapido:
            time.sleep(1.5)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grabar", action="store_true", help="habla con el agente real y guarda la conversación")
    ap.add_argument("--rapido", action="store_true", help="sin pausas")
    args = ap.parse_args()
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows rompe las tildes si no
    grabar() if args.grabar else reproducir(args.rapido)


if __name__ == "__main__":
    main()
