"""Valoraciones de las respuestas del asistente: el guardado en el Store de largo plazo (SQLite y PostgreSQL)."""

import sqlite3

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.sqlite import SqliteStore

from taaml.agente import conversar_en_vivo, crear_agente, mensaje_del_hilo
from taaml.retroalimentacion import NAMESPACE, registrar


class ModeloEspia(GenericFakeChatModel):
    """Modelo simulado: contesta sin llamar a Gemini ni a Ollama."""

    def bind_tools(self, *args, **kwargs):
        return self


def _agente(hilo, mensaje_id="m1", texto="Son 12 horas."):
    """Agente con un turno cuyo mensaje final tiene un id conocido."""
    return crear_agente(
        llm=ModeloEspia(messages=iter([AIMessage(content=texto, id=mensaje_id)] * 5)),
        checkpointer=InMemorySaver(),
        store=InMemoryStore(),
    )


def test_el_turno_entrega_el_id_del_mensaje_en_el_evento_fin():
    agente = _agente("hilo-fin")
    eventos = list(conversar_en_vivo("¿Cuánta luz hay?", "hilo-fin", agente=agente))
    fin = next(e for e in eventos if e["tipo"] == "fin")
    assert fin["mensaje_id"] == "m1"


def test_el_mensaje_del_hilo_confirma_que_el_id_existe():
    agente = _agente("hilo-valida")
    agente.invoke({"messages": [{"role": "user", "content": "¿Cuánta luz hay?"}]}, {"configurable": {"thread_id": "hilo-valida"}})
    assert mensaje_del_hilo("hilo-valida", "m1", agente=agente) is True
    assert mensaje_del_hilo("hilo-valida", "m2", agente=agente) is False
    assert mensaje_del_hilo("hilo-otro", "m1", agente=agente) is False


def _store_sqlite(ruta):
    store = SqliteStore(sqlite3.connect(ruta, check_same_thread=False, isolation_level=None))
    store.setup()
    return store


def test_registrar_guarda_la_valoración_y_los_duplicados_no_se_escriben(tmp_path):
    store = _store_sqlite(tmp_path / "retro.sqlite")
    assert registrar("h1", "m1", 1, "u1", almacen=store) is True
    assert registrar("h1", "m1", 1, "u1", almacen=store) is False  # ya estaba valorada
    assert registrar("h1", "m2", -1, "u1", almacen=store) is True  # otro mensaje
    assert registrar("h2", "m1", 1, "u1", almacen=store) is True  # otro hilo


def test_el_guardado_queda_después_de_una_conexión_nueva(tmp_path):
    ruta = tmp_path / "retro.sqlite"
    registrar("h1", "m1", 1, "u1", almacen=_store_sqlite(ruta))
    item = _store_sqlite(ruta).get(NAMESPACE, "h1:m1")
    assert item.value["valor"] == 1 and item.value["usuario"] == "u1"
