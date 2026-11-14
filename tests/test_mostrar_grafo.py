import importlib.util
from pathlib import Path

from langchain_core.messages import AIMessage

RUTA = Path(__file__).resolve().parent.parent / "scripts" / "31_mostrar_grafo.py"


def test_el_agente_es_un_stategraph_con_el_ciclo_modelo_herramientas():
    spec = importlib.util.spec_from_file_location("grafo", RUTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    from taaml.agente import crear_agente

    agente = crear_agente(llm=modulo.ModeloSimulado(messages=iter([AIMessage(content="ok")])))
    assert type(agente).__name__ == "CompiledStateGraph"
    nodos = set(agente.get_graph().nodes)
    assert {"model", "tools", "__start__", "__end__"} <= nodos
    aristas = modulo.aristas_del_grafo(agente)
    assert any(
        o == "tools" and c for o, _, c in aristas
    )  # tras las herramientas se decide si el modelo vuelve a correr
    assert any(d == "tools" and c for _, d, c in aristas)  # y tras el modelo, si se llaman herramientas
