"""Registro en memoria de lo que hace el agente, para el panel en vivo de la demostración.

Cada turno deja una fila: cuándo, por qué canal llegó, quién (solo un trozo del hash del teléfono, nunca el número), qué escribió, qué
herramientas usó, cuánto tardó y cómo terminó. Se guardan solo los últimos `MAXIMO` en memoria del proceso: no hay base de datos y se
pierde al reiniciar, que es lo que se quiere para una pantalla de demostración.
"""

import hashlib
import threading
import time
from collections import deque
from typing import Any

MAXIMO = 200
MAX_TEXTO = 140  # lo que se ve del mensaje en pantalla
ESTADOS = ("respondido", "pendiente de aprobación", "límite", "no soportado", "error", "aprobación", "voz")

_FILAS: deque[dict[str, Any]] = deque(maxlen=MAXIMO)
_CERROJO = threading.Lock()
_SIGUIENTE = 1


def quien(telefono: str) -> str:
    """Un identificador corto y estable para ver quién escribe sin mostrar el número."""
    digitos = "".join(c for c in telefono if c.isdigit()) or telefono
    return hashlib.sha256(f"panel:{digitos}".encode()).hexdigest()[:6]


def registrar(
    canal: str,
    telefono: str,
    mensaje: str,
    estado: str,
    herramientas: list[str] | None = None,
    segundos: float | None = None,
    reloj=time.time,
) -> dict[str, Any]:
    """Agrega una fila y la devuelve. `estado` es uno de ESTADOS (cómo terminó el turno)."""
    global _SIGUIENTE
    with _CERROJO:
        fila = {
            "n": _SIGUIENTE,
            "hora": time.strftime("%H:%M:%S", time.localtime(reloj())),
            "canal": canal,
            "quien": quien(telefono),
            "mensaje": " ".join(mensaje.split())[:MAX_TEXTO],
            "estado": estado,
            "herramientas": list(herramientas or []),
            "segundos": None if segundos is None else round(segundos, 1),
        }
        _SIGUIENTE += 1
        _FILAS.append(fila)
    return fila


def recientes(desde: int = 0) -> list[dict[str, Any]]:
    """Las filas con número mayor que `desde`, de la más vieja a la más nueva."""
    with _CERROJO:
        return [f for f in _FILAS if f["n"] > desde]


def vaciar() -> None:
    """Borra el registro (para las pruebas y para empezar la demostración en limpio)."""
    global _SIGUIENTE
    with _CERROJO:
        _FILAS.clear()
        _SIGUIENTE = 1
