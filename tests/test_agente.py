from taaml.agente import buscar_en_base


def test_la_herramienta_devuelve_fragmentos_con_su_fuente(monkeypatch):
    monkeypatch.setattr("taaml.agente.buscar", lambda p, k=0: [{"documento": "Doc", "categoria": "c", "region": "r", "fuente": "https://www.celsia.com/x", "texto": "hola"}])
    salida = buscar_en_base.invoke({"pregunta": "algo"})
    assert "https://www.celsia.com/x" in salida and "hola" in salida


def test_la_herramienta_tiene_descripcion_para_el_modelo():
    assert buscar_en_base.name == "buscar_en_base" and "Celsia" in buscar_en_base.description


def test_consultar_datos_devuelve_filas_reales_de_la_tabla():
    from taaml.agente import consultar_datos
    salida = consultar_datos.invoke({"tabla": "sedes", "ciudad": "Ibagué"})
    assert "Ibagu" in salida and "Dirección" in salida


def test_consultar_datos_sin_coincidencias_lo_dice():
    from taaml.agente import consultar_datos
    assert "Sin resultados" in consultar_datos.invoke({"tabla": "sedes", "ciudad": "Ciudad inexistente"})


def test_consultar_datos_rechaza_una_tabla_que_no_existe():
    import pytest
    from taaml.agente import consultar_datos
    with pytest.raises(Exception):
        consultar_datos.invoke({"tabla": "facturas"})


def test_la_descripcion_orienta_al_modelo_sobre_cuando_usarla():
    from taaml.agente import consultar_datos
    d = consultar_datos.description.lower()
    assert "sedes" in d and "contactos" in d and "teléfonos" in d


def test_el_agente_tiene_las_dos_herramientas():
    from taaml.agente import HERRAMIENTAS
    assert [h.name for h in HERRAMIENTAS] == ["buscar_en_base", "consultar_datos"]


# --- memoria conversacional (modelo simulado: no llama a Gemini ni a Ollama) ---
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402

from taaml.agente import conversar, crear_agente  # noqa: E402


class ModeloEspia(GenericFakeChatModel):
    """Responde «ok» y anota cuántos mensajes recibió en cada llamada."""
    vistos: list = []

    def bind_tools(self, *args, **kwargs):
        return self

    def _generate(self, messages, *args, **kwargs):
        self.vistos.append([m.content for m in messages if m.type == "human"])
        return super()._generate(messages, *args, **kwargs)


def _agente_espia():
    modelo = ModeloEspia(messages=iter(AIMessage(content="ok") for _ in range(20)), vistos=[])
    return crear_agente(llm=modelo), modelo


def test_misma_conversacion_el_modelo_ve_el_turno_anterior():
    agente, modelo = _agente_espia()
    conversar("¿Qué sedes hay en Ibagué?", "hilo-1", agente=agente)
    conversar("¿Y su teléfono?", "hilo-1", agente=agente)
    assert modelo.vistos[1] == ["¿Qué sedes hay en Ibagué?", "¿Y su teléfono?"]


def test_otra_conversacion_empieza_en_blanco():
    agente, modelo = _agente_espia()
    conversar("¿Qué sedes hay en Ibagué?", "hilo-1", agente=agente)
    conversar("¿Y su teléfono?", "hilo-2", agente=agente)
    assert modelo.vistos[1] == ["¿Y su teléfono?"]


def test_conversar_devuelve_la_respuesta_y_sin_herramientas_si_no_las_uso():
    agente, _ = _agente_espia()
    assert conversar("hola", "h", agente=agente) == ("ok", [])


def test_el_agente_por_modelo_se_reutiliza(monkeypatch):
    from taaml import agente as mod
    mod._AGENTES.clear()
    monkeypatch.setattr(mod, "crear_agente", lambda modelo: object())
    assert mod._agente("m") is mod._agente("m")
    mod._AGENTES.clear()


def test_conversar_informa_la_herramienta_usada_solo_en_este_turno():
    llamada = AIMessage(content="", tool_calls=[{"name": "consultar_datos", "args": {"tabla": "sedes", "ciudad": "Ibagué"}, "id": "1"}])
    modelo = ModeloEspia(messages=iter([llamada, AIMessage(content="Hay sedes en Ibagué"), AIMessage(content="ok")]), vistos=[])
    agente = crear_agente(llm=modelo)
    respuesta, usadas = conversar("¿Sedes en Ibagué?", "h", agente=agente)
    assert respuesta == "Hay sedes en Ibagué" and usadas == [{"herramienta": "consultar_datos", "args": {"tabla": "sedes", "ciudad": "Ibagué"}}]
    assert conversar("gracias", "h", agente=agente) == ("ok", [])  # el turno anterior no se arrastra


# --- modelo del agente ---
def test_el_agente_usa_gemini_de_pago_y_ollama_de_respaldo():
    from taaml.agente import MODELO_AGENTE, MODELO_RESPALDO
    assert MODELO_AGENTE == "gemini-3.8-flash" and MODELO_RESPALDO.startswith("ollama:")


def test_crear_agente_pide_el_modelo_a_obtener_modelo_y_arma_el_respaldo(monkeypatch):
    from taaml import agente as mod
    pedidos = []
    monkeypatch.setattr(mod, "obtener_modelo", lambda nombre: pedidos.append(nombre) or ModeloEspia(messages=iter([]), vistos=[]))
    mod.crear_agente()
    assert pedidos == [mod.MODELO_AGENTE, mod.MODELO_RESPALDO]


def test_el_modelo_de_respaldo_no_se_respalda_a_si_mismo(monkeypatch):
    from taaml import agente as mod
    pedidos = []
    monkeypatch.setattr(mod, "obtener_modelo", lambda nombre: pedidos.append(nombre) or ModeloEspia(messages=iter([]), vistos=[]))
    mod.crear_agente(mod.MODELO_RESPALDO)
    assert pedidos == [mod.MODELO_RESPALDO]
