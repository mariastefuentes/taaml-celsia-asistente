"""Límite de mensajes por teléfono: protege la cuota del modelo cuando el bot es público (por ejemplo, durante la demo en vivo).

Ventana deslizante en memoria: cada teléfono puede mandar `maximo` mensajes en `ventana` segundos. Pasado el tope, los mensajes se
rechazan sin llamar al modelo hasta que el más antiguo salga de la ventana. Con varios procesos cada uno cuenta por su lado; para
esta entrega (un solo proceso de uvicorn) basta, y no necesita Redis ni otra base.

Se configura con `LIMITE_MENSAJES` (por defecto 8) y `LIMITE_VENTANA_S` (por defecto 60); `LIMITE_MENSAJES=0` lo apaga.
"""

import hashlib
import math
import os
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

MAXIMO_POR_DEFECTO = 8
VENTANA_POR_DEFECTO = 60.0
MAX_TELEFONOS_RECORDADOS = 5000  # tope de memoria: se olvidan primero los que llevan más tiempo sin escribir

TEXTO_LIMITE = (
    "Dame un momento: recibí varios mensajes seguidos. Escríbeme de nuevo en unos segundos; "
    "si es urgente, llama a la línea 01 8000 112 115."
)


@dataclass(frozen=True)
class Decision:
    permitido: bool
    espera_s: int = 0  # segundos hasta poder escribir de nuevo (solo si no se permite)
    avisar: bool = False  # True solo en el primer rechazo de la ventana: así el aviso no se convierte en otro spam


class LimitePorTelefono:
    def __init__(self, maximo: int, ventana: float, reloj: Callable[[], float] = time.monotonic):
        self.maximo, self.ventana, self._reloj = maximo, ventana, reloj
        self._envios: dict[str, deque[float]] = {}
        self._avisados: set[str] = set()
        self._cerrojo = threading.Lock()

    def revisar(self, telefono: str) -> Decision:
        """Cuenta un mensaje de este teléfono y dice si se atiende. No guarda el número: usa un hash."""
        if self.maximo <= 0:
            return Decision(True)
        clave = hashlib.sha256(f"limite:{telefono}".encode()).hexdigest()[:16]
        ahora = self._reloj()
        with self._cerrojo:
            envios = self._envios.pop(clave, None) or deque()  # pop + reinsertar: el diccionario queda ordenado por último uso
            while envios and ahora - envios[0] >= self.ventana:
                envios.popleft()
            self._envios[clave] = envios
            while len(self._envios) > MAX_TELEFONOS_RECORDADOS:
                viejo = next(iter(self._envios))
                self._envios.pop(viejo)
                self._avisados.discard(viejo)
            if len(envios) < self.maximo:
                envios.append(ahora)
                self._avisados.discard(clave)
                return Decision(True)
            primera_vez = clave not in self._avisados
            self._avisados.add(clave)
            return Decision(False, espera_s=max(1, math.ceil(self.ventana - (ahora - envios[0]))), avisar=primera_vez)


def limite_desde_entorno() -> LimitePorTelefono:
    """El límite según `LIMITE_MENSAJES` y `LIMITE_VENTANA_S`; un valor ilegible deja el valor por defecto."""

    def leer(nombre: str, defecto: float) -> float:
        try:
            return float(os.environ.get(nombre, defecto))
        except ValueError:
            return defecto

    return LimitePorTelefono(int(leer("LIMITE_MENSAJES", MAXIMO_POR_DEFECTO)), leer("LIMITE_VENTANA_S", VENTANA_POR_DEFECTO))
