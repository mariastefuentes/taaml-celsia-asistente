"""Herramientas de servicio al cliente que se suman a las cinco del agente base (una por una, cada una con su esquema y sus pruebas).

La lógica vive en funciones simples que se prueban sin modelo; la herramienta de LangChain solo las envuelve.
"""

import json
import math
import re
from datetime import datetime, timedelta, timezone

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


LINEA_EMERGENCIAS = "123"  # línea nacional de emergencias de Colombia: no sale de los datos de Celsia, es la que el agente da ante un peligro


def canales_de_emergencia_texto() -> str:
    """Los canales para un peligro o una falla eléctrica: la 123 más el WhatsApp de energía, el enlace para reportar un daño y la línea de servicio, sacados de los contactos oficiales."""
    lineas = [f"- Peligro inmediato (cable caído, chispas, humo, descarga): llama a la línea nacional de emergencias {LINEA_EMERGENCIAS}."]
    for c in contactos(tipo="whatsapp", tema="energía")[:1]:
        lineas.append(f"- WhatsApp de atención de energía de Celsia: {c['valor']}.")
    for c in contactos(tipo="enlace", tema="daño")[:1]:
        lineas.append(f"- Reportar un daño o falla del servicio: {c['valor']}")
    for c in contactos(tipo="telefono", tema="servicio al cliente")[:1]:
        lineas.append(f"- Línea de servicio al cliente de Celsia: {c['valor']}.")
    return "\n".join(lineas)


class SinParametros(EsquemaEstricto):
    """Esquema de las herramientas que no piden nada al modelo."""


@tool(args_schema=SinParametros)
def canales_de_emergencia() -> str:
    """Da los canales para un peligro o una falla eléctrica: la línea 123, el WhatsApp de energía de Celsia, el enlace para reportar
    un daño y la línea de servicio. Úsala cuando el cliente describa un peligro eléctrico (cable caído, chispas, humo, descarga) o
    pida cómo reportar una falla o un corte; antes dile qué hacer para estar seguro. No radica nada: para radicar usa `radicar_reclamo`."""
    return canales_de_emergencia_texto()


HUSO_COLOMBIA = timezone(timedelta(hours=-5))  # Colombia no cambia la hora en el año: siempre UTC-5
DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)  # fmt: skip


def fecha_y_hora_texto(ahora: datetime | None = None) -> str:
    """Día de la semana, fecha y hora de Colombia en una frase (nombres en español sin depender del idioma del equipo)."""
    t = (ahora or datetime.now(timezone.utc)).astimezone(HUSO_COLOMBIA)
    return f"Hoy es {DIAS[t.weekday()]} {t.day} de {MESES[t.month - 1]} de {t.year}, {t:%H:%M} (hora de Colombia, UTC-5)."


@tool(args_schema=SinParametros)
def fecha_y_hora_actual() -> str:
    """Devuelve el día de la semana, la fecha y la hora actuales en Colombia. Úsala cuando el cliente pregunte qué día u hora es,
    o si una sede está abierta ahora o abre hoy: compara esta hora con el horario que da `consultar_datos`."""
    return fecha_y_hora_texto()


def pesos(valor: float) -> str:
    """Pesos colombianos con punto de miles y sin decimales: 1234567 → «$1.234.567»."""
    return f"${round(valor):,}".replace(",", ".")


def factura_estimada(consumo_kwh: float, tarifa_cop_kwh: float, cargo_fijo_cop: float = 0, ajuste_pct: float = 0) -> str:
    """Estimado de la factura: energía (kWh × tarifa) + cargo fijo + ajuste porcentual sobre la energía (positivo = contribución, negativo = subsidio)."""
    energia = consumo_kwh * tarifa_cop_kwh
    ajuste = energia * ajuste_pct / 100
    total = energia + cargo_fijo_cop + ajuste
    lineas = [f"- Energía: {consumo_kwh:g} kWh × {pesos(tarifa_cop_kwh)} por kWh = {pesos(energia)}"]
    if cargo_fijo_cop:
        lineas.append(f"- Cargo fijo: {pesos(cargo_fijo_cop)}")
    if ajuste_pct:
        nombre = "Contribución" if ajuste_pct > 0 else "Subsidio"
        lineas.append(f"- {nombre} ({abs(ajuste_pct):g} % de la energía): {'+' if ajuste > 0 else '-'}{pesos(abs(ajuste))}")
    lineas.append(f"Total estimado: {pesos(total)}")
    lineas.append(
        "Es un cálculo con los datos que dio el cliente: no incluye otros cobros de la factura (como alumbrado público o aseo) "
        "y la factura oficial puede variar."
    )
    return "\n".join(lineas)


class FacturaEstimada(EsquemaEstricto):
    """Esquema de entrada de `calcular_factura_estimada`."""

    consumo_kwh: float = Field(gt=0, le=100_000, description="Consumo de energía del mes en kWh, tal como lo dijo el cliente.")
    tarifa_cop_kwh: float = Field(gt=0, le=10_000, description="Precio de cada kWh en pesos. Del cliente o de la base; nunca inventado.")
    cargo_fijo_cop: float = Field(0, ge=0, le=1_000_000, description="Cargo fijo mensual en pesos, solo si el cliente lo dio.")
    ajuste_pct: float = Field(0, ge=-100, le=100, description="Subsidio (negativo) o contribución (positivo) en %, solo si el cliente lo dio.")


@tool(args_schema=FacturaEstimada)
def calcular_factura_estimada(
    consumo_kwh: float, tarifa_cop_kwh: float, cargo_fijo_cop: float = 0, ajuste_pct: float = 0
) -> str:
    """Calcula un estimado de la factura de energía a partir del consumo en kWh y la tarifa por kWh (más cargo fijo y subsidio o
    contribución si el cliente los da). Úsala cuando el cliente dé o pregunte su consumo y quiera saber cuánto pagaría. Si falta la
    tarifa, búscala con `buscar_en_base` o pídesela al cliente (está en su factura); nunca la inventes. El resultado es un estimado."""
    return factura_estimada(consumo_kwh, tarifa_cop_kwh, cargo_fijo_cop, ajuste_pct)


def consumo_aparato(potencia_vatios: float, horas_por_dia: float, dias: int = 30, tarifa_cop_kwh: float | None = None) -> str:
    """kWh que gasta un aparato (vatios × horas × días ÷ 1.000) y, si hay tarifa, lo que cuesta."""
    kwh = potencia_vatios * horas_por_dia * dias / 1000
    texto = f"{potencia_vatios:g} W × {horas_por_dia:g} h al día × {dias} días ÷ 1.000 = {kwh:.2f} kWh"
    if tarifa_cop_kwh is None:
        return texto + ". Sin la tarifa por kWh no puedo calcular el costo: pídesela al cliente (está en su factura)."
    return texto + f", que a {pesos(tarifa_cop_kwh)} por kWh cuestan {pesos(kwh * tarifa_cop_kwh)}. Es un estimado: el consumo real depende del uso."


class ConsumoDeAparato(EsquemaEstricto):
    """Esquema de entrada de `consumo_de_un_aparato`."""

    potencia_vatios: float = Field(gt=0, le=100_000, description="Potencia del aparato en vatios (W), como dice su etiqueta o el cliente. Nunca inventada.")
    horas_por_dia: float = Field(gt=0, le=24, description="Horas que lo usa cada día (hasta 24).")
    dias: int = Field(30, ge=1, le=366, description="Días del período; 30 si el cliente habla de un mes.")
    tarifa_cop_kwh: float | None = Field(None, gt=0, le=10_000, description="Precio del kWh en pesos, solo si el cliente lo dio; si no, déjalo vacío.")


@tool(args_schema=ConsumoDeAparato)
def consumo_de_un_aparato(
    potencia_vatios: float, horas_por_dia: float, dias: int = 30, tarifa_cop_kwh: float | None = None
) -> str:
    """Calcula cuántos kWh gasta un aparato (nevera, bombillo, aire…) y, si hay tarifa, cuánto cuesta, a partir de su potencia en vatios
    y las horas de uso al día. Úsala cuando el cliente pregunte cuánto gasta un aparato. La potencia la da el cliente (viene en la
    etiqueta del aparato): si no la sabe, pídesela y no supongas una; la tarifa, si no la dio, no la inventes."""
    return consumo_aparato(potencia_vatios, horas_por_dia, dias, tarifa_cop_kwh)


def ahorro_solar(consumo_kwh_mes: float, tarifa_cop_kwh: float, porcentaje_cubierto: float) -> str:
    """Ahorro de energía solar bajo un supuesto: qué parte del consumo mensual (en %) cubriría el sistema, al precio actual del kWh."""
    kwh_solar = consumo_kwh_mes * porcentaje_cubierto / 100
    mensual = kwh_solar * tarifa_cop_kwh
    return (
        f"Si la energía solar cubriera el {porcentaje_cubierto:g} % de {consumo_kwh_mes:g} kWh al mes, serían {kwh_solar:.1f} kWh menos "
        f"comprados a {pesos(tarifa_cop_kwh)} por kWh: ahorro de {pesos(mensual)} al mes, {pesos(mensual * 12)} al año. "
        "Es un escenario con el porcentaje indicado, no una promesa: no incluye el costo de instalación ni el mantenimiento, "
        "y la cobertura real depende del sistema y del lugar. Para una cotización real, un asesor de Celsia debe visitar el sitio."
    )


class AhorroSolar(EsquemaEstricto):
    """Esquema de entrada de `estimar_ahorro_solar`."""

    consumo_kwh_mes: float = Field(gt=0, le=1_000_000, description="Consumo mensual de energía en kWh, según el cliente.")
    tarifa_cop_kwh: float = Field(gt=0, le=10_000, description="Precio del kWh en pesos. Del cliente o de la base; nunca inventado.")
    porcentaje_cubierto: float = Field(
        gt=0, le=100, description="Qué parte del consumo (en %) cubriría la energía solar. La dice el cliente; si no, un escenario que se presenta como hipotético."
    )


@tool(args_schema=AhorroSolar)
def estimar_ahorro_solar(consumo_kwh_mes: float, tarifa_cop_kwh: float, porcentaje_cubierto: float) -> str:
    """Estima cuánto ahorraría un cliente al mes y al año si la energía solar cubriera una parte de su consumo. Úsala cuando el
    cliente pregunte cuánto ahorraría con paneles solares. Necesita el consumo mensual y la tarifa por kWh (si faltan, pídelos o
    busca la tarifa con `buscar_en_base`; nunca los inventes). El porcentaje que cubriría lo dice el cliente; si no lo sabe, usa un
    escenario (por ejemplo 50 %) y di claramente que es hipotético. No incluye el costo de instalación ni promete resultados."""
    return ahorro_solar(consumo_kwh_mes, tarifa_cop_kwh, porcentaje_cubierto)
