"""Piezas comunes de las herramientas del agente: los esquemas base (que rechazan argumentos inventados), el contexto de quién conversa y el acceso al Store.

Viven aquí, y no en `agente.py`, para que las herramientas nuevas (`herramientas_servicio.py`) las importen sin importaciones circulares.
"""

from dataclasses import dataclass

from langchain.tools import ToolRuntime
from langgraph.store.base import BaseStore
from pydantic import BaseModel, ConfigDict, Field


class EsquemaEstricto(BaseModel):
    """Base de los esquemas de entrada de las herramientas: rechaza argumentos que no existen y recorta espacios sobrantes."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


ANONIMO = "anonimo"  # sin identificador de cliente no hay memoria de largo plazo: si no, todos los anónimos compartirían lo guardado


@dataclass
class Contexto:
    """Quién conversa: el Store separa lo guardado de cada cliente con este identificador (no lo ve el modelo)."""

    usuario: str = ANONIMO


def _almacen(runtime: ToolRuntime[Contexto]) -> BaseStore:
    if runtime.store is None:
        raise RuntimeError("El agente se creó sin Store: no hay memoria de largo plazo")
    return runtime.store


class EsquemaConRuntime(EsquemaEstricto):
    """Base de los esquemas de las herramientas que usan la memoria: lleva `runtime`, que inyecta el sistema.

    Hay que declararlo en el esquema: sin él, LangChain no lo inyecta y la llamada falla. Aun así el modelo no lo ve: el JSON Schema
    que se le envía (`tool_call_schema`) solo trae los campos de cada herramienta (lo comprueba una prueba).
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, arbitrary_types_allowed=True)
    runtime: ToolRuntime = Field(exclude=True)  # exclude: que Pydantic no intente serializar el contexto
