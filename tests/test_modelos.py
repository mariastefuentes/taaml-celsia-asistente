
import pytest
from langchain_openai import ChatOpenAI

from taaml import tareas
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


def test_sin_clave_de_gemini_falla_con_mensaje_claro(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        obtener_modelo("gemini-3.5-flash")


def test_el_error_de_configuracion_no_incluye_el_valor_de_la_clave(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "sk-valor-secreto-de-prueba")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY") as error:
        obtener_modelo("deepseek-v4-pro")
    assert "sk-valor-secreto-de-prueba" not in str(error.value)


def test_el_reordenador_es_de_la_misma_familia():
    assert modelo_reordenador("deepseek-flash") == "deepseek-flash"
    assert modelo_reordenador("gemini-3.5-flash") == MODELO_REORDENADOR


def test_los_tres_modelos_se_crean_con_init_chat_model(monkeypatch):
    """El enunciado del Módulo 3 exige `init_chat_model`: se espía y se comprueba qué proveedor pide cada nombre."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "clave-de-prueba")
    monkeypatch.setenv("GOOGLE_API_KEY", "clave-de-prueba")
    pedidos = []
    real = tareas.init_chat_model

    def espia(modelo, **kwargs):
        pedidos.append((modelo, kwargs["model_provider"]))
        return real(modelo, **kwargs)

    monkeypatch.setattr(tareas, "init_chat_model", espia)
    tareas.obtener_modelo.cache_clear()
    modelos = [tareas.obtener_modelo(n) for n in ("deepseek-flash", "gemini-3.5-flash")]
    tareas.obtener_modelo.cache_clear()
    assert pedidos == [("deepseek-flash", "openai"), ("gemini-3.5-flash", "google_genai")]
    assert [type(m).__name__ for m in modelos] == ["ChatOpenAI", "ChatGoogleGenerativeAI"]
