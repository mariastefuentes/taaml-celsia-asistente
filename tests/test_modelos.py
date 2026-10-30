import json

import pytest
from langchain_openai import ChatOpenAI

from taaml.reordenar import MODELO_REORDENADOR, modelo_reordenador
from taaml.tareas import _tag_instalado, obtener_modelo


class _RespuestaTags:
    def __init__(self, nombres):
        self._cuerpo = json.dumps({"models": [{"name": n} for n in nombres]}).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self._cuerpo


def test_un_modelo_local_sin_tag_usa_el_tag_que_ollama_tiene_instalado(monkeypatch):
    from taaml import tareas

    monkeypatch.setattr(tareas.urllib.request, "urlopen", lambda *a, **k: _RespuestaTags(["llama3.2:3b", "nomic-embed-text-v2-moe:latest"]))
    assert _tag_instalado("llama3.2") == "llama3.2:3b"
    assert _tag_instalado("llama3.2:3b") == "llama3.2:3b"
    assert _tag_instalado("nomic-embed-text-v2-moe") == "nomic-embed-text-v2-moe:latest"
    assert _tag_instalado("modelo-inexistente") == "modelo-inexistente"


def test_si_ollama_no_responde_se_deja_el_nombre_tal_cual(monkeypatch):
    from taaml import tareas

    def sin_ollama(*_a, **_k):
        raise ConnectionError("Ollama apagado")

    monkeypatch.setattr(tareas.urllib.request, "urlopen", sin_ollama)
    assert _tag_instalado("llama3.2") == "llama3.2"


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
