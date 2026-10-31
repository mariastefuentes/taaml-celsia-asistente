from types import SimpleNamespace

import pytest

from taaml import tareas


class _ModeloFalso:
    def invoke(self, mensajes, config=None):
        return SimpleNamespace(text="  respuesta de prueba  ")


def test_el_qa_devuelve_respuesta_fragmentos_y_metricas(monkeypatch):
    fragmentos = [{"chunk_id": "a", "documento": "D", "categoria": "c", "region": "r", "fuente": "f", "texto": "t"}]

    def _recuperar(pregunta, k=12, metodo="auto"):
        return fragmentos, {"encontrados": len(fragmentos), "metodo": metodo, "tiempo_ms": 9.0}

    monkeypatch.setattr(tareas, "recuperar", _recuperar)
    monkeypatch.setattr(tareas, "obtener_modelo", lambda nombre: _ModeloFalso())
    respuesta, fragmentos_devueltos, metricas = tareas.responder_con_fuentes("pregunta", "rag", "gemini-3.5-flash")
    assert respuesta == "respuesta de prueba"
    assert fragmentos_devueltos == fragmentos and metricas["encontrados"] == 1 and metricas["tiempo_ms"] == 9.0


def test_si_la_recuperacion_falla_se_propaga_el_error_para_el_respaldo(monkeypatch):
    def _recuperar(pregunta, k=12, metodo="auto"):
        return [], {"encontrados": 0, "metodo": "error", "tiempo_ms": 1.0, "error": "ConnectionError ollama apagado"}

    monkeypatch.setattr(tareas, "recuperar", _recuperar)
    with pytest.raises(RuntimeError, match="ollama apagado"):
        tareas.responder_con_fuentes("pregunta", "rag", "gemini-3.5-flash")


def test_con_base_que_no_busca_no_toma_metricas_de_recuperacion(monkeypatch):
    monkeypatch.setattr(tareas, "recuperar", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debe recuperarse")))
    monkeypatch.setattr(tareas, "cargar_base", lambda tipo, max_por_doc=600: "base")
    monkeypatch.setattr(tareas, "obtener_modelo", lambda nombre: _ModeloFalso())
    respuesta, fragmentos, metricas = tareas.responder_con_fuentes("pregunta", "compacta", "gemini-3.5-flash")
    assert respuesta == "respuesta de prueba" and fragmentos == [] and "error" not in metricas
