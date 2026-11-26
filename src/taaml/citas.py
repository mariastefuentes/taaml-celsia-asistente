"""La fuente de una respuesta, solo cuando el cliente la pide (WhatsApp y `POST /chat`).

El chat web muestra las fuentes en pantalla. En WhatsApp las respuestas salen limpias y, si el cliente escribe «fuente» o pregunta de dónde
salió el dato, contesta este módulo con lo que quedó guardado en la conversación: documento, fragmento y enlace de la última respuesta.
No llama al modelo, así que no puede inventar una cita ni gasta cuota.
"""

import re
import unicodedata

MAXIMO_FUENTES = 2  # en el celular más de dos no se leen
CERCANIA = 0.6  # la segunda fuente sale solo si coincide con la respuesta casi tanto como la primera

SIN_RESPUESTA = "Todavía no te he dado una respuesta de la que pueda mostrarte la fuente. Hazme primero una pregunta sobre Celsia."
SIN_EVIDENCIA = "En mi última respuesta no encontré esa información, así que no tengo una fuente que mostrarte."
SIN_TEXTO = "Mi última respuesta no salió de un texto del sitio de Celsia, así que no tengo un fragmento que mostrarte."

# El mensaje entero tiene que ser la petición: «¿cuál es la fuente de energía de Celsia?» es una pregunta para el agente.
_PETICION = re.compile(
    r"(?:(?:me )?(?:puedes |podrias )?"
    r"(?:dame|darme|dar|das|muestrame|mostrarme|mostrar|muestras|enviame|enviarme|enviar|envias|mandame|mandarme|mandar|mandas|pasame|pasar|pasas|ver|quiero ver|cual es|cuales son) )?"
    r"(?:la |las )?fuentes?(?: de (?:eso|esa informacion|ese dato|esa respuesta))?"
    r"|de donde (?:sacaste|sacas|salio|sale|viene|obtuviste) (?:eso|esa informacion|esta informacion|ese dato|esa respuesta)"
    r"|(?:y )?en que (?:te )?basas(?: para decir(?:lo| eso))?"
)
_CORTESIA = re.compile(r"^(?:hola |oye |y )+|(?: por favor| porfa| gracias)+$|^(?:por favor |porfa )")
_SIN_EVIDENCIA = re.compile(r"no tengo esa informacion")


def _plano(texto: str) -> str:
    """Minúsculas, sin tildes ni signos y con un solo espacio entre palabras."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", sin_tildes))


def pide_la_fuente(mensaje: str) -> bool:
    """Si el mensaje completo es una petición de la fuente de la respuesta anterior."""
    plano = _plano(mensaje)
    while (recortado := _CORTESIA.sub("", plano)) != plano:
        plano = recortado
    return bool(_PETICION.fullmatch(plano))


def _palabras(texto: str) -> set[str]:
    return {p for p in _plano(texto).split() if len(p) >= 4 and p != "celsia"}


def _las_que_apoyan(fuentes: list[dict], respuesta: str, textos: dict[str, str]) -> list[dict]:
    """Las fuentes que más palabras comparten con la respuesta, primero la mejor (la búsqueda no siempre deja de primera la que se usó)."""
    dichas = _palabras(respuesta)
    unicas = list({f["chunk_id"]: f for f in fuentes}.values())
    puntos = {f["chunk_id"]: len(dichas & _palabras(textos.get(f["chunk_id"]) or f.get("extracto", ""))) for f in unicas}
    ordenadas = sorted(unicas, key=lambda f: -puntos[f["chunk_id"]])  # en empate se respeta el orden de la búsqueda
    mejor = puntos[ordenadas[0]["chunk_id"]]
    cercanas = [f for f in ordenadas[1:] if mejor and puntos[f["chunk_id"]] >= CERCANIA * mejor]
    return [ordenadas[0], *cercanas][:MAXIMO_FUENTES]


def texto_de_fuentes(conversacion: list[dict], textos: dict[str, str] | None = None) -> str:
    """La contestación a «fuente», a partir de la conversación visible (`agente.historial_visible`).

    `textos` trae el texto completo de cada fragmento por su `chunk_id`; sin él se compara con el extracto guardado.
    """
    ultima = next((m for m in reversed(conversacion) if m["rol"] == "assistant"), None)
    if not ultima:
        return SIN_RESPUESTA
    if _SIN_EVIDENCIA.search(_plano(ultima["texto"])):
        return SIN_EVIDENCIA
    if not ultima.get("fuentes"):
        usadas = ultima.get("usadas", "")
        return f"{SIN_TEXTO} {usadas}." if usadas.startswith("Usó: ") else SIN_TEXTO
    elegidas = _las_que_apoyan(ultima["fuentes"], ultima["texto"], textos or {})
    bloques = [f"«{f['documento']}», fragmento {f['fragmento']}\n{f['fuente']}" for f in elegidas]
    titulo = "📄 Fuente de mi última respuesta:" if len(bloques) == 1 else "📄 Fuentes de mi última respuesta:"
    return "\n\n".join([f"{titulo}\n{bloques[0]}", *bloques[1:]])
