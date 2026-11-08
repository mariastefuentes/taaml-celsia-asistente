from streamlit.testing.v1 import AppTest

from conftest import RAIZ
from taaml.agente import etiqueta_herramientas


def test_etiqueta_sin_herramientas():
    assert etiqueta_herramientas([]) == "Respondió sin consultar herramientas"


def test_etiqueta_de_datos_muestra_tabla_y_filtros():
    llamadas = [{"herramienta": "consultar_datos", "args": {"tabla": "sedes", "ciudad": "Ibagué", "tipo": ""}}]
    assert etiqueta_herramientas(llamadas) == "Usó: consultó la tabla sedes (ciudad: Ibagué)"


def test_etiqueta_de_texto_y_de_ambas():
    texto = {"herramienta": "buscar_en_base", "args": {"pregunta": "cancelar"}}
    datos = {"herramienta": "consultar_datos", "args": {"tabla": "contactos", "tipo": "whatsapp"}}
    assert etiqueta_herramientas([texto]) == "Usó: buscó en el texto del sitio"
    assert etiqueta_herramientas([datos, texto]).startswith("Usó: consultó la tabla contactos (tipo: whatsapp); buscó")


def _app(monkeypatch, respuestas):
    visto = []

    def falso(pregunta, thread_id, *args, **kwargs):
        visto.append((pregunta, thread_id))
        return respuestas.pop(0)

    monkeypatch.setattr("taaml.agente.conversar", falso)
    at = AppTest.from_file(str(RAIZ / "app" / "asistente.py"), default_timeout=30)
    at.run()
    return at, visto


def test_la_pestana_agente_existe_y_muestra_la_respuesta_con_su_etiqueta(monkeypatch):
    llamadas = [{"herramienta": "consultar_datos", "args": {"tabla": "sedes", "ciudad": "Ibagué"}}]
    at, visto = _app(monkeypatch, [("Hay sedes en Ibagué.", llamadas)])
    assert "Agente" in [t.label for t in at.tabs]
    at.chat_input[0].set_value("¿Sedes en Ibagué?").run()
    assert not at.exception
    assert "Hay sedes en Ibagué." in [m.value for m in at.markdown]
    assert any("consultó la tabla sedes" in c.value for c in at.caption)
    assert visto[0][0] == "¿Sedes en Ibagué?"


def test_la_conversacion_conserva_el_hilo_y_nueva_conversacion_lo_cambia(monkeypatch):
    at, visto = _app(monkeypatch, [("uno", []), ("dos", [])])
    at.chat_input[0].set_value("a").run()
    at.chat_input[0].set_value("b").run()
    assert visto[0][1] == visto[1][1] and len(at.session_state.agente_mensajes) == 4
    hilo = at.session_state.agente_hilo
    next(b for b in at.button if b.label == "Nueva conversación").click().run()
    assert at.session_state.agente_hilo != hilo and at.session_state.agente_mensajes == []


def test_un_error_del_agente_se_muestra_sin_romper_la_app(monkeypatch):
    def falla(*args, **kwargs):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")
    monkeypatch.setattr("taaml.agente.conversar", falla)
    at = AppTest.from_file(str(RAIZ / "app" / "asistente.py"), default_timeout=30)
    at.run()
    at.chat_input[0].set_value("hola").run()
    assert not at.exception and any("cuota" in e.value for e in at.error)
