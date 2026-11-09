"""Agente con herramienta: `create_agent` de LangChain 1.x con una herramienta que consulta la base de Celsia.

Es el patrón «modelo + herramientas + prompt», con memoria por conversación (`thread_id`) y dos herramientas: `buscar_en_base`
(texto, reutiliza `recuperacion.buscar`) y `consultar_datos` (datos exactos). Usa Gemini de pago (indicación del profesor) y, si
falla, cae a un modelo local de Ollama. Se envían temperature 0.0 y top_p 0.1, pero gemini-3.8-flash los ignora (medido): la respuesta puede variar.
"""
from datetime import date
from typing import Literal
from uuid import uuid4

from langchain.agents import create_agent
from langchain.agents.middleware import ModelFallbackMiddleware
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from taaml.consulta_datos import consultar
from taaml.prompts import leer_prompt
from taaml.recuperacion import buscar, formatear_contexto
from taaml.sanitizar import quitar_invisibles
from taaml.tareas import obtener_modelo

MODELO_AGENTE = "gemini-3.8-flash"  # API de pago, el más reciente de la familia Flash (indicación del profesor)
MODELO_RESPALDO = "ollama:llama3.2"  # 3B local y gratis: solo entra si Gemini falla (cuota, red)
FRAGMENTOS_AGENTE = 4  # cada turno reenvía el historial: pocos fragmentos mantienen bajo el costo en tokens


# USD por millón de tokens (entrada, salida con "pensamiento" incluido), página oficial de precios de Gemini; la tarifa de 2026 es introductoria
PRECIOS_USD = {"gemini-3.8-flash": (0.75, 3.75)}
PRECIOS_USD_2027 = {"gemini-3.8-flash": (1.50, 7.50)}  # desde el 1 de enero de 2027
INICIO_2027 = date(2027, 1, 1)


@tool
def buscar_en_base(pregunta: str) -> str:
    """Busca en la información oficial de Celsia los fragmentos que responden la pregunta del cliente."""
    return formatear_contexto(buscar(pregunta, k=FRAGMENTOS_AGENTE))


@tool
def consultar_datos(tabla: Literal["sedes", "contactos", "catalogo"], ciudad: str = "", departamento: str = "", tipo: str = "",
                    tema: str = "", texto: str = "") -> str:
    """Consulta datos exactos de Celsia en tablas, sin buscar por significado. Úsala para direcciones, horarios y teléfonos de sedes,
    tiendas y puntos de pago (tabla «sedes»: ciudad, departamento, tipo), para teléfonos, WhatsApp, correos y enlaces de atención
    (tabla «contactos»: tipo, tema) y para ubicar páginas del sitio (tabla «catalogo»: texto del título)."""
    filtros = {"ciudad": ciudad, "departamento": departamento, "tipo": tipo, "tema": tema, "texto": texto}
    return consultar(tabla, filtros)


HERRAMIENTAS = [buscar_en_base, consultar_datos]


_AGENTES: dict = {}  # un agente (con su memoria) por modelo: el cuaderno vive dentro del agente, así que hay que reutilizarlo


def crear_agente(modelo: str = MODELO_AGENTE, llm=None):
    """Agente con memoria: el checkpointer guarda cada conversación bajo su `thread_id`. `llm` permite inyectar un modelo (pruebas)."""
    con_respaldo = llm is None and modelo != MODELO_RESPALDO  # un modelo inyectado o el propio respaldo no necesitan otro
    llm = llm or obtener_modelo(modelo)
    respaldo = [ModelFallbackMiddleware(obtener_modelo(MODELO_RESPALDO))] if con_respaldo else []
    return create_agent(model=llm, tools=HERRAMIENTAS, system_prompt=leer_prompt("v2_agente.md"), checkpointer=InMemorySaver(),
                        middleware=respaldo)


def _agente(modelo: str):
    if modelo not in _AGENTES:
        _AGENTES[modelo] = crear_agente(modelo)
    return _AGENTES[modelo]


def conversar(pregunta: str, thread_id: str, modelo: str = MODELO_AGENTE, agente=None) -> tuple[str, list[dict]]:
    """Un turno de una conversación: devuelve la respuesta y las herramientas que usó en este turno (nombre y argumentos).

    Mismo `thread_id` = misma conversación (el agente ve los turnos anteriores); otro `thread_id` empieza en blanco.
    """
    agente = agente or _agente(modelo)
    resultado = agente.invoke({"messages": [{"role": "user", "content": quitar_invisibles(pregunta)}]},
                              config={"configurable": {"thread_id": thread_id}, "run_name": "agente_celsia", "tags": ["agente"]})
    mensajes = resultado["messages"]
    ultimo = max(i for i, m in enumerate(mensajes) if m.type == "human")  # la memoria trae turnos viejos: solo cuenta lo de este turno
    llamadas = [{"herramienta": ll["name"], "args": ll["args"]} for m in mensajes[ultimo:] for ll in getattr(m, "tool_calls", [])]
    return mensajes[-1].text.strip(), llamadas


def uso_del_turno(agente, thread_id: str) -> tuple[int, int]:
    """Tokens (entrada, salida) que gastó el último turno de una conversación, sumando todas las llamadas al modelo.

    La salida se calcula como total - entrada, porque así incluye el «pensamiento» del modelo, que también se cobra.
    """
    mensajes = agente.get_state({"configurable": {"thread_id": thread_id}}).values["messages"]
    ultimo = max(i for i, m in enumerate(mensajes) if m.type == "human")
    usos = [m.usage_metadata for m in mensajes[ultimo:] if m.type == "ai" and m.usage_metadata]
    entrada = sum(u.get("input_tokens", 0) for u in usos)
    return entrada, sum(u.get("total_tokens", 0) for u in usos) - entrada


def costo_usd(entrada: int, salida: int, modelo: str = MODELO_AGENTE, hoy: date | None = None) -> float | None:
    """Costo en dólares de una cantidad de tokens; 0.0 para un modelo local y None si no hay precio conocido."""
    if modelo.startswith("ollama:"):
        return 0.0
    precios = PRECIOS_USD_2027 if (hoy or date.today()) >= INICIO_2027 else PRECIOS_USD
    if modelo not in precios:
        return None
    por_entrada, por_salida = precios[modelo]
    return (entrada * por_entrada + salida * por_salida) / 1_000_000


def etiqueta_herramientas(llamadas: list[dict]) -> str:
    """Texto corto para la app: qué herramienta usó el agente en un turno (muestra el router)."""
    if not llamadas:
        return "Respondió sin consultar herramientas"
    partes = []
    for ll in llamadas:
        if ll["herramienta"] == "buscar_en_base":
            partes.append("buscó en el texto del sitio")
        else:
            filtros = ", ".join(f"{k}: {v}" for k, v in ll["args"].items() if k != "tabla" and v)
            partes.append(f"consultó la tabla {ll['args'].get('tabla', '?')}" + (f" ({filtros})" if filtros else ""))
    return "Usó: " + "; ".join(partes)


def preguntar(pregunta: str, modelo: str = MODELO_AGENTE) -> tuple[str, list[str]]:
    """Pregunta suelta (sin conversación previa): devuelve la respuesta y las consultas que hizo a `buscar_en_base`."""
    respuesta, llamadas = conversar(pregunta, thread_id=uuid4().hex, modelo=modelo)
    return respuesta, [ll["args"].get("pregunta", "") for ll in llamadas if ll["herramienta"] == "buscar_en_base"]
