"""Limpieza de caracteres invisibles (contrabando Unicode).

Hay caracteres que el ojo no ve pero el tokenizer sí: espacios de ancho cero, controles de dirección, «etiquetas» Unicode
(U+E0000–U+E007F) y selectores de variación. Sirven para esconder instrucciones dentro de un texto que parece inocente
(una pregunta del usuario o una página scrapeada) y, sin mala intención, ensucian el corpus (una palabra partida por
U+200B no coincide al buscar). Se eliminan en las dos puertas: la entrada del usuario y la construcción del corpus.
"""

import unicodedata

CONSERVAR = {"\n", "\t", "\r"}  # los únicos controles legítimos en un texto
SELECTORES_VARIACION = set(range(0xFE00, 0xFE10)) | set(range(0xE0100, 0xE01F0))


def _es_invisible(caracter: str) -> bool:
    if caracter in CONSERVAR:
        return False
    # Cf: formato (ancho cero, dirección, guion blando, etiquetas Unicode); Cc: controles; Co/Cs: uso privado y sustitutos sueltos
    return unicodedata.category(caracter) in ("Cf", "Cc", "Co", "Cs") or ord(caracter) in SELECTORES_VARIACION


def quitar_invisibles(texto: str) -> str:
    """Devuelve el texto sin caracteres invisibles. Quita también el ZWJ y el selector de emoji (los emojis compuestos se ven más simples)."""
    return "".join(c for c in texto if not _es_invisible(c))


def contar_invisibles(texto: str) -> int:
    """Cuántos caracteres invisibles trae el texto (para medir y reportar)."""
    return sum(_es_invisible(c) for c in texto)
