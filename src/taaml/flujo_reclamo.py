"""Flujo con aprobación humana para radicar un reclamo: un StateGraph escrito a mano.

El agente de `agente.py` no lo necesita (es un solo ciclo de decisión), pero este flujo sí: tiene ramas explícitas y una pausa obligatoria.
Nodos: `extraer` (el mensaje del cliente pasa a un `Reclamo` validado con Pydantic) → `pedir_aprobacion` (el grafo se pausa con `interrupt` hasta que una persona decide)
→ `radicar` o `cancelar`. Si falta un dato (la ciudad), termina en `incompleto` sin pedir nada. El estado vive en un checkpointer, así que la pausa sobrevive entre llamadas.
Nada se radica sin el «sí» explícito: el nodo que escribe nunca corre antes de la decisión.
"""

from collections.abc import Callable
from typing import Any, Literal, TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, Field


class Reclamo(BaseModel):
    """Lo que hace falta para radicar un reclamo (esquema de la salida estructurada del modelo)."""

    tipo: Literal["falla_de_servicio", "facturacion", "otro"] = Field(description="Tipo de reclamo.")
    ciudad: str = Field("", max_length=80, description="Ciudad donde ocurre; vacío si el cliente no la dijo.")
    descripcion: str = Field(max_length=500, description="Qué pasó, en una frase.")


class Estado(TypedDict, total=False):
    """Estado del grafo: lo que cada nodo lee y escribe."""

    mensaje: str
    reclamo: dict[str, Any]
    aprobado: bool
    radicado: str
    resultado: str


def extractor_con_modelo(modelo: str = "gemini-3.8-flash") -> Callable[[str], Reclamo]:
    """Extractor real: el modelo devuelve un `Reclamo` con `with_structured_output` (GASTA cuota; las pruebas usan uno falso)."""
    from taaml.tareas import _estructurado

    estructurado = _estructurado(modelo, Reclamo)
    return lambda mensaje: estructurado.invoke(f"Extrae el reclamo de este mensaje de un cliente de Celsia:\n{mensaje}")


def radicar_simulado(reclamo: dict[str, Any]) -> str:
    """Registro de mentira: devuelve un número de radicado. Un sistema real llamaría a la herramienta que escribe."""
    return f"REC-{uuid4().hex[:8].upper()}"


def construir_flujo(
    extractor: Callable[[str], Reclamo], registrar: Callable[[dict], str] = radicar_simulado, checkpointer: Any = None
) -> Any:
    """Compila el StateGraph. `extractor` y `registrar` se inyectan para poder probarlo sin modelo."""

    def extraer(estado: Estado) -> Estado:
        return {"reclamo": extractor(estado["mensaje"]).model_dump()}

    def pedir_aprobacion(estado: Estado) -> Estado:
        decision = interrupt({"pregunta": "¿Radico este reclamo?", "reclamo": estado["reclamo"]})  # pausa hasta que una persona responda
        return {"aprobado": bool(decision)}

    def radicar(estado: Estado) -> Estado:
        numero = registrar(estado["reclamo"])
        return {"radicado": numero, "resultado": f"Reclamo radicado con el número {numero}."}

    def cancelar(estado: Estado) -> Estado:
        return {"resultado": "No se radicó: el cliente no lo aprobó."}

    def incompleto(estado: Estado) -> Estado:
        return {"resultado": "Falta la ciudad para radicar el reclamo: pídesela al cliente."}

    def tras_extraer(estado: Estado) -> str:
        return "pedir_aprobacion" if estado["reclamo"]["ciudad"].strip() else "incompleto"

    def tras_aprobar(estado: Estado) -> str:
        return "radicar" if estado["aprobado"] else "cancelar"

    grafo = StateGraph(Estado)
    for nombre, nodo in (
        ("extraer", extraer),
        ("pedir_aprobacion", pedir_aprobacion),
        ("radicar", radicar),
        ("cancelar", cancelar),
        ("incompleto", incompleto),
    ):
        grafo.add_node(nombre, nodo)
    grafo.add_edge(START, "extraer")
    grafo.add_conditional_edges("extraer", tras_extraer, {"pedir_aprobacion": "pedir_aprobacion", "incompleto": "incompleto"})
    grafo.add_conditional_edges("pedir_aprobacion", tras_aprobar, {"radicar": "radicar", "cancelar": "cancelar"})
    for final in ("radicar", "cancelar", "incompleto"):
        grafo.add_edge(final, END)
    return grafo.compile(checkpointer=checkpointer or InMemorySaver())
