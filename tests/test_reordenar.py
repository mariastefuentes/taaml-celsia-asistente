from taaml.reordenar import parsear_orden, reordenar


def test_parsea_el_orden_del_modelo():
    assert parsear_orden('{"orden": [3, 1, 2]}', 5) == [2, 0, 1]


def test_descarta_repetidos_y_fuera_de_rango():
    assert parsear_orden('{"orden": [2, 2, 9, 0, "a", 1]}', 3) == [1, 0]


def test_respuesta_ilegible_da_lista_vacia():
    assert parsear_orden("no sé", 5) == [] and parsear_orden('{"otra": 1}', 5) == []


def test_si_el_modelo_falla_se_conserva_el_orden_original(monkeypatch):
    def falla(*_a, **_k):
        raise RuntimeError("sin cuota")
    monkeypatch.setattr("taaml.tareas.obtener_modelo", falla)
    candidatos = [{"texto": f"c{i}"} for i in range(6)]
    assert reordenar("pregunta", candidatos, k=3) == candidatos[:3]


def test_si_el_modelo_elige_menos_de_k_se_completa_con_la_busqueda(monkeypatch):
    class Resp:
        text = '{"orden": [4]}'

    class Modelo:
        def invoke(self, _m):
            return Resp()
    monkeypatch.setattr("taaml.tareas.obtener_modelo", lambda _n: Modelo())
    candidatos = [{"texto": f"c{i}"} for i in range(6)]
    assert [c["texto"] for c in reordenar("p", candidatos, k=3)] == ["c3", "c0", "c1"]
