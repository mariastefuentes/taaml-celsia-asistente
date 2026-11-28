"""Atajos de intención: variantes que sí son triviales y mensajes con contenido que deben seguir al agente."""

import pytest

from taaml.atajos import normalizar, respuesta_rapida


@pytest.mark.parametrize(
    ("texto", "intencion"),
    [
        ("Hola", "saludo"),
        ("Holaaa!!", "saludo"),
        ("  ¡HOLA! 👋  ", "saludo"),
        ("Buenos días", "saludo"),
        ("Buenas tardes", "saludo"),
        ("Hola, buenas tardes", "saludo"),
        ("¿Qué tal?", "saludo"),
        ("Mil gracias", "agradecimiento"),
        ("Muchas gracias por tu ayuda", "agradecimiento"),
        ("Gracias", "agradecimiento"),
        ("Chao, nos vemos", "despedida"),
        ("Adiós", "despedida"),
        ("Hasta luego", "despedida"),
        ("Menú", "ayuda"),
        ("¿Qué puedes hacer?", "ayuda"),
        ("¿Quién eres?", "ayuda"),
        ("En qué me puedes ayudar", "ayuda"),
    ],
)
def test_reconoce_las_variantes_triviales(texto, intencion):
    atajo = respuesta_rapida(texto)
    assert atajo is not None
    assert atajo.intencion == intencion
    assert atajo.texto.strip()


@pytest.mark.parametrize(
    "texto",
    [
        "Hola, ¿dónde queda la sede de Ibagué?",
        "Buenas, necesito un reclamo",
        "Ayuda con mi factura",
        "¿Qué puedes hacer para bajar mi consumo?",
        "Gracias, pero quiero cambiar mi factura",
        "Hola, quiero saber mi saldo",
        "Chao, pero antes dime una sede",
        "Hello",
        "",
        "   ",
        "?!",
    ],
)
def test_no_secuestra_mensajes_con_contenido(texto):
    assert respuesta_rapida(texto) is None


def test_normaliza_tildes_mayusculas_signos_emojis_y_letras_repetidas():
    assert normalizar("  ¡HOLAAA!! 👋  ") == "hola"
    assert normalizar("Buuuenas tardes") == "buenas tardes"
    assert normalizar("¿Qué tal?") == "que tal"


def test_las_cuatro_respuestas_son_textos_distintos():
    textos = {respuesta_rapida(t).texto for t in ("hola", "gracias", "chao", "menú")}
    assert len(textos) == 4
