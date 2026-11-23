"""Herramientas de servicio al cliente que se suman a las cinco del agente base (una por una, cada una con su esquema y sus pruebas).

La lógica vive en funciones simples que se prueban sin modelo; la herramienta de LangChain solo las envuelve.
"""

import json
import math
import re

from langchain_core.tools import tool
from pydantic import Field, model_validator

from taaml.base_herramientas import EsquemaEstricto
from taaml.consulta_datos import SEDES, SIN_RESULTADOS, _contiene_alguno, _norm, contactos
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


AVISO_NO_FIGURA = (
    "No figura entre los canales oficiales que tengo. Eso no prueba que sea falso, pero no lo uses para dar datos ni pagos: "
    "confírmalo llamando a la línea 01 8000 112 115."
)
DOMINIOS_DE_CELSIA = ("celsia.com", "celsiainternet.com")


def _digitos(valor: str) -> str:
    """Solo los dígitos de un teléfono, sin el indicativo +57 / 57 de Colombia (los canales oficiales se guardan sin él)."""
    d = re.sub(r"\D", "", valor)
    return d[2:] if d.startswith("57") and len(d) in (11, 12) else d


def _anfitrion(enlace: str) -> str:
    """Solo el dominio de un enlace, sin esquema, «www.», ruta ni puerto, en minúsculas."""
    sin_esquema = re.sub(r"^[a-z][a-z0-9+.-]*://", "", enlace.strip().lower())
    return re.sub(r"^www\.", "", re.split(r"[/?#:]", sin_esquema, maxsplit=1)[0])


def _ruta(enlace: str) -> str:
    sin_esquema = re.sub(r"^[a-z][a-z0-9+.-]*://", "", enlace.strip().lower())
    return sin_esquema.split("/", 1)[1].strip("/") if "/" in sin_esquema else ""


def verificar_canal(valor: str) -> str:
    """Dice si un teléfono, correo o enlace figura entre los canales oficiales de Celsia (tablas de contactos y sedes)."""
    valor = valor.strip()
    oficiales = contactos()
    if "@" in valor:
        for c in oficiales:
            if c["tipo"] == "correo" and c["valor"].strip().lower() == valor.lower():
                return f"Sí figura como canal oficial: correo {c['valor']}. {c['para_que_sirve']}."
        if any(valor.lower().endswith("@" + d) for d in DOMINIOS_DE_CELSIA):
            return (
                f"El dominio del correo es de Celsia, pero ese correo no figura entre los canales oficiales que tengo. "
                "Confírmalo llamando a la línea 01 8000 112 115."
            )
        return AVISO_NO_FIGURA
    if re.search(r"[A-Za-z]{2,}\.[A-Za-z]{2,}", valor) or "://" in valor:
        host, ruta = _anfitrion(valor), _ruta(valor)
        mismos = [c for c in oficiales if c["tipo"] == "enlace" and _anfitrion(c["valor"]) == host]
        for c in mismos:
            if _ruta(c["valor"]) == ruta:
                return f"Sí figura como canal oficial: enlace {c['valor']}. {c['para_que_sirve']}."
        if mismos:
            return (
                f"El sitio {host} figura como canal oficial ({mismos[0]['para_que_sirve']}), pero esa dirección exacta no está "
                "en mi lista. Entra mejor por el enlace oficial que te dé el agente o por celsia.com."
            )
        return AVISO_NO_FIGURA
    digitos = _digitos(valor)
    if len(digitos) >= 7:
        for c in oficiales:
            if c["tipo"] in ("telefono", "whatsapp") and _digitos(c["valor"]) == digitos:
                clase = "WhatsApp" if c["tipo"] == "whatsapp" else "teléfono"
                return f"Sí figura como canal oficial: {clase} {c['valor']}. {c['para_que_sirve']}."
        for s in _sedes_de_colombia():
            if s["PHONE"] and _digitos(s["PHONE"]) == digitos:
                return f"Sí figura como teléfono oficial de {s['NAME']} ({s['CITY']}): {s['PHONE']}."
        return AVISO_NO_FIGURA
    return "No entendí qué canal verificar: dame el teléfono, el correo o el enlace completo."


class CanalAVerificar(EsquemaEstricto):
    """Esquema de entrada de `verificar_canal_oficial`."""

    canal: str = Field(min_length=3, max_length=200, description="El teléfono, WhatsApp, correo o enlace que el cliente quiere comprobar, tal como lo escribió.")


@tool(args_schema=CanalAVerificar)
def verificar_canal_oficial(canal: str) -> str:
    """Comprueba si un teléfono, WhatsApp, correo o enlace figura entre los canales oficiales de Celsia. Úsala cuando el cliente
    pregunte si un número, correo o página es de Celsia, o cuando desconfíe de un mensaje o una llamada (posible fraude).
    Responde solo «sí figura» o «no figura»: no digas que algo es falso ni verdadero; si no figura, recomienda llamar a la línea oficial."""
    return verificar_canal(quitar_invisibles(canal))
