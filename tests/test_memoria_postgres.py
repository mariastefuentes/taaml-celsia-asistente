"""Memoria con PostgreSQL real (PostgresSaver y PostgresStore). Levanta un Postgres local con `pgserver`; si no está disponible, se omiten."""
import pytest
from langchain_core.messages import AIMessage

pgserver = pytest.importorskip("pgserver")
pytest.importorskip("langgraph.checkpoint.postgres")


@pytest.fixture(scope="module")
def url(tmp_path_factory):
    try:
        servidor = pgserver.get_server(tmp_path_factory.mktemp("pg"))
    except Exception as e:  # sin binarios de Postgres en este equipo
        pytest.skip(f"No se pudo levantar PostgreSQL: {e}")
    yield servidor.get_uri()
    servidor.cleanup()


def _agente(url, respuestas):
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

    from taaml.agente import almacen_de_largo_plazo, almacen_de_memoria, crear_agente

    class Modelo(GenericFakeChatModel):
        def bind_tools(self, *a, **k):
            return self

    return crear_agente(llm=Modelo(messages=iter(AIMessage(content=r) for r in respuestas)), checkpointer=almacen_de_memoria(url=url), store=almacen_de_largo_plazo(url=url))


def test_se_usa_postgres_cuando_hay_database_url(url, monkeypatch):
    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.store.postgres import PostgresStore

    from taaml.agente import almacen_de_largo_plazo, almacen_de_memoria
    monkeypatch.setenv("DATABASE_URL", url)
    assert isinstance(almacen_de_memoria(), PostgresSaver) and isinstance(almacen_de_largo_plazo(), PostgresStore)


def test_la_conversacion_sobrevive_a_un_agente_nuevo(url):
    from taaml.agente import conversar
    conversar("Me llamo Ana", "pg-hilo", agente=_agente(url, ["Mucho gusto, Ana."]))
    nuevo = _agente(url, ["Te llamas Ana."])  # otro agente, otra conexión: lo único compartido es la base
    assert [m.text for m in nuevo.get_state({"configurable": {"thread_id": "pg-hilo"}}).values["messages"]] == ["Me llamo Ana", "Mucho gusto, Ana."]


def test_el_viaje_en_el_tiempo_funciona_en_postgres(url):
    from taaml.agente import conversar
    agente = _agente(url, ["Primera.", "Segunda."])
    conversar("Hola", "pg-viaje", agente=agente)
    config = {"configurable": {"thread_id": "pg-viaje"}}
    antes = next(e for e in agente.get_state_history(config) if e.next and e.values["messages"][-1].type == "human")
    agente.invoke(None, antes.config)
    assert agente.get_state(config).values["messages"][-1].text == "Segunda."


def test_el_store_separa_a_los_clientes_por_namespace(url):
    from taaml.agente import almacen_de_largo_plazo, datos_del_cliente, olvidar_cliente
    almacen = almacen_de_largo_plazo(url=url)
    almacen.put(("perfil", "ana-pg"), "1", {"dato": "Vive en Cali"})
    almacen.put(("perfil", "luis-pg"), "1", {"dato": "Vive en Ibagué"})
    assert datos_del_cliente("ana-pg", almacen) == ["Vive en Cali"]
    assert olvidar_cliente("ana-pg", almacen) == 1 and datos_del_cliente("ana-pg", almacen) == [] and datos_del_cliente("luis-pg", almacen) == ["Vive en Ibagué"]
