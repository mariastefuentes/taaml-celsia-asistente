"""Valoraciones que los usuarios dan a las respuestas del asistente: 👍 (1) y 👎 (-1).

Se guardan en el Store de largo plazo del proceso (PostgreSQL o SQLite) que ya usan los datos del cliente
(`taaml.agente.almacen_de_largo_plazo`): una clave única por conversación y mensaje (`<hilo>:<id del mensaje>`),
así no se puede valorar dos veces la misma respuesta.
"""

from datetime import datetime
from typing import Any

from taaml.agente import almacen_compartido

NAMESPACE = ("retroalimentos",)  # espacio del Store: las valoraciones de todas las conversaciones


def registrar(hilo: str, mensaje_id: str, valor: int, usuario: str, almacen: Any = None) -> bool:
    """Guarda la valoración de una respuesta del asistente; devuelve False si ya había una (la clave es única).

    `hilo` y `mensaje_id` son los identificadores que la API entrega al frontend en el evento `fin` de un turno
    (el mensaje del asistente en la conversación, validado por `taaml.agente.mensaje_del_hilo`).
    """
    almacen = almacen or almacen_compartido()
    clave = f"{hilo}:{mensaje_id}"
    if almacen.get(NAMESPACE, clave):
        return False
    almacen.put(NAMESPACE, clave, {"valor": valor, "usuario": usuario, "fecha": datetime.now().isoformat()})
    return True
