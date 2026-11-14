"""MUESTRA EL GRAFO DEL AGENTE (LangGraph): `create_agent` devuelve un StateGraph compilado con nodos, aristas y estado. No llama a ningún modelo: usa uno simulado.

Los nodos son el modelo, las herramientas y dos nodos de middleware (el resumen antes del modelo y el tope de llamadas después). Las aristas condicionales son las decisiones del ciclo:
tras el modelo, el tope de llamadas decide si sigue a las herramientas o termina.
Uso:  uv run python scripts/31_mostrar_grafo.py
"""

import os
import sys
from pathlib import Path

os.environ["LANGSMITH_TRACING"] = os.environ["LANGCHAIN_TRACING_V2"] = "false"  # no envía nada a LangSmith

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402

from taaml.agente import crear_agente  # noqa: E402


class ModeloSimulado(GenericFakeChatModel):
    """Acepta herramientas sin usarlas."""

    def bind_tools(self, *args, **kwargs):
        return self


def aristas_del_grafo(agente) -> list[tuple[str, str, bool]]:
    """(origen, destino, condicional) de cada arista del grafo compilado."""
    return sorted((e.source, e.target, bool(e.conditional)) for e in agente.get_graph().edges)


def main() -> None:
    agente = crear_agente(llm=ModeloSimulado(messages=iter([AIMessage(content="ok")])))
    grafo = agente.get_graph()
    print(
        f"{type(agente).__name__}: {len(grafo.nodes)} nodos y {len(grafo.edges)} aristas\n\nNodos: "
        + ", ".join(grafo.nodes)
    )
    print("\nAristas:")
    for origen, destino, condicional in aristas_del_grafo(agente):
        print(f"  {origen} -> {destino}" + ("   (condicional)" if condicional else ""))
    print(
        "\nEstado: los mensajes (reductor add_messages), guardados por el checkpointer bajo el thread_id; la memoria de largo plazo va aparte, en el Store."
    )


if __name__ == "__main__":
    main()
