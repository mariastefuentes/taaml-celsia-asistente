"""Atajos de intención: saludos, agradecimientos, despedidas y ayuda sin llamar al modelo.

No es un modelo: es un clasificador de reglas cerradas. Normaliza el texto (minúsculas, sin tildes, sin signos, sin
emojis, sin letras repetidas) y solo responde cuando **todo** el mensaje encaja con una de las cuatro intenciones. Si
trae contenido adicional («hola, ¿dónde queda la sede?») devuelve None y el mensaje sigue al agente, que es quien debe
responder con datos. Así se gana latencia y cuota en lo trivial sin arriesgar respuestas equivocadas.

Se usa en `POST /api/chat` (chat web), en `POST /chat` (puente de OpenClaw) y, para el menú con botones, en el webhook
de Meta. Los textos son los mismos en web y OpenClaw; el webhook conserva sus botones.
"""

import re
import unicodedata
from dataclasses import dataclass

TEXTO_SALUDO = (
    "Hola, soy el asistente virtual de Celsia. Puedo ayudarte con sedes, canales, trámites, facturación o reclamos. "
    "¿Qué necesitas?"
)
TEXTO_GRACIAS = "Con gusto. ¿Hay algo más en lo que te pueda ayudar?"
TEXTO_DESPEDIDA = "Gracias por escribir. Si necesitas algo más, aquí estoy."
TEXTO_AYUDA = (
    "Puedo consultar sedes y canales, trámites, cobertura, un estimado de factura, recordar lo que me cuentas y radicar "
    "un reclamo (lo aprueba una persona). Escríbeme tu pregunta. Si algo no lo puedo resolver, te doy la línea 01 8000 112 115."
)

TEXTOS = {"saludo": TEXTO_SALUDO, "agradecimiento": TEXTO_GRACIAS, "despedida": TEXTO_DESPEDIDA, "ayuda": TEXTO_AYUDA}

# El patrón está anclado al inicio y al final: si hay una sola palabra de contenido, no coincide.
_SALUDO = re.compile(
    r"^(hola|buenas|buen dia|buenos dias|buenas tardes|buenas noches|que tal|saludos|hey)"
    r"(\s+(hola|buenas|buen dia|buenos dias|buenas tardes|buenas noches|que tal|saludos|hey))*$"
)
_GRACIAS = re.compile(
    r"^(muchas |mil |un millon de )?gracias"
    r"(\s+(por (todo|tu ayuda|la ayuda|la informacion|escribir)))?"
    r"(\s+gracias)*$"
)
_DESPEDIDA = re.compile(
    r"^(adios|chao|hasta luego|nos vemos|hasta pronto|bye)"
    r"(\s+(adios|chao|hasta luego|nos vemos|hasta pronto|bye))*$"
)
_AYUDA = {
    "menu",
    "/menu",
    "inicio",
    "/inicio",
    "ayuda",
    "/ayuda",
    "que puedes hacer",
    "que sabes hacer",
    "quien eres",
    "en que me puedes ayudar",
    "como funcionas",
    "que mas puedes hacer",
    "para que sirves",
    "que haces",
}

MAXIMO = 80  # una frase más larga no es un saludo; se deja al agente


@dataclass(frozen=True)
class Atajo:
    """La intención reconocida y el texto que se le responde al cliente, sin llamar al modelo."""

    intencion: str
    texto: str


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes, sin signos ni emojis, sin letras repetidas y con espacios simples.

    Se conserva la barra para reconocer `/nuevo`, `/menu` y `/ayuda` como hasta ahora.
    """
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    limpio = re.sub(r"[^a-z0-9/ ]", "", sin_tildes)
    limpio = re.sub(r"(.)\1{2,}", r"\1", limpio)  # «holaaa» y «buuuenas» cuentan como «hola» y «buenas»
    return re.sub(r"\s+", " ", limpio).strip()


def respuesta_rapida(texto: str) -> Atajo | None:
    """La respuesta fija si **todo** el mensaje es un saludo, agradecimiento, despedida o ayuda; si no, None."""
    clave = normalizar(texto)
    if not clave or len(clave) > MAXIMO:
        return None
    if _SALUDO.fullmatch(clave):
        return Atajo("saludo", TEXTO_SALUDO)
    if _GRACIAS.fullmatch(clave):
        return Atajo("agradecimiento", TEXTO_GRACIAS)
    if _DESPEDIDA.fullmatch(clave):
        return Atajo("despedida", TEXTO_DESPEDIDA)
    if clave in _AYUDA:
        return Atajo("ayuda", TEXTO_AYUDA)
    return None
