import pytest
from langchain_openai import ChatOpenAI

from taaml.reordenar import MODELO_REORDENADOR, modelo_reordenador
from taaml.tareas import obtener_modelo


def test_un_nombre_deepseek_usa_deepseek_con_razonamiento_apagado(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "clave-de-prueba")
    modelo = obtener_modelo("deepseek-flash")
    assert isinstance(modelo, ChatOpenAI)
    assert modelo.openai_api_base == "https://api.deepseek.com" and modelo.temperature == 0.0 and modelo.top_p == 0.1
    assert modelo.extra_body == {"thinking": {"type": "disabled"}}


def test_sin_clave_de_deepseek_falla_con_mensaje_claro(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        obtener_modelo("deepseek-v4-pro")


def test_el_reordenador_es_de_la_misma_familia():
    assert modelo_reordenador("deepseek-flash") == "deepseek-flash"
    assert modelo_reordenador("gemini-3.5-flash") == MODELO_REORDENADOR
