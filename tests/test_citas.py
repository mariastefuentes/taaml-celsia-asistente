"""La fuente por WhatsApp solo cuando la piden (D61): sin modelos, sin red y sin enviar nada."""

import pytest

from taaml.citas import SIN_EVIDENCIA, SIN_RESPUESTA, SIN_TEXTO, pide_la_fuente, texto_de_fuentes


def _fuente(chunk, documento, fragmento="1 de 3", extracto=""):
    return {"chunk_id": chunk, "documento": documento, "fragmento": fragmento, "fuente": f"https://www.celsia.com/es/{chunk}/", "extracto": extracto}


def _conversacion(texto, fuentes=(), usadas="Usó: buscó en el texto del sitio"):
    return [{"rol": "user", "texto": "pregunta"}, {"rol": "assistant", "texto": texto, "usadas": usadas, "fuentes": list(fuentes)}]


@pytest.mark.parametrize(
    "mensaje",
    [
        "fuente",
        "Fuente?",
        "  FUENTES ",
        "la fuente por favor",
        "¿Cuál es la fuente?",
        "dame la fuente de esa información",
        "me puedes mostrar las fuentes",
        "¿De dónde sacaste eso?",
        "oye, y de donde salió ese dato",
        "¿En qué te basas?",
    ],
)
def test_reconoce_cuando_piden_la_fuente(mensaje):
    assert pide_la_fuente(mensaje)


@pytest.mark.parametrize(
    "mensaje",
    [
        "¿Cuál es la fuente de energía de Celsia?",
        "fuentes renovables",
        "¿Qué fuentes de generación tiene Celsia?",
        "¿De dónde sale el valor de mi factura?",
        "dame la fuente de energía solar",
        "hola",
        "gracias",
        "",
    ],
)
def test_una_pregunta_que_habla_de_fuentes_sigue_para_el_agente(mensaje):
    assert not pide_la_fuente(mensaje)


def test_muestra_documento_fragmento_y_enlace():
    texto = texto_de_fuentes(_conversacion("Hay un plan.", [_fuente("a", "Planes", "2 de 5")]))
    assert texto == "📄 Fuente de mi última respuesta:\n«Planes», fragmento 2 de 5\nhttps://www.celsia.com/es/a/"


def test_pone_primero_el_fragmento_que_apoya_la_respuesta_aunque_la_busqueda_lo_deje_de_segundo():
    fuentes = [_fuente("a", "Noticia"), _fuente("b", "Requisitos")]
    textos = {"a": "Inauguración de una planta solar.", "b": "Para el trámite necesitas la factura reciente y el documento de identidad."}
    texto = texto_de_fuentes(_conversacion("Necesitas tu documento de identidad y una factura reciente.", fuentes), textos)
    assert "«Requisitos»" in texto and "«Noticia»" not in texto


def test_muestra_dos_como_maximo_y_sin_repetir():
    fuentes = [_fuente("a", "Uno"), _fuente("a", "Uno"), _fuente("b", "Dos"), _fuente("c", "Tres")]
    textos = dict.fromkeys("abc", "factura documento identidad")
    texto = texto_de_fuentes(_conversacion("Factura, documento e identidad.", fuentes), textos)
    assert texto.startswith("📄 Fuentes") and texto.count("fragmento") == 2 and "«Tres»" not in texto


def test_dice_cuando_no_tiene_una_fuente_que_mostrar():
    assert texto_de_fuentes([]) == SIN_RESPUESTA
    assert texto_de_fuentes(_conversacion("No tengo esa información.", [_fuente("a", "Otra cosa")])) == SIN_EVIDENCIA
    assert texto_de_fuentes(_conversacion("Hola.", usadas="Respondió sin consultar herramientas")) == SIN_TEXTO
    assert texto_de_fuentes(_conversacion("Hay 3 sedes.", usadas="Usó: consultó las sedes")) == f"{SIN_TEXTO} Usó: consultó las sedes."


# --- por POST /chat, que es por donde entra WhatsApp ---
def _preparar(monkeypatch, pendiente=None):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import api.main as api

    llamadas = []
    monkeypatch.setattr(api, "conversar", lambda mensaje, hilo, usuario: llamadas.append(mensaje) or ("Respuesta del agente.", []))
    monkeypatch.setattr(api, "pendiente_de_aprobacion", lambda hilo: pendiente)
    monkeypatch.setattr(api, "historial_visible", lambda hilo: _conversacion("Hay un plan.", [_fuente("a", "Planes")]))
    monkeypatch.setattr(api, "cargar_fragmentos", lambda: [])
    cliente = TestClient(api.app)
    return llamadas, lambda mensaje: cliente.post("/chat", json={"mensaje": mensaje, "telefono": "573001234567"}).json()


def test_por_telefono_la_fuente_la_contesta_el_programa_sin_llamar_al_modelo(monkeypatch):
    llamadas, escribir = _preparar(monkeypatch)
    respuesta = escribir("fuente")
    assert "«Planes», fragmento 1 de 3" in respuesta["respuesta"] and respuesta["herramientas"] == [] and llamadas == []
    assert escribir("¿Qué planes hay?")["respuesta"] == "Respuesta del agente." and llamadas == ["¿Qué planes hay?"]


def test_con_algo_en_revision_el_mensaje_sigue_su_camino_normal(monkeypatch):
    llamadas, escribir = _preparar(monkeypatch, pendiente={"herramienta": "radicar_reclamo", "args": {}})
    escribir("fuente")
    assert llamadas == ["fuente"]


def test_con_el_historial_real_del_agente(monkeypatch):
    """La cita sale de lo que de verdad queda guardado en la conversación, no de un historial inventado."""
    from langchain_core.messages import AIMessage

    from taaml.agente import conversar, crear_agente, historial_visible
    from test_agente import _FRAGMENTO, ModeloSinTrozos

    monkeypatch.setattr("taaml.agente.buscar", lambda p, k=0, **kw: [_FRAGMENTO])
    llamada = AIMessage(content="", tool_calls=[{"name": "buscar_en_base", "args": {"pregunta": "impuestos"}, "id": "t1"}])
    agente = crear_agente(llm=ModeloSinTrozos(messages=iter([llamada, AIMessage(content="Hay una política de impuestos.")])))
    conversar("¿Qué dice sobre impuestos?", "hilo-cita", agente=agente)
    texto = texto_de_fuentes(historial_visible("hilo-cita", agente=agente))
    assert "«Gobierno corporativo», fragmento 18 de 29" in texto
