"""Post-validación: cada cifra, correo o enlace de la respuesta debe poder rastrearse hasta un fragmento recuperado.

No llama a ningún modelo y no cambia la respuesta: solo devuelve lo que no tiene respaldo, para avisar a quien lee.
Es una revisión de texto (¿aparece escrito?), no de significado: un número correcto usado en otro contexto pasa la prueba.
"""
import re

from taaml.prompts import construir_prompt_sistema

PATRON_URL = re.compile(r"https?://[^\s)>\]\"']+", re.I)
PATRON_CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PATRON_NUMERO = re.compile(r"\d+(?:[ .,-]\d+)*")  # un teléfono o un precio con separadores cuenta como un solo número
PATRON_ENUMERACION = re.compile(r"^\s*(?:[-*]\s+)?\d+[.)]\s+", re.M)  # «1. » al inicio de una línea no es una cifra


def _solo_digitos(numero: str) -> str:
    return re.sub(r"\D", "", numero)


def _url(url: str) -> str:
    return url.rstrip(".,;:").rstrip("/").lower()


def _numeros(texto: str) -> set[str]:
    """Cada número del texto, entero y también por partes («01 8000 112 115» y «018000112115» se aceptan)."""
    valores = set()
    for numero in PATRON_NUMERO.findall(texto):
        valores.add(_solo_digitos(numero))
        valores.update(re.findall(r"\d+", numero))
    return valores


def datos_sin_respaldo(respuesta: str, fragmentos: list[dict]) -> list[str]:
    """Devuelve las cifras, correos y enlaces de `respuesta` que no están escritos en los `fragmentos` ni en las instrucciones del asistente.

    Las instrucciones cuentan como fuente porque traen la línea 01 8000 112 115, que el asistente da cuando no encuentra la respuesta.
    """
    fuente = "\n".join([construir_prompt_sistema("")] + [f"{f['texto']}\n{f.get('fuente', '')}" for f in fragmentos])
    sin_enumerar = PATRON_ENUMERACION.sub("", respuesta)
    sin_respaldo = []
    urls_fuente = {_url(u) for u in PATRON_URL.findall(fuente)}
    for url in dict.fromkeys(PATRON_URL.findall(sin_enumerar)):
        if _url(url) not in urls_fuente:
            sin_respaldo.append(url.rstrip(".,;:"))
    correos_fuente = {c.lower() for c in PATRON_CORREO.findall(fuente)}
    for correo in dict.fromkeys(PATRON_CORREO.findall(sin_enumerar)):
        if correo.lower() not in correos_fuente:
            sin_respaldo.append(correo)
    sin_urls = PATRON_CORREO.sub("", PATRON_URL.sub("", sin_enumerar))  # los números de un enlace ya se revisaron con el enlace
    numeros_fuente = _numeros(fuente)
    vistos = set()
    for numero in PATRON_NUMERO.findall(sin_urls):
        digitos = _solo_digitos(numero)
        # los de una sola cifra («paso 2», «1 vez») no se validan: casi siempre son conteos del texto
        respaldado = digitos in numeros_fuente or all(p in numeros_fuente for p in re.findall(r"\d+", numero))
        if len(digitos) >= 2 and not respaldado and digitos not in vistos:
            vistos.add(digitos)
            sin_respaldo.append(numero.rstrip(".,"))
    return sin_respaldo
