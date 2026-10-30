"""Diccionario de sinónimos hecho a mano: une el lenguaje del cliente con el del sitio de Celsia.

El cliente pregunta «si me atraso con el pago» y el sitio habla de «intereses de mora» y «suspensión del servicio». El
buscador por significado no siempre los conecta. Cada grupo de este diccionario se usa de dos formas, con la misma lista:
  - en la pregunta: si encaja `pregunta`, se le agregan los `terminos` antes de buscar (`ampliar_consulta`);
  - en los fragmentos: si el texto del fragmento encaja `fragmento`, el índice de embeddings lo calcula con los `terminos`
    como etiqueta (`etiquetas_fragmento`). El texto que lee el modelo no cambia: solo cambia dónde lo ubica el buscador.

Es un parche deliberado: solo cubre los temas escritos aquí y no generaliza a preguntas nuevas. Los términos salen del
vocabulario del propio sitio (se verificaron en la base de conocimiento); no se agrega ningún dato nuevo.
Si se edita un grupo, hay que volver a ejecutar scripts/07_construir_indice.py (solo recalcula los fragmentos afectados).
"""
import re

GRUPOS = [
    {   # qué pasa si no pago a tiempo (C8)
        "pregunta": r"atras|\bmora\b|no (he |puedo )?pag|vencid|deuda|me (cortan|suspenden)|corte por (falta de )?pago",
        "fragmento": r"intereses de mora|costos asociados a la suspensi[oó]n del servicio|acuerdo de pago",
        "terminos": "qué pasa si no pago a tiempo la factura: intereses de mora, suspensión del servicio, reconexión, acuerdo de pago",
    },
    {   # cultura y valores (G10)
        "pregunta": r"\bvalores\b|principios|\bcultura\b|prop[oó]sito|c[oó]mo es (la empresa|trabajar)",
        "fragmento": r"cultura de principios y valores|\bun ADN\b|cultura naranja|Cultura Celsia",
        "terminos": "valores de Celsia, Cultura Celsia, cultura de principios y valores, el respeto es la base, nuestro ADN",
    },
    {   # historia y nombre anterior (G3)
        "pregunta": r"desde cu[aá]ndo|historia|fundad|fundaci[oó]n|antes se llamaba|c[oó]mo naci[oó]|nombre anterior",
        "fragmento": r"Colinversiones|Hitos estrat[eé]gicos",
        "terminos": "historia de Celsia, hitos estratégicos, Colinversiones, cambio de nombre, desde cuándo existe",
    },
]

_PREGUNTA = [re.compile(g["pregunta"], re.I) for g in GRUPOS]
_FRAGMENTO = [re.compile(g["fragmento"], re.I) for g in GRUPOS]


def ampliar_consulta(pregunta: str) -> str:
    """La pregunta seguida de los términos de los grupos que encajan (igual si ninguno encaja)."""
    extra = [g["terminos"] for g, rx in zip(GRUPOS, _PREGUNTA) if rx.search(pregunta)]
    return f"{pregunta} {' '.join(extra)}" if extra else pregunta


def etiquetas_fragmento(texto: str) -> str:
    """Los términos de los grupos que encajan con el fragmento (vacío si ninguno), para calcular su embedding."""
    return " ".join(g["terminos"] for g, rx in zip(GRUPOS, _FRAGMENTO) if rx.search(texto))
