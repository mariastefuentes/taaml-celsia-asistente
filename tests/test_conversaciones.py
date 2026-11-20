from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from taaml.agente import MENSAJE_EN_REVISION
from taaml.conversaciones import MAX_CARACTERES, conversacion_de, es_fallida, leer_conversaciones


def test_conversacion_normal_no_es_fallida_y_lista_herramientas():
    mensajes = [
        HumanMessage("¿Qué es Celsia Solar?"),
        AIMessage("", tool_calls=[{"name": "buscar_en_base", "args": {"consulta": "solar"}, "id": "1"}]),
        ToolMessage("fragmento", tool_call_id="1", name="buscar_en_base"),
        AIMessage("Es la línea de energía solar de Celsia."),
    ]
    c = conversacion_de("h1", mensajes)
    assert c["herramientas"] == ["buscar_en_base"]
    assert [t["rol"] for t in c["turnos"]] == ["cliente", "asistente"]
    assert not c["fallida"] and not c["en_revision"]
    assert c["texto"].startswith("Cliente: ¿Qué es Celsia Solar?")


def test_fallida_si_el_asistente_dice_que_no_sabe_o_la_herramienta_da_error():
    assert es_fallida([{"rol": "asistente", "texto": "Lo siento, no tengo esa información."}])
    assert not es_fallida([{"rol": "cliente", "texto": "no tengo esa información"}])  # solo cuenta lo que dice el asistente
    mensajes = [HumanMessage("hola"), ToolMessage("falló", tool_call_id="1", name="x", status="error"), AIMessage("Listo")]
    assert conversacion_de("h", mensajes)["fallida"]


def test_reclamo_en_revision_y_texto_acotado():
    mensajes = [HumanMessage("x" * (MAX_CARACTERES * 2)), AIMessage(MENSAJE_EN_REVISION)]
    c = conversacion_de("h", mensajes)
    assert c["en_revision"]
    assert len(c["texto"]) == MAX_CARACTERES


class FalsoCheckpointer:
    def __init__(self, hilos):
        self.hilos = hilos

    def list(self, _config):
        # un hilo tiene varios puntos de control: no debe duplicarse
        for h in self.hilos:
            for _ in range(2):
                yield SimpleNamespace(config={"configurable": {"thread_id": h}})

    def get_tuple(self, config):
        mensajes = self.hilos[config["configurable"]["thread_id"]]
        return SimpleNamespace(checkpoint={"channel_values": {"messages": mensajes}})


def test_leer_conversaciones_una_por_hilo_ordenadas_y_omite_vacias():
    cp = FalsoCheckpointer({"b": [HumanMessage("hola"), AIMessage("Hola")], "a": [HumanMessage("hey")], "c": []})
    assert [c["hilo"] for c in leer_conversaciones(cp)] == ["a", "b"]


def test_el_cuaderno_de_conversaciones_reales_tiene_codigo_valido_y_avisa_que_no_son_clientes():
    import ast
    import importlib.util
    from pathlib import Path

    ruta = Path(__file__).resolve().parent.parent / "scripts" / "36_construir_notebook_tsne.py"
    spec = importlib.util.spec_from_file_location("construir_notebook_tsne", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    celdas = modulo.celdas_reales()
    for celda in celdas:
        if celda["cell_type"] == "code":
            ast.parse(celda["source"])  # cada celda de código compila
    texto = " ".join(c["source"] for c in celdas if c["cell_type"] == "markdown")
    assert "no clientes de Celsia" in texto and "nadie etiquetó" in texto
