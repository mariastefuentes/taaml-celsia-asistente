from taaml.agente import buscar_en_base


def test_la_herramienta_devuelve_fragmentos_con_su_fuente(monkeypatch):
    monkeypatch.setattr("taaml.agente.buscar", lambda p, k=0: [{"documento": "Doc", "categoria": "c", "region": "r", "fuente": "https://www.celsia.com/x", "texto": "hola"}])
    salida = buscar_en_base.invoke({"pregunta": "algo"})
    assert "https://www.celsia.com/x" in salida and "hola" in salida


def test_la_herramienta_tiene_descripcion_para_el_modelo():
    assert buscar_en_base.name == "buscar_en_base" and "Celsia" in buscar_en_base.description
