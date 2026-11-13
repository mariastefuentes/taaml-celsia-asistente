import importlib.util
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage

RUTA = Path(__file__).resolve().parent.parent / "scripts" / "27_viaje_en_el_tiempo.py"


@pytest.fixture
def demo():
    spec = importlib.util.spec_from_file_location("viaje", RUTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _agente(demo, tmp_path, respuestas):
    from taaml.agente import almacen_de_memoria, crear_agente
    return crear_agente(llm=demo.ModeloSimulado(messages=iter(AIMessage(content=r) for r in respuestas)), checkpointer=almacen_de_memoria(tmp_path / "m.db"))


def test_el_historial_guarda_un_punto_de_control_por_paso(demo, tmp_path):
    agente = _agente(demo, tmp_path, ["Hola, Ana."])
    demo.conversar("Me llamo Ana", "h", agente=agente)
    historial = list(agente.get_state_history({"configurable": {"thread_id": "h"}}))
    assert len(historial) >= 4 and historial[-1].values.get("messages", []) == []


def test_replay_vuelve_a_ejecutar_desde_un_punto_anterior(demo, tmp_path):
    agente = _agente(demo, tmp_path, ["Primera.", "Segunda."])
    demo.conversar("Hola", "h", agente=agente)
    antes = demo.punto_de_control(agente, "h", "Hola")
    agente.invoke(None, antes.config)
    assert demo.textos(agente, {"configurable": {"thread_id": "h"}})[-1] == "ai: Segunda."


def test_fork_crea_una_rama_sin_tocar_el_punto_original(demo, tmp_path):
    agente = _agente(demo, tmp_path, ["Primera.", "Rama."])
    demo.conversar("Hola", "h", agente=agente)
    antes = demo.punto_de_control(agente, "h", "Hola")
    pregunta = antes.values["messages"][-1]
    rama = agente.update_state(antes.config, {"messages": [HumanMessage(content="Otra", id=pregunta.id)]})
    resultado = agente.invoke(None, rama)
    assert [f"{m.type}: {m.text}" for m in resultado["messages"]] == ["human: Otra", "ai: Rama."]
    assert demo.textos(agente, antes.config)[-1] == "human: Hola"
