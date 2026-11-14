"""VIAJE EN EL TIEMPO DEL ESTADO (clase de memoria): historial de puntos de control, replay y fork. No llama a ningún modelo: usa uno simulado.

Cada paso del agente (la pregunta, la respuesta del modelo, cada herramienta) deja un punto de control (checkpoint) en la memoria de la conversación.
  - Historial: `agente.get_state_history(config)` lista los puntos de control de un `thread_id`, del más reciente al más antiguo.
  - Replay: invocar con `None` y el `checkpoint_id` de un punto anterior vuelve a ejecutar desde ahí.
  - Fork: `agente.update_state(config_del_punto, cambios)` guarda una variante a partir de un punto anterior (aquí, otra pregunta) y la conversación original no se toca.
Uso:  uv run python scripts/27_viaje_en_el_tiempo.py
"""

import os
import sys
from pathlib import Path

os.environ["LANGSMITH_TRACING"] = os.environ["LANGCHAIN_TRACING_V2"] = (
    "false"  # el modelo simulado no se lleva bien con las trazas, y esta demo no gasta ni envía nada
)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402

from taaml.agente import conversar, crear_agente  # noqa: E402


class ModeloSimulado(GenericFakeChatModel):
    """Responde con lo que se le da, en orden; acepta herramientas sin usarlas."""

    def bind_tools(self, *args, **kwargs):
        return self


def punto_de_control(agente, hilo: str, pregunta: str):
    """El punto de control justo después de recibir `pregunta` y antes de que el modelo responda (su siguiente paso es el modelo)."""
    for estado in agente.get_state_history({"configurable": {"thread_id": hilo}}):
        mensajes = estado.values.get("messages", [])
        if mensajes and mensajes[-1].type == "human" and mensajes[-1].text == pregunta and estado.next:
            return estado
    raise LookupError(f"No hay un punto de control para «{pregunta}»")


def textos(agente, config) -> list[str]:
    return [f"{m.type}: {m.text}" for m in agente.get_state(config).values["messages"]]


def main() -> None:
    respuestas = [
        "Mucho gusto, Ana.",
        "Trabajas en Carvajal.",
        "Respuesta repetida desde el punto de control.",
        "Vives en Cali.",
    ]
    agente = crear_agente(llm=ModeloSimulado(messages=iter(AIMessage(content=r) for r in respuestas)))
    hilo = "demo-viaje"
    config = {"configurable": {"thread_id": hilo}}
    conversar("Me llamo Ana y trabajo en Carvajal", hilo, agente=agente)
    conversar("¿Dónde trabajo?", hilo, agente=agente)

    historial = list(agente.get_state_history(config))
    print(f"1. Historial: {len(historial)} puntos de control en la conversación (del más reciente al más antiguo)")
    for e in historial:
        print(
            f"   paso {e.metadata['step']:>2} | mensajes: {len(e.values.get('messages', []))} | siguiente: {e.next or 'fin'} | {e.config['configurable']['checkpoint_id'][:8]}"
        )

    antes = punto_de_control(agente, hilo, "¿Dónde trabajo?")
    print(
        f"\n2. Replay: se vuelve al punto {antes.config['configurable']['checkpoint_id'][:8]} (justo antes de responder «¿Dónde trabajo?») y se ejecuta de nuevo"
    )
    agente.invoke(None, antes.config)
    print("   la conversación ahora termina en: " + textos(agente, config)[-1])

    print("\n3. Fork: desde ese mismo punto se cambia la pregunta por «¿Dónde vivo?» y se continúa")
    pregunta_original = antes.values["messages"][-1]
    rama = agente.update_state(
        antes.config, {"messages": [HumanMessage(content="¿Dónde vivo?", id=pregunta_original.id)]}
    )
    resultado = agente.invoke(None, rama)
    print("   rama nueva:     " + " | ".join(f"{m.type}: {m.text}" for m in resultado["messages"][-2:]))
    print(
        "   punto original: "
        + " | ".join(textos(agente, antes.config)[-1:])
        + "  (no se modificó: sigue siendo un punto de control propio)"
    )


if __name__ == "__main__":
    main()
