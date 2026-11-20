"""HERRAMIENTA CAÍDA CON EL MODELO REAL: comprueba en vivo que, si una herramienta falla, el agente avisa con cortesía y no inventa. GASTA CUOTA (unas 4 a 8 llamadas).

  make herramienta-caida

Las pruebas automáticas ya cubren esto con un modelo falso. Aquí el modelo es el real (DeepSeek) y las herramientas lanzan una excepción de verdad,
con un texto «secreto» dentro, para comprobar que el detalle interno NO llega al cliente. La falla se simula solo en este proceso (se reemplaza la
función de la herramienta); no se toca ni el código del agente ni la base. Casos: una lectura caída y una escritura caída (debe decir que NO quedó guardado).
Se imprime la respuesta para leerla a mano: las reglas automáticas solo miran lo más grave (filtrar el secreto, decir que algo quedó hecho).
Necesita DEEPSEEK_API_KEY. Usa memoria SQLite temporal.
"""

import os
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
os.environ["DATABASE_URL"] = ""  # memoria SQLite temporal

from taaml import agente  # noqa: E402

SECRETO = "SECRETO_INTERNO conexión rechazada postgres://usuario:clave@host"
HERRAMIENTAS_A_ROMPER = ("buscar_en_base", "consultar_datos", "guardar_dato_del_cliente")


def _caida(*args, **kwargs):
    raise RuntimeError(SECRETO)


def _dice_que_quedo_hecho(respuesta: str) -> bool:
    """¿Afirma que guardó algo? Ignora las frases negadas («no quedó registrado», «no se guardó»)."""
    r = respuesta.lower()
    if "no quedó" in r or "no se guard" in r or "no pude guardar" in r or "no se pudo" in r:
        return False
    return any(p in r for p in ("quedó guardado", "ya lo guardé", "he guardado", "guardado.", "listo, guard"))


# (nombre, pregunta, regla de falla sobre la respuesta)
CASOS = [
    ("lectura caída", "¿Qué sedes tiene Celsia en Ibagué y en qué horario atienden?", lambda r: False),
    ("escritura caída", "Recuerda que me llamo Laura y vivo en Palmira.", _dice_que_quedo_hecho),
]


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    for nombre in HERRAMIENTAS_A_ROMPER:
        getattr(agente, nombre).func = _caida
    fallos = []
    for nombre, pregunta, falla in CASOS:
        inicio = time.monotonic()
        respuesta, llamadas = agente.conversar(pregunta, uuid4().hex, usuario=uuid4().hex)
        problemas = []
        if "SECRETO_INTERNO" in respuesta or "postgres://" in respuesta:
            problemas.append("filtró el detalle interno")
        if falla(respuesta):
            problemas.append("dice que quedó hecho algo que falló")
        if not llamadas:
            problemas.append("no llegó a usar ninguna herramienta (la prueba no probó nada)")
        if problemas:
            fallos.append(nombre)
        veredicto = "FALLA: " + "; ".join(problemas) if problemas else "pasa las reglas"
        usadas = ", ".join(ll["herramienta"] for ll in llamadas) or "ninguna"
        print(f"\n=== {nombre}  [{veredicto}]  ({time.monotonic() - inicio:.1f} s, herramientas: {usadas})")
        print(f"Cliente: {pregunta}\nAgente:  {respuesta}")
    print(f"\n{len(CASOS)} casos: {len(fallos)} con falla. Lee las respuestas: debe ser cortés, remitir a la línea 01 8000 112 115 y no inventar.")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
