"""Agente con herramienta: `create_agent` de LangChain 1.x con una herramienta que consulta la base de Celsia.

Es el patrón «modelo + herramientas + prompt», con memoria por conversación (`thread_id`) y dos herramientas: `buscar_en_base`
(texto, reutiliza `recuperacion.buscar`) y `consultar_datos` (datos exactos). Usa Gemini de pago (indicación del profesor) y, si
falla, cae a un modelo local de Ollama. Se envían temperature 0.0 y top_p 0.1, pero gemini-3.8-flash los ignora (medido): la respuesta puede variar.
"""
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal
from uuid import uuid4

from langchain.agents import create_agent
from langchain.agents.middleware import ModelFallbackMiddleware, wrap_model_call
from langchain.tools import ToolRuntime
from langchain_core.messages.utils import count_tokens_approximately, trim_messages
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from langgraph.store.sqlite import SqliteStore

from taaml.consulta_datos import consultar
from taaml.prompts import leer_prompt
from taaml.recuperacion import buscar, formatear_contexto
from taaml.sanitizar import quitar_invisibles
from taaml.tareas import obtener_modelo

MODELO_AGENTE = "gemini-3.8-flash"  # API de pago, el más reciente de la familia Flash (indicación del profesor)
MODELO_RESPALDO = "ollama:llama3.2"  # 3B local y gratis: solo entra si Gemini falla (cuota, red)
RUTA_MEMORIA = Path(__file__).resolve().parents[2] / "data" / "memoria" / "conversaciones.sqlite"  # las conversaciones sobreviven a reiniciar la app
RUTA_MEMORIA_LARGA = RUTA_MEMORIA.with_name("largo_plazo.sqlite")  # lo que el cliente cuenta de sí mismo, para otras conversaciones
MAX_DATOS_CLIENTE = 20  # tope de datos guardados por cliente
MAX_TOKENS_HISTORIAL = 3000  # lo que el modelo ve de la conversación; el historial completo sigue guardado
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


@dataclass
class Contexto:
    """Quién conversa: el Store separa lo guardado de cada cliente con este identificador (no lo ve el modelo)."""
    usuario: str = "anonimo"


def _espacio(runtime: ToolRuntime[Contexto]) -> tuple[str, str]:
    return ("perfil", runtime.context.usuario)  # namespace: un cliente nunca lee los datos de otro


def _almacen(runtime: ToolRuntime[Contexto]) -> BaseStore:
    if runtime.store is None:
        raise RuntimeError("El agente se creó sin Store: no hay memoria de largo plazo")
    return runtime.store


@tool
def guardar_dato_del_cliente(dato: str, runtime: ToolRuntime[Contexto]) -> str:
    """Guarda un dato que el cliente contó de sí mismo (nombre, ciudad, empresa, preferencia) para recordarlo en conversaciones futuras.
    Úsala solo cuando el cliente comparta ese dato o pida que lo recuerdes; nunca guardes cédulas, claves, tarjetas ni cuentas."""
    dato = quitar_invisibles(dato).strip()[:300]
    existentes = _almacen(runtime).search(_espacio(runtime), limit=MAX_DATOS_CLIENTE + 1)
    if any(e.value["dato"] == dato for e in existentes):
        return "Ya lo tenía guardado."
    if len(existentes) >= MAX_DATOS_CLIENTE:
        return "No pude guardarlo: hay demasiados datos guardados de este cliente."
    _almacen(runtime).put(_espacio(runtime), uuid4().hex, {"dato": dato})
    return "Guardado."


@tool
def recordar_datos_del_cliente(runtime: ToolRuntime[Contexto]) -> str:
    """Devuelve lo que el cliente contó de sí mismo en conversaciones anteriores. Úsala cuando pregunte por algo que dijo antes
    (su nombre, dónde trabaja, qué prefiere) y no esté en la conversación actual."""
    items = _almacen(runtime).search(_espacio(runtime), limit=MAX_DATOS_CLIENTE)
    return "\n".join(f"- {quitar_invisibles(i.value['dato'])}" for i in items) or "No hay datos guardados de este cliente."


HERRAMIENTAS = [buscar_en_base, consultar_datos, guardar_dato_del_cliente, recordar_datos_del_cliente]


@wrap_model_call
def limitar_historial(request, handler):
    """Al modelo solo le llegan los últimos mensajes que caben en `MAX_TOKENS_HISTORIAL` (siempre empezando en un turno del cliente).

    Recorta lo que ve el modelo, no lo guardado: el checkpointer conserva todo y la pantalla puede mostrarlo entero.
    """
    recorte = trim_messages(request.messages, max_tokens=MAX_TOKENS_HISTORIAL, strategy="last", token_counter=count_tokens_approximately, start_on="human")
    return handler(request.override(messages=recorte or request.messages))  # un solo turno gigante no se recorta a nada


def almacen_de_memoria(ruta: Path | None = None) -> SqliteSaver:
    """Checkpointer en SQLite: guarda cada conversación en disco bajo su `thread_id`."""
    ruta = ruta or RUTA_MEMORIA
    ruta.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver(sqlite3.connect(ruta, check_same_thread=False))  # Streamlit atiende cada usuario en un hilo distinto


def almacen_de_largo_plazo(ruta: Path | None = None) -> SqliteStore:
    """Store en SQLite: lo que cada cliente contó de sí mismo, guardado por namespace y compartido entre conversaciones."""
    ruta = ruta or RUTA_MEMORIA_LARGA
    ruta.parent.mkdir(parents=True, exist_ok=True)
    almacen = SqliteStore(sqlite3.connect(ruta, check_same_thread=False, isolation_level=None))
    almacen.setup()
    return almacen


_ALMACEN_LARGO: list[SqliteStore] = []  # uno solo por proceso: la API y el agente deben ver los mismos datos


def almacen_compartido() -> SqliteStore:
    if not _ALMACEN_LARGO:
        _ALMACEN_LARGO.append(almacen_de_largo_plazo())
    return _ALMACEN_LARGO[0]


def datos_del_cliente(usuario: str, almacen=None) -> list[str]:
    """Lo que hay guardado de un cliente (para mostrárselo)."""
    return [i.value["dato"] for i in (almacen or almacen_compartido()).search(("perfil", usuario), limit=MAX_DATOS_CLIENTE)]


def olvidar_cliente(usuario: str, almacen=None) -> int:
    """Borra todo lo guardado de un cliente (su derecho a la supresión de datos) y devuelve cuántos datos eran."""
    almacen = almacen or almacen_compartido()
    items = almacen.search(("perfil", usuario), limit=MAX_DATOS_CLIENTE)
    for i in items:
        almacen.delete(("perfil", usuario), i.key)
    return len(items)


_AGENTES: dict = {}  # un agente (con su memoria) por modelo: el cuaderno vive dentro del agente, así que hay que reutilizarlo


def crear_agente(modelo: str = MODELO_AGENTE, llm=None, checkpointer=None, store: BaseStore | None = None):
    """Agente con memoria corta (checkpointer, por `thread_id`) y larga (Store, por cliente). `llm` permite inyectar un modelo (pruebas).

    Sin `checkpointer` ni `store`, un modelo real guarda en SQLite y uno inyectado en memoria (así las pruebas no escriben en disco).
    """
    es_real = llm is None
    con_respaldo = es_real and modelo != MODELO_RESPALDO  # un modelo inyectado o el propio respaldo no necesitan otro
    llm = llm or obtener_modelo(modelo)
    checkpointer = checkpointer or (almacen_de_memoria() if es_real else InMemorySaver())
    store = store or (almacen_compartido() if es_real else InMemoryStore())
    respaldo = [ModelFallbackMiddleware(obtener_modelo(MODELO_RESPALDO))] if con_respaldo else []
    return create_agent(model=llm, tools=HERRAMIENTAS, system_prompt=leer_prompt("v3_agente.md"), checkpointer=checkpointer, store=store,  # ty: ignore[no-matching-overload]  # el decorador tipa el contexto del middleware como None
                        context_schema=Contexto, middleware=[limitar_historial, *respaldo])


def _agente(modelo: str):
    if modelo not in _AGENTES:
        _AGENTES[modelo] = crear_agente(modelo)
    return _AGENTES[modelo]


def conversar(pregunta: str, thread_id: str, modelo: str = MODELO_AGENTE, agente=None, usuario: str = "anonimo") -> tuple[str, list[dict]]:
    """Un turno de una conversación: devuelve la respuesta y las herramientas que usó en este turno (nombre y argumentos).

    Mismo `thread_id` = misma conversación (el agente ve los turnos anteriores); otro `thread_id` empieza en blanco.
    """
    agente = agente or _agente(modelo)
    resultado = agente.invoke({"messages": [{"role": "user", "content": quitar_invisibles(pregunta)}]},
                              config={"configurable": {"thread_id": thread_id}, "run_name": "agente_celsia", "tags": ["agente"]},
                              context=Contexto(usuario=usuario))
    mensajes = resultado["messages"]
    ultimo = max(i for i, m in enumerate(mensajes) if m.type == "human")  # la memoria trae turnos viejos: solo cuenta lo de este turno
    llamadas = [{"herramienta": ll["name"], "args": ll["args"]} for m in mensajes[ultimo:] for ll in getattr(m, "tool_calls", [])]
    return mensajes[-1].text.strip(), llamadas


def conversar_en_vivo(pregunta: str, thread_id: str, modelo: str = MODELO_AGENTE, agente=None, usuario: str = "anonimo"):
    """Un turno como flujo de eventos (para el streaming de la API): `herramienta`, `texto` (trozos de la respuesta) y `fin`.

    Mismo `thread_id` = misma conversación. El evento `fin` trae los tokens y el costo del turno. Un error del modelo sube como excepción.
    """
    agente = agente or _agente(modelo)
    entrada = {"messages": [{"role": "user", "content": quitar_invisibles(pregunta)}]}
    config = {"configurable": {"thread_id": thread_id}, "run_name": "agente_celsia", "tags": ["agente"]}
    llamadas: list[dict] = []
    hubo_texto = False
    for modo, datos in agente.stream(entrada, config=config, context=Contexto(usuario=usuario), stream_mode=["updates", "messages"]):
        if modo == "messages":
            trozo, meta = datos
            if trozo.type == "AIMessageChunk" and meta.get("langgraph_node") == "model" and trozo.text:
                hubo_texto = True
                yield {"tipo": "texto", "texto": trozo.text}
        else:
            for actualizacion in datos.values():
                for m in (actualizacion or {}).get("messages", []):
                    for ll in getattr(m, "tool_calls", []):
                        llamadas.append({"herramienta": ll["name"], "args": ll["args"]})
                        yield {"tipo": "herramienta", "herramienta": ll["name"], "args": ll["args"]}
    if not hubo_texto:  # un modelo que no emite trozos (o el respaldo) entrega la respuesta completa de una vez
        yield {"tipo": "texto", "texto": agente.get_state(config).values["messages"][-1].text.strip()}
    entrada_tokens, salida_tokens = uso_del_turno(agente, thread_id)
    yield {"tipo": "fin", "usadas": etiqueta_herramientas(llamadas), "tokens_entrada": entrada_tokens, "tokens_salida": salida_tokens,
           "costo_usd": costo_usd(entrada_tokens, salida_tokens, modelo)}


def historial_visible(thread_id: str, modelo: str = MODELO_AGENTE, agente=None) -> list[dict]:
    """La conversación guardada, lista para pintarla en pantalla: `rol`, `texto` y, en las respuestas, qué herramientas usó."""
    agente = agente or _agente(modelo)
    mensajes = agente.get_state({"configurable": {"thread_id": thread_id}}).values.get("messages", [])
    visibles, llamadas = [], []
    for m in mensajes:
        if m.type == "human":
            visibles.append({"rol": "user", "texto": m.text})
            llamadas = []
        elif m.type == "ai":
            llamadas += [{"herramienta": ll["name"], "args": ll["args"]} for ll in m.tool_calls]
            if m.text.strip() and not m.tool_calls:
                visibles.append({"rol": "assistant", "texto": m.text.strip(), "usadas": etiqueta_herramientas(llamadas)})
    return visibles


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
