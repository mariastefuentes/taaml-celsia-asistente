"""Herramientas de servicio al cliente que se suman a las cinco del agente base (una por una, cada una con su esquema y sus pruebas).

La lógica vive en funciones simples que se prueban sin modelo; la herramienta de LangChain solo las envuelve.
"""

import json
import math

from langchain_core.tools import tool
from pydantic import Field, model_validator

from taaml.base_herramientas import EsquemaEstricto
from taaml.consulta_datos import SEDES, SIN_RESULTADOS, _contiene_alguno, _norm
from taaml.sanitizar import quitar_invisibles

MAX_SEDES_CERCANAS = 3
RADIO_TIERRA_KM = 6371.0


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en línea recta entre dos puntos (fórmula de haversine), en kilómetros."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(a))


def _sedes_de_colombia() -> list[dict]:
    return [s for s in json.loads(SEDES.read_text(encoding="utf-8")) if s["COUNTRY"] == "Colombia"]


def sedes_cercanas_a(latitud: float | None = None, longitud: float | None = None, ciudad: str = "") -> str:
    """Las sedes de Colombia más cercanas a un punto (coordenadas) o a una ciudad que ya tenga sede, con la distancia en línea recta."""
    sedes = _sedes_de_colombia()
    if latitud is None or longitud is None:
        de_la_ciudad = [s for s in sedes if _norm(ciudad) and _norm(ciudad) in _norm(s["CITY"])]
        if not de_la_ciudad:
            return (
                f"No tengo coordenadas de «{ciudad}» porque no figura entre las ciudades con sede. "
                "Pídele al cliente que comparta su ubicación o que diga una ciudad cercana donde haya sede."
            )
        latitud = sum(s["LATITUDE"] for s in de_la_ciudad) / len(de_la_ciudad)
        longitud = sum(s["LONGITUDE"] for s in de_la_ciudad) / len(de_la_ciudad)
    con_distancia = sorted(
        ((distancia_km(latitud, longitud, s["LATITUDE"], s["LONGITUDE"]), s) for s in sedes), key=lambda par: par[0]
    )[:MAX_SEDES_CERCANAS]
    lineas = [
        f"- {s['NAME']} ({s['HQ_TYPE']}, {s['CITY']}), a {km:.1f} km en línea recta. Dirección: {s['ADDRESS']}. "
        f"Teléfono: {s['PHONE'] or 'sin dato'}. Horario: {s['SHEDULE'] or 'sin dato'}"
        for km, s in con_distancia
    ]
    return "\n".join(lineas) + "\nLas distancias son en línea recta, no por carretera."


def ciudades_con_atencion_en(departamento: str = "") -> str:
    """Ciudades de Colombia con sede o punto de atención, agrupadas por departamento; el total lo cuenta el código."""
    por_departamento: dict[str, set[str]] = {}
    for s in _sedes_de_colombia():
        if _contiene_alguno(s["DEPARTMENT"], departamento):
            por_departamento.setdefault(s["DEPARTMENT"], set()).add(s["CITY"])
    if not por_departamento:
        return SIN_RESULTADOS
    lineas = [f"- {dep}: {', '.join(sorted(ciudades))}" for dep, ciudades in sorted(por_departamento.items())]
    total = sum(len(c) for c in por_departamento.values())
    return "\n".join(lineas) + f"\nTotal: {total} {'ciudad' if total == 1 else 'ciudades'}."


class SedesCercanas(EsquemaEstricto):
    """Esquema de entrada de `sedes_cercanas`: o las coordenadas completas o una ciudad."""

    latitud: float | None = Field(None, ge=-90, le=90, description="Latitud de la ubicación del cliente (si la compartió).")
    longitud: float | None = Field(None, ge=-180, le=180, description="Longitud de la ubicación del cliente (si la compartió).")
    ciudad: str = Field("", max_length=80, description="Ciudad del cliente, solo si no compartió su ubicación. Por ejemplo «Cali».")

    @model_validator(mode="after")
    def _punto_completo(self) -> "SedesCercanas":
        if (self.latitud is None) != (self.longitud is None):
            raise ValueError("latitud y longitud van juntas")
        if self.latitud is None and not self.ciudad:
            raise ValueError("falta la ubicación o la ciudad")
        return self


@tool(args_schema=SedesCercanas)
def sedes_cercanas(latitud: float | None = None, longitud: float | None = None, ciudad: str = "") -> str:
    """Encuentra las sedes, tiendas o puntos de atención de Celsia más cercanos al cliente, con la distancia en línea recta.
    Úsala cuando el cliente pregunte cuál es la sede más cercana o comparta su ubicación (latitud y longitud) o diga su ciudad.
    Para listar las sedes de una ciudad concreta usa `consultar_datos`."""
    return sedes_cercanas_a(latitud, longitud, quitar_invisibles(ciudad))


class CiudadesConAtencion(EsquemaEstricto):
    """Esquema de entrada de `ciudades_con_atencion`."""

    departamento: str = Field(
        "",
        max_length=80,
        description="Departamento por el que filtrar («Tolima», «Valle del Cauca»; varios separados por comas). Vacío: todos los de Colombia.",
    )


@tool(args_schema=CiudadesConAtencion)
def ciudades_con_atencion(departamento: str = "") -> str:
    """Lista las ciudades de Colombia donde Celsia tiene sede o punto de atención, agrupadas por departamento, con el total ya contado.
    Úsala para «¿en qué ciudades del Tolima hay oficinas?» o «¿en cuántas ciudades tienen atención?». Para ver las direcciones y los
    horarios de las sedes de una ciudad usa `consultar_datos`."""
    return ciudades_con_atencion_en(quitar_invisibles(departamento))
