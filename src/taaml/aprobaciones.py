"""Lo que está esperando a una persona, para decidirlo desde el panel sin conocer el teléfono del cliente.

Cuando el agente se pausa (radicar o cancelar un reclamo, reportar un daño), la API lo anota aquí. El panel pide la lista, que no
trae teléfonos ni identificadores de la conversación: cada pendiente se decide con un código al azar. También guarda las respuestas
que no se pudieron enviar, para entregarlas con el siguiente mensaje del cliente.

Todo vive en memoria del proceso. Si la API se reinicia, la conversación sigue pausada en la base de datos y vuelve a aparecer aquí
en cuanto el cliente escribe de nuevo.
"""

import secrets
import threading
import time
from dataclasses import dataclass, field

MAXIMO = 200  # tope de pendientes y de respuestas sin entregar: el canal es público y no puede crecer sin límite


@dataclass
class Pendiente:
    codigo: str
    hilo: str
    usuario: str
    herramienta: str
    args: dict
    canal: str  # «chat» (OpenClaw y POST /chat), «web», «whatsapp» o «whatsapp (voz)» (webhook de Meta)
    telefono: str | None  # None en el chat web
    desde: float = field(default_factory=time.time)


_PENDIENTES: dict[str, Pendiente] = {}  # por hilo: una conversación solo espera una decisión a la vez
_SIN_ENTREGAR: dict[str, str] = {}  # por hilo
_DECIDIENDO: set[str] = set()
_CERROJO = threading.Lock()


def _recortar(cosas: dict) -> None:
    while len(cosas) > MAXIMO:
        cosas.pop(next(iter(cosas)))


def registrar(hilo: str, usuario: str, pendiente: dict, canal: str, telefono: str | None = None) -> Pendiente:
    """Anota lo que espera a una persona. Si la conversación ya estaba anotada, conserva su código y su hora."""
    with _CERROJO:
        anterior = _PENDIENTES.get(hilo)
        herramienta, args = pendiente.get("herramienta", ""), dict(pendiente.get("args") or {})
        if anterior and (anterior.herramienta, anterior.args) == (herramienta, args):
            return anterior
        nuevo = Pendiente(secrets.token_hex(4), hilo, usuario, herramienta, args, canal, telefono)
        _PENDIENTES[hilo] = nuevo
        _recortar(_PENDIENTES)
        return nuevo


def todos() -> list[Pendiente]:
    """Los pendientes, del más viejo al más nuevo."""
    with _CERROJO:
        return sorted(_PENDIENTES.values(), key=lambda p: p.desde)


def por_codigo(codigo: str) -> Pendiente | None:
    with _CERROJO:
        return next((p for p in _PENDIENTES.values() if secrets.compare_digest(p.codigo.encode(), codigo.encode())), None)


def por_hilo(hilo: str) -> Pendiente | None:
    with _CERROJO:
        return _PENDIENTES.get(hilo)


def quitar(hilo: str) -> None:
    with _CERROJO:
        _PENDIENTES.pop(hilo, None)


def empezar_decision(hilo: str) -> bool:
    """Reserva la conversación mientras se aplica una decisión; False si otra petición ya la está aplicando (evita radicar dos veces)."""
    with _CERROJO:
        if hilo in _DECIDIENDO:
            return False
        _DECIDIENDO.add(hilo)
        return True


def terminar_decision(hilo: str) -> None:
    with _CERROJO:
        _DECIDIENDO.discard(hilo)


def guardar_sin_entregar(hilo: str, texto: str) -> None:
    with _CERROJO:
        _SIN_ENTREGAR[hilo] = texto
        _recortar(_SIN_ENTREGAR)


def tomar_sin_entregar(hilo: str) -> str | None:
    """La respuesta que quedó sin enviar a esa conversación (y la olvida), o None."""
    with _CERROJO:
        return _SIN_ENTREGAR.pop(hilo, None)


def vaciar() -> None:
    """Para las pruebas."""
    with _CERROJO:
        _PENDIENTES.clear()
        _SIN_ENTREGAR.clear()
        _DECIDIENDO.clear()
