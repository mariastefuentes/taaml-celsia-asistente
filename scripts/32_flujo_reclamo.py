"""FLUJO CON APROBACIÓN HUMANA (StateGraph a mano): radicar un reclamo solo si una persona lo aprueba. Sin modelos ni costo: el extractor es determinista.

Muestra los nodos y las aristas del grafo, y tres corridas: aprobada, rechazada e incompleta (sin ciudad). La pausa es un `interrupt` y se retoma con `Command(resume=...)`.
Con `--real` el extractor es el modelo (`with_structured_output` con el esquema Pydantic `Reclamo`) y SÍ GASTA CUOTA de Gemini.
Uso:  uv run python scripts/32_flujo_reclamo.py
      uv run python scripts/32_flujo_reclamo.py --real "Se fue la luz en Ibagué desde las 8 y nadie responde"
"""

import os
import sys
from pathlib import Path

os.environ["LANGSMITH_TRACING"] = os.environ["LANGCHAIN_TRACING_V2"] = "false"  # la demo gratuita no envía trazas

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from langgraph.types import Command  # noqa: E402

from taaml.flujo_reclamo import Reclamo, construir_flujo, extractor_con_modelo  # noqa: E402


def falso(mensaje: str) -> Reclamo:
    """Extractor de mentira: la ciudad es lo que viene después de « en »."""
    ciudad = mensaje.split(" en ")[-1].strip(" .") if " en " in mensaje else ""
    return Reclamo(tipo="falla_de_servicio", ciudad=ciudad, descripcion=mensaje)


def correr(flujo, mensaje: str, decision: bool | None, hilo: str) -> None:
    config = {"configurable": {"thread_id": hilo}}
    print(f"\n» «{mensaje}»")
    salida = flujo.invoke({"mensaje": mensaje}, config)
    if "__interrupt__" in salida:
        pausa = salida["__interrupt__"][0].value
        print(f"  pausa: {pausa['pregunta']} {pausa['reclamo']}")
        print(f"  una persona responde: {'sí' if decision else 'no'}")
        salida = flujo.invoke(Command(resume=decision), config)
    print(f"  resultado: {salida['resultado']}")


def main() -> None:
    real = "--real" in sys.argv
    flujo = construir_flujo(extractor_con_modelo() if real else falso)
    grafo = flujo.get_graph()
    print("Nodos: " + ", ".join(grafo.nodes))
    print("Aristas: " + "; ".join(f"{e.source}->{e.target}{' (condicional)' if e.conditional else ''}" for e in grafo.edges))
    if real:
        correr(flujo, sys.argv[sys.argv.index("--real") + 1], True, "real")
        return
    correr(flujo, "Se fue la luz en Ibagué", True, "a")
    correr(flujo, "Me cobraron de más en Cali", False, "b")
    correr(flujo, "No tengo servicio desde ayer", True, "c")


if __name__ == "__main__":
    main()
