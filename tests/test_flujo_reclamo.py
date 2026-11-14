import pytest
from langgraph.types import Command

from taaml.flujo_reclamo import Reclamo, construir_flujo


def _extractor(ciudad="Ibagué"):
    return lambda mensaje: Reclamo(tipo="falla_de_servicio", ciudad=ciudad, descripcion=mensaje)


def _config(hilo):
    return {"configurable": {"thread_id": hilo}}


def test_el_flujo_se_pausa_y_no_radica_hasta_que_una_persona_aprueba():
    radicados = []
    flujo = construir_flujo(_extractor(), registrar=lambda r: radicados.append(r) or "REC-1")
    salida = flujo.invoke({"mensaje": "Se fue la luz"}, _config("h1"))
    assert "__interrupt__" in salida and not radicados  # pausa antes de escribir
    assert salida["__interrupt__"][0].value["reclamo"]["ciudad"] == "Ibagué"
    final = flujo.invoke(Command(resume=True), _config("h1"))
    assert final["radicado"] == "REC-1" and radicados and "REC-1" in final["resultado"]


def test_si_la_persona_rechaza_no_se_radica():
    radicados = []
    flujo = construir_flujo(_extractor(), registrar=lambda r: radicados.append(r) or "REC-2")
    flujo.invoke({"mensaje": "Cobro de más"}, _config("h2"))
    final = flujo.invoke(Command(resume=False), _config("h2"))
    assert not radicados and "radicado" not in final and "no lo aprobó" in final["resultado"]


def test_sin_ciudad_termina_en_incompleto_sin_pedir_aprobacion():
    flujo = construir_flujo(_extractor(ciudad=""), registrar=lambda r: "REC-3")
    salida = flujo.invoke({"mensaje": "No hay servicio"}, _config("h3"))
    assert "__interrupt__" not in salida and "ciudad" in salida["resultado"]


def test_el_grafo_tiene_ramas_explicitas():
    grafo = construir_flujo(_extractor()).get_graph()
    assert {"extraer", "pedir_aprobacion", "radicar", "cancelar", "incompleto"} <= set(grafo.nodes)
    assert sum(1 for e in grafo.edges if e.conditional) == 4


def test_el_esquema_rechaza_un_tipo_desconocido():
    with pytest.raises(ValueError):
        Reclamo(tipo="inventado", ciudad="Cali", descripcion="x")
