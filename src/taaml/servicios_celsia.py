"""Lógica de dos herramientas de servicio al cliente: comprobar si un canal es oficial y estimar la factura.

Son funciones simples que se prueban sin modelo ni red; las herramientas de LangChain (con su esquema Pydantic) están en `agente.py` y
solo las envuelven. Los canales se comparan contra las tablas versionadas de contactos y sedes: nada se inventa.
"""

import json
import re

from taaml.consulta_datos import SEDES, contactos


def _sedes_de_colombia() -> list[dict]:
    return [s for s in json.loads(SEDES.read_text(encoding="utf-8")) if s["COUNTRY"] == "Colombia"]


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
