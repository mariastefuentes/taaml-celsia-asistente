"""Registro en memoria de lo que hace el agente, para el panel en vivo de la demostración.

Cada turno deja una fila: cuándo, por qué canal llegó, quién (solo un trozo del hash del teléfono, nunca el número), qué escribió, qué
se le respondió y con qué fuentes, qué herramientas usó, cuánto tardó y cómo terminó. Se guardan solo los últimos `MAXIMO` en memoria del
proceso: no hay base de datos y se pierde al reiniciar, que es lo que se quiere para una pantalla de demostración.
"""

import hashlib
import threading
import time
from collections import deque
from typing import Any

MAXIMO = 200
MAX_TEXTO = 140  # lo que se ve del mensaje en pantalla
MAX_RESPUESTA = 1500  # lo que se guarda de la respuesta del asistente
MAX_FUENTES = 6
MAX_EXTRACTO = 300
ESTADOS = ("respondido", "pendiente de aprobación", "límite", "no soportado", "error", "aprobación", "voz")

_FILAS: deque[dict[str, Any]] = deque(maxlen=MAXIMO)
_USADAS: set[str] = set()  # herramientas distintas usadas desde que arrancó el servidor, aunque sus filas ya hayan salido
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
    nota: bool = False,
    costo: float | None = None,
    respuesta: str = "",
    fuentes: list[dict] | None = None,
) -> dict[str, Any]:
    """Agrega una fila y la devuelve. `estado` es uno de ESTADOS (cómo terminó el turno).

    `nota` dice si la respuesta llevó la nota de «dato sin respaldo»; `costo` es lo que costó el turno en dólares (None si no se pudo
    calcular). De cada fuente se guardan documento, fragmento, enlace y extracto, sin repetir fragmentos.
    """
    global _SIGUIENTE
    unicas = list({(f.get("documento"), f.get("fragmento")): f for f in fuentes or []}.values())[:MAX_FUENTES]
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
            "nota": bool(nota),
            "costo": None if costo is None else round(costo, 5),
            "respuesta": respuesta.strip()[:MAX_RESPUESTA],
            "fuentes": [
                {
                    **{campo: str(f.get(campo, "")) for campo in ("documento", "fragmento", "fuente")},
                    "extracto": str(f.get("extracto", ""))[:MAX_EXTRACTO],
                }
                for f in unicas
            ],
        }
        _SIGUIENTE += 1
        _FILAS.append(fila)
        _USADAS.update(fila["herramientas"])
    return fila


def herramientas_usadas() -> list[str]:
    """Las herramientas distintas que el agente ha usado desde que arrancó el servidor, en orden alfabético."""
    with _CERROJO:
        return sorted(_USADAS)


def recientes(desde: int = 0) -> list[dict[str, Any]]:
    """Las filas con número mayor que `desde`, de la más vieja a la más nueva."""
    with _CERROJO:
        return [f for f in _FILAS if f["n"] > desde]


def vaciar() -> None:
    """Borra el registro (para las pruebas y para empezar la demostración en limpio)."""
    global _SIGUIENTE
    with _CERROJO:
        _FILAS.clear()
        _USADAS.clear()
        _SIGUIENTE = 1
