"""Piezas comunes de las herramientas del agente: el esquema base que rechaza argumentos inventados.

Viven aquí, y no en `agente.py`, para que las herramientas nuevas (`herramientas_servicio.py`) las importen sin importaciones circulares.
"""

from pydantic import BaseModel, ConfigDict


class EsquemaEstricto(BaseModel):
    """Base de los esquemas de entrada de las herramientas: rechaza argumentos que no existen y recorta espacios sobrantes."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
