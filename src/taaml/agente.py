"""Agente con herramienta: `create_agent` de LangChain 1.x con una herramienta que consulta la base de Celsia.

Es el patrón «modelo + herramientas + prompt». Reutiliza la misma recuperación del Q&A (`recuperacion.buscar`), así que
la base de conocimiento sigue en un solo lugar. Por defecto usa un modelo local de Ollama (sin costo); temperature 0.0 y top_p 0.1.
"""
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_ollama import ChatOllama

from taaml.prompts import PARAMETROS_MODELO, leer_prompt
from taaml.recuperacion import buscar, formatear_contexto

MODELO_AGENTE = "llama3.2"  # 3B, soporta llamadas a herramientas; gratis y local
FRAGMENTOS_AGENTE = 4  # el modelo es pequeño y corre en CPU: con 12 fragmentos tarda demasiado y desborda su ventana
VENTANA_CONTEXTO = 8192  # Ollama usa 4096 por defecto y recortaría el prompt


@tool
def buscar_en_base(pregunta: str) -> str:
    """Busca en la información oficial de Celsia los fragmentos que responden la pregunta del cliente."""
    return formatear_contexto(buscar(pregunta, k=FRAGMENTOS_AGENTE))


def crear_agente(modelo: str = MODELO_AGENTE):
    llm = ChatOllama(model=modelo, temperature=PARAMETROS_MODELO["temperature"], top_p=PARAMETROS_MODELO["top_p"], num_ctx=VENTANA_CONTEXTO)
    return create_agent(model=llm, tools=[buscar_en_base], system_prompt=leer_prompt("v1_agente.md"))


def preguntar(pregunta: str, modelo: str = MODELO_AGENTE) -> tuple[str, list[str]]:
    """Devuelve la respuesta del agente y las consultas que hizo a la herramienta."""
    resultado = crear_agente(modelo).invoke({"messages": [{"role": "user", "content": pregunta}]},
                                            config={"run_name": "agente_celsia", "tags": ["agente"]})
    consultas = [llamada["args"].get("pregunta", "") for m in resultado["messages"] for llamada in getattr(m, "tool_calls", [])]
    return resultado["messages"][-1].text.strip(), consultas
