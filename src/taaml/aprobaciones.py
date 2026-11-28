"""Lo que está esperando a una persona, para decidirlo desde el panel sin conocer el teléfono del cliente.

Cuando el agente se pausa (radicar o cancelar un reclamo, reportar un daño), la API lo anota aquí. El panel pide la lista, que no
trae teléfonos ni identificadores de la conversación: cada pendiente se decide con un código al azar. También guarda las respuestas
que no se pudieron enviar: el chat web las recoge del historial y, en los demás canales, salen con el siguiente mensaje del cliente.

El índice de pendientes se guarda en el Store (PostgreSQL o SQLite) cuando la API lo configura; sin Store (scripts y pruebas) vive
en memoria. Si la API se reinicia, el pendiente se recupera del Store. Las respuestas sin entregar siguen en memoria del proceso.
"""

import logging
import secrets
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any

log = logging.getLogger("taaml.aprobaciones")
MAXIMO = 200  # tope de pendientes y de respuestas sin entregar: el canal es público y no puede crecer sin límite
ESPACIO = ("aprobaciones",)  # namespace del Store: una conversación solo espera una decisión a la vez


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
_SIN_ENTREGAR: dict[str, tuple[str, str]] = {}  # por hilo: (texto, canal)
_DECIDIENDO: set[str] = set()
_CERROJO = threading.Lock()
_ALMACEN: Any | None = None  # Store de LangGraph cuando la API lo configura; None = solo memoria
_CARGADO = False


def configurar(almacen: Any | None) -> None:
    """Fija el Store donde se guardan los pendientes y carga los que ya existan (None vuelve a memoria)."""
    global _ALMACEN, _CARGADO
    with _CERROJO:
        _ALMACEN = almacen
        _CARGADO = False
        _PENDIENTES.clear()
    if almacen is not None:
        _cargar()


def _cargar() -> None:
    """Lee del Store el índice de pendientes; si falla, conserva la caché y sigue en memoria."""
    global _CARGADO
    with _CERROJO:
        if _ALMACEN is None:
            _CARGADO = True
            return
        try:
            items = _ALMACEN.search(ESPACIO, limit=MAXIMO * 2)
        except Exception:  # noqa: BLE001  la API sigue en memoria si el Store no responde
            log.exception("no se pudieron cargar los pendientes del Store")
            _CARGADO = True
            return
        _PENDIENTES.clear()
        for item in items:
            try:
                pendiente = Pendiente(**item.value)
            except (TypeError, ValueError):
                log.warning("pendiente guardado con formato inesperado: %s", item.key)
                continue
            _PENDIENTES[pendiente.hilo] = pendiente
        _recortar()
        _CARGADO = True


def _guardar(pendiente: Pendiente) -> None:
    """Escribe el pendiente en el Store; un fallo no impide decidirlo en este proceso."""
    if _ALMACEN is None:
        return
    try:
        _ALMACEN.put(ESPACIO, pendiente.hilo, asdict(pendiente))
    except Exception:  # noqa: BLE001
        log.exception("no se pudo guardar el pendiente %s", pendiente.hilo[:8])


def _borrar(hilo: str) -> None:
    if _ALMACEN is None:
        return
    try:
        _ALMACEN.delete(ESPACIO, hilo)
    except Exception:  # noqa: BLE001
        log.exception("no se pudo borrar el pendiente %s", hilo[:8])


def _recortar() -> None:
    while len(_PENDIENTES) > MAXIMO:
        hilo, viejo = min(_PENDIENTES.items(), key=lambda par: par[1].desde)
        _PENDIENTES.pop(hilo, None)
        _borrar(hilo)


def registrar(hilo: str, usuario: str, pendiente: dict, canal: str, telefono: str | None = None) -> Pendiente:
    """Anota lo que espera a una persona. Si la conversación ya estaba anotada, conserva su código y su hora."""
    with _CERROJO:
        anterior = _PENDIENTES.get(hilo)
        herramienta, args = pendiente.get("herramienta", ""), dict(pendiente.get("args") or {})
        if anterior and (anterior.herramienta, anterior.args) == (herramienta, args):
            return anterior
        nuevo = Pendiente(secrets.token_hex(4), hilo, usuario, herramienta, args, canal, telefono)
        _PENDIENTES[hilo] = nuevo
        _guardar(nuevo)
        _recortar()
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
        if _PENDIENTES.pop(hilo, None):
            _borrar(hilo)


def olvidar_usuario(usuario: str) -> int:
    """Borra los pendientes de un cliente al borrar sus datos; devuelve cuántos eran."""
    with _CERROJO:
        de_este = [p.hilo for p in _PENDIENTES.values() if p.usuario == usuario]
        for hilo in de_este:
            _PENDIENTES.pop(hilo, None)
            _borrar(hilo)
        return len(de_este)


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


def decidiendo(hilo: str) -> bool:
    """Si una decisión se está aplicando ahora mismo: la respuesta para el cliente todavía no está lista."""
    with _CERROJO:
        return hilo in _DECIDIENDO


def guardar_sin_entregar(hilo: str, texto: str, canal: str = "chat") -> None:
    """Si esa conversación ya tenía una decisión sin entregar, se juntan: la nueva no borra la anterior."""
    with _CERROJO:
        if previa := _SIN_ENTREGAR.get(hilo):
            texto = f"{previa[0]}\n\n{texto}"
        _SIN_ENTREGAR[hilo] = (texto, canal)
        while len(_SIN_ENTREGAR) > MAXIMO:
            _SIN_ENTREGAR.pop(next(iter(_SIN_ENTREGAR)))


def tomar_sin_entregar(hilo: str) -> str | None:
    """La respuesta que quedó sin enviar a esa conversación (y la olvida), o None."""
    with _CERROJO:
        entrega = _SIN_ENTREGAR.pop(hilo, None)
    return entrega[0] if entrega else None


def entregada_en_la_web(hilo: str) -> None:
    """El chat web ya la muestra (la trae del historial), así que no se repite con el siguiente mensaje. Lo de WhatsApp se conserva."""
    with _CERROJO:
        if _SIN_ENTREGAR.get(hilo, ("", ""))[1] == "web":
            del _SIN_ENTREGAR[hilo]


def vaciar() -> None:
    """Para las pruebas: borra la caché y, si hay Store, sus pendientes."""
    global _CARGADO
    with _CERROJO:
        for hilo in list(_PENDIENTES):
            _borrar(hilo)
        _PENDIENTES.clear()
        _SIN_ENTREGAR.clear()
        _DECIDIENDO.clear()
        _CARGADO = False
