"""Herramientas de servicio al cliente que se suman a las cinco del agente base (una por una, cada una con su esquema y sus pruebas).

La lógica vive en funciones simples que se prueban sin modelo; la herramienta de LangChain solo las envuelve.
"""

import json
import math
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from langchain_core.tools import tool
from langchain.tools import ToolRuntime
from pydantic import Field, field_validator, model_validator

from taaml.base_herramientas import ANONIMO, Contexto, EsquemaConRuntime, EsquemaEstricto, _almacen
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
                "El dominio del correo es de Celsia, pero ese correo no figura entre los canales oficiales que tengo. "
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


NUMERO_RECLAMO = re.compile(r"^REC-[0-9A-F]{8}$")
TIPOS_DE_RECLAMO = {"falla_de_servicio": "falla del servicio", "facturacion": "facturación", "otro": "otro"}


def estado_de_reclamo(almacen, usuario: str, numero: str) -> str:
    """Busca un radicado entre los reclamos de ESTE cliente (el espacio del Store es suyo) y dice qué figura, sin inventar un estado de gestión."""
    if usuario == ANONIMO:
        return "No puedo consultarlo: no hay un cliente identificado, y los reclamos se ven solo desde la cuenta de quien los radicó."
    item = almacen.get(("reclamos", usuario), numero)
    if item is None:
        return f"No encontré el radicado {numero} entre los reclamos de este cliente. Revisa que el número esté bien escrito o llama a la línea 01 8000 112 115."
    r = item.value
    fecha = item.created_at.astimezone(HUSO_COLOMBIA)
    adicionales = r.get("detalles", [])
    extra = (" Información agregada después: " + " | ".join(adicionales) + ".") if adicionales else ""
    return (
        f"El radicado {numero} figura radicado el {fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}. "
        f"Tipo: {TIPOS_DE_RECLAMO.get(r.get('tipo'), 'otro')}. Ciudad: {r.get('ciudad', 'sin dato')}. Lo que se reportó: {r.get('descripcion', 'sin dato')}.{extra} "
        "Desde aquí no veo si ya lo están gestionando ni en qué estado va: para eso llama a la línea 01 8000 112 115 con el número de radicado."
    )


class EstadoDeReclamo(EsquemaConRuntime):
    """Esquema de entrada de `consultar_estado_reclamo`."""

    numero: str = Field(description="Número de radicado del reclamo, con la forma REC-XXXXXXXX (letras A-F y números).")

    @field_validator("numero", mode="before")
    @classmethod
    def _formato(cls, v: object) -> object:
        v = str(v).strip().upper()
        if not NUMERO_RECLAMO.match(v):
            raise ValueError("el radicado tiene la forma REC- y 8 caracteres (números o letras A-F)")
        return v


@tool(args_schema=EstadoDeReclamo)
def consultar_estado_reclamo(numero: str, runtime: ToolRuntime[Contexto]) -> str:
    """Consulta un reclamo que este cliente radicó antes, por su número de radicado (REC-…). Úsala cuando el cliente pregunte por
    su reclamo o por un radicado. Solo ve los reclamos del propio cliente. Dice qué se radicó y cuándo, no el estado de gestión de
    Celsia (no lo tiene): para eso remite a la línea 01 8000 112 115. Si no tiene el número, usa `listar_mis_reclamos`."""
    return estado_de_reclamo(_almacen(runtime), runtime.context.usuario, numero)


MAX_RECLAMOS_LISTADOS = 10


def reclamos_del_cliente(almacen, usuario: str) -> str:
    """Los reclamos que ESTE cliente radicó, del más reciente al más antiguo; el total lo cuenta el código."""
    if usuario == ANONIMO:
        return "No puedo listarlos: no hay un cliente identificado, y los reclamos se ven solo desde la cuenta de quien los radicó."
    items = sorted(almacen.search(("reclamos", usuario), limit=100), key=lambda i: i.created_at, reverse=True)
    if not items:
        return "Este cliente no tiene reclamos radicados desde este servicio."
    lineas = []
    for i in items[:MAX_RECLAMOS_LISTADOS]:
        f = i.created_at.astimezone(HUSO_COLOMBIA)
        lineas.append(
            f"- {i.key}: {f.day} de {MESES[f.month - 1]} de {f.year}, {TIPOS_DE_RECLAMO.get(i.value.get('tipo'), 'otro')}, "
            f"{i.value.get('ciudad', 'sin dato')}: {str(i.value.get('descripcion', ''))[:100]}"
        )
    total = f"Total: {len(items)} {'reclamo' if len(items) == 1 else 'reclamos'}"
    lineas.append(f"{total} (se muestran los {MAX_RECLAMOS_LISTADOS} más recientes)." if len(items) > MAX_RECLAMOS_LISTADOS else f"{total}.")
    return "\n".join(lineas)


class SoloElCliente(EsquemaConRuntime):
    """Esquema de las herramientas que no piden nada al modelo y solo miran lo del cliente actual."""


@tool(args_schema=SoloElCliente)
def listar_mis_reclamos(runtime: ToolRuntime[Contexto]) -> str:
    """Lista los reclamos que este cliente radicó (número, fecha, tipo, ciudad y qué reportó), del más reciente al más antiguo, con el
    total ya contado. Úsala cuando el cliente pregunte qué reclamos tiene, cuántos ha puesto o no recuerde el número de su radicado.
    Solo ve los del propio cliente. No dice el estado de gestión de Celsia (no lo tiene)."""
    return reclamos_del_cliente(_almacen(runtime), runtime.context.usuario)


MAX_DETALLES_POR_RECLAMO = 5


def agregar_detalle(almacen, usuario: str, numero: str, detalle: str) -> str:
    """Añade una nota a un reclamo ya radicado de ESTE cliente (no cambia lo radicado: queda como información adicional)."""
    if usuario == ANONIMO:
        return "No se agregó: no hay un cliente identificado, y solo se puede ampliar un reclamo desde la cuenta de quien lo radicó."
    detalle = quitar_invisibles(detalle).strip()[:300]
    if not detalle:
        return "No se agregó: el detalle está vacío."
    espacio = ("reclamos", usuario)
    item = almacen.get(espacio, numero)
    if item is None:
        return f"No se agregó: no encontré el radicado {numero} entre los reclamos de este cliente."
    valor = dict(item.value)
    detalles = list(valor.get("detalles", []))
    if detalle in detalles:
        return "Ese detalle ya estaba agregado al reclamo."
    if len(detalles) >= MAX_DETALLES_POR_RECLAMO:
        return f"No se agregó: el reclamo ya tiene {MAX_DETALLES_POR_RECLAMO} detalles adicionales. Para más, llama a la línea 01 8000 112 115."
    valor["detalles"] = detalles + [detalle]
    almacen.put(espacio, numero, valor)
    return (
        f"Agregado al reclamo {numero}. Queda como información adicional; lo ya radicado no cambia y la gestión de Celsia sigue siendo la misma."
    )


class DetalleDeReclamo(EstadoDeReclamo):
    """Esquema de entrada de `agregar_detalle_a_reclamo`: el radicado (con su misma validación) y lo que se agrega."""

    detalle: str = Field(min_length=1, max_length=300, description="Lo que el cliente quiere añadir, en sus palabras (sin cédulas, claves ni tarjetas).")


@tool(args_schema=DetalleDeReclamo)
def agregar_detalle_a_reclamo(numero: str, detalle: str, runtime: ToolRuntime[Contexto]) -> str:
    """Agrega información nueva a un reclamo que este cliente ya radicó (por ejemplo, un dato que faltaba o algo que cambió). Úsala
    cuando el cliente quiera ampliar su reclamo y dé el número de radicado (si no lo sabe, usa antes `listar_mis_reclamos`). No
    cambia lo radicado: queda como nota adicional. Para un reclamo nuevo usa `radicar_reclamo`. Nunca guardes cédulas, claves ni tarjetas."""
    return agregar_detalle(_almacen(runtime), runtime.context.usuario, numero, detalle)


MAX_SOLICITUDES_ABIERTAS = 3
LINEAS_PARA_HABLAR_CON_UNA_PERSONA = (
    "Mientras tanto puedes hablar con una persona llamando a la línea 01 8000 112 115 o escribiendo al WhatsApp de energía +57 310 390 3468."
)


def solicitar_asesor(almacen, usuario: str, motivo: str) -> str:
    """Deja anotado que el cliente pide hablar con una persona (no hay transferencia en vivo) y le da los canales que sí atienden."""
    if usuario == ANONIMO:
        return "No pude dejar la solicitud: no hay un cliente identificado. " + LINEAS_PARA_HABLAR_CON_UNA_PERSONA
    motivo = quitar_invisibles(motivo).strip()[:300]
    if not motivo:
        return "No se registró: falta el motivo."
    espacio = ("escalamientos", usuario)
    existentes = almacen.search(espacio, limit=MAX_SOLICITUDES_ABIERTAS + 1)
    if any(e.value["motivo"] == motivo for e in existentes):
        return "Esa solicitud ya estaba registrada. " + LINEAS_PARA_HABLAR_CON_UNA_PERSONA
    if len(existentes) >= MAX_SOLICITUDES_ABIERTAS:
        return f"Ya hay {MAX_SOLICITUDES_ABIERTAS} solicitudes registradas de este cliente. " + LINEAS_PARA_HABLAR_CON_UNA_PERSONA
    numero = f"ESC-{uuid4().hex[:8].upper()}"
    almacen.put(espacio, numero, {"motivo": motivo})
    return (
        f"Dejé anotada tu solicitud {numero} para que una persona de Celsia la vea. En esta demostración no hay una transferencia en vivo "
        f"ni un tiempo de respuesta confirmado. {LINEAS_PARA_HABLAR_CON_UNA_PERSONA}"
    )


class SolicitudDeAsesor(EsquemaConRuntime):
    """Esquema de entrada de `escalar_a_asesor`."""

    motivo: str = Field(min_length=1, max_length=300, description="Por qué quiere hablar con una persona, con las palabras del cliente (sin cédulas, claves ni tarjetas).")


@tool(args_schema=SolicitudDeAsesor)
def escalar_a_asesor(motivo: str, runtime: ToolRuntime[Contexto]) -> str:
    """Deja anotada la solicitud del cliente de hablar con una persona (un asesor humano) y le da los canales para hacerlo ya.
    Úsala cuando el cliente pida hablar con una persona o un asesor, o cuando no puedas resolver su caso. No hay transferencia en vivo
    ni tiempo de respuesta: nunca prometas que lo llamarán o que lo atenderán pronto. Para un reclamo usa `radicar_reclamo`."""
    return solicitar_asesor(_almacen(runtime), runtime.context.usuario, motivo)


MAX_CALIFICACIONES = 10


def registrar_calificacion(almacen, usuario: str, puntaje: int, comentario: str = "") -> str:
    """Guarda la calificación (1 a 5) que el cliente da a la atención recibida, con un comentario opcional."""
    if usuario == ANONIMO:
        return "No pude guardar la calificación: no hay un cliente identificado. Gracias por tomarte el tiempo de opinar."
    if not isinstance(puntaje, int) or isinstance(puntaje, bool) or not 1 <= puntaje <= 5:
        return "No se registró: la calificación debe ser un número entero de 1 a 5."
    comentario = quitar_invisibles(comentario or "").strip()[:300]
    espacio = ("calificaciones", usuario)
    if len(almacen.search(espacio, limit=MAX_CALIFICACIONES + 1)) >= MAX_CALIFICACIONES:
        return f"Ya hay {MAX_CALIFICACIONES} calificaciones registradas de este cliente; no se guardan más."
    numero = f"CAL-{uuid4().hex[:8].upper()}"
    almacen.put(espacio, numero, {"puntaje": puntaje, "comentario": comentario})
    return f"Gracias, quedó registrada tu calificación {numero}: {puntaje} de 5." + (" También guardé tu comentario." if comentario else "")


class CalificacionDeAtencion(EsquemaConRuntime):
    """Esquema de entrada de `calificar_atencion`."""

    puntaje: int = Field(ge=1, le=5, description="Calificación de la atención, un número entero de 1 (muy mala) a 5 (excelente).")
    comentario: str = Field(default="", max_length=300, description="Comentario opcional del cliente, con sus palabras (sin cédulas, claves ni tarjetas).")


@tool(args_schema=CalificacionDeAtencion)
def calificar_atencion(puntaje: int, runtime: ToolRuntime[Contexto], comentario: str = "") -> str:
    """Registra la calificación (de 1 a 5) que el cliente da a la atención recibida, con un comentario opcional. Úsala solo cuando
    el cliente diga o dé una calificación; nunca inventes el puntaje ni lo pidas con insistencia. No es un reclamo: para quejas
    formales usa `radicar_reclamo`."""
    return registrar_calificacion(_almacen(runtime), runtime.context.usuario, puntaje, comentario)


def resumen_de_actividad(almacen, usuario: str) -> str:
    """Cuenta lo que hay guardado del cliente (datos, reclamos, solicitudes de asesor y calificaciones), sin repetir su contenido."""
    if usuario == ANONIMO:
        return "No hay un cliente identificado: de un cliente anónimo no se guarda nada."
    datos = almacen.search(("perfil", usuario), limit=100)
    reclamos = sorted(almacen.search(("reclamos", usuario), limit=1000), key=lambda i: i.created_at, reverse=True)
    solicitudes = almacen.search(("escalamientos", usuario), limit=100)
    calificaciones = almacen.search(("calificaciones", usuario), limit=100)
    if not (datos or reclamos or solicitudes or calificaciones):
        return "No hay nada guardado de este cliente todavía."
    lineas = [
        f"- Datos que contó de sí mismo: {len(datos)}.",
        f"- Reclamos radicados: {len(reclamos)}" + (f" (el más reciente: {reclamos[0].key})." if reclamos else "."),
        f"- Solicitudes para hablar con una persona: {len(solicitudes)}.",
    ]
    if calificaciones:
        promedio = sum(c.value["puntaje"] for c in calificaciones) / len(calificaciones)
        lineas.append(f"- Calificaciones de la atención: {len(calificaciones)} (promedio {promedio:.1f} de 5).")
    else:
        lineas.append("- Calificaciones de la atención: 0.")
    return "Esto es lo que hay guardado de este cliente:\n" + "\n".join(lineas)


@tool(args_schema=SoloElCliente)
def resumen_de_mi_actividad(runtime: ToolRuntime[Contexto]) -> str:
    """Resume lo que hay guardado del cliente: cuántos datos suyos, reclamos, solicitudes de asesor y calificaciones, y su reclamo más
    reciente. Úsala cuando el cliente pregunte qué hay guardado de él o cuál es su actividad con Celsia en general. Para el detalle de
    un reclamo usa `consultar_estado_reclamo`; para lo que contó de sí mismo, `recordar_datos_del_cliente`."""
    return resumen_de_actividad(_almacen(runtime), runtime.context.usuario)
