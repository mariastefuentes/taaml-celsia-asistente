import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("evaluar_en_langsmith", RAIZ / "scripts" / "24_evaluar_en_langsmith.py")
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)


def test_el_dataset_sale_de_la_matriz_con_todas_sus_preguntas():
    ejemplos = ev.cargar_ejemplos()
    assert len(ejemplos) == 43  # las 33 de antes (R01 a R33) y las 10 de la ampliación (R34 a R43, D36)
    r01 = ejemplos[0]
    assert r01["inputs"]["id"] == "R01" and r01["outputs"]["herramienta_esperada"] == "consultar_sedes"
    assert next(e for e in ejemplos if e["inputs"]["id"] == "R19")["inputs"][
        "previo"
    ]  # las de memoria llevan su turno de preparación


def _salida(*herramientas, respuesta="ok"):
    return {
        "respuesta": respuesta,
        "llamadas": [{"herramienta": h, "args": {"tabla": "sedes", "ciudad": "Ibagué"}} for h in herramientas],
    }


def test_ruta_ok_puntua_1_si_usa_la_herramienta_esperada_y_0_si_no():
    entrada, ref = {"id": "R01"}, {"herramienta_esperada": "consultar_datos", "parametros_esperados": ""}
    assert ev.ruta_ok(entrada, _salida("consultar_datos"), ref) == {"key": "ruta_ok", "score": 1}
    assert ev.ruta_ok(entrada, _salida("buscar_en_base"), ref)["score"] == 0
    assert (
        ev.ruta_ok({"id": "R23"}, _salida(), {"herramienta_esperada": "ninguna"})["score"] == 1
    )  # un saludo no debe usar herramientas
    assert ev.ruta_ok({"id": "R23"}, _salida("buscar_en_base"), {"herramienta_esperada": "ninguna"})["score"] == 0


def test_detalle_ok_exige_parametros_y_texto_solo_cuando_la_matriz_los_pide():
    ref = {"herramienta_esperada": "consultar_datos", "parametros_esperados": "tabla=sedes; ciudad=Ibagué"}
    assert ev.detalle_ok({"id": "R01"}, _salida("consultar_datos"), ref)["score"] == 1
    assert (
        ev.detalle_ok(
            {"id": "R01"},
            {
                "respuesta": "x",
                "llamadas": [{"herramienta": "consultar_datos", "args": {"tabla": "sedes", "ciudad": "Cali"}}],
            },
            ref,
        )["score"]
        == 0
    )
    sin_exigencias = {"herramienta_esperada": "ninguna", "parametros_esperados": ""}
    assert ev.detalle_ok({"id": "R23"}, _salida(), sin_exigencias)["score"] == 1
    assert (
        ev.detalle_ok({"id": "R20"}, _salida(respuesta="Sí hay"), sin_exigencias)["score"] == 0
    )  # R20 exige «solo atiendo temas de Celsia»
    assert ev.detalle_ok({"id": "R20"}, _salida(respuesta="Eso se sale de lo que puedo ayudarte: solo atiendo temas de Celsia."), sin_exigencias)["score"] == 1


def test_n_llamadas_cuenta_las_herramientas_pedidas():
    assert ev.n_llamadas({}, _salida("buscar_en_base", "consultar_datos"), {}) == {"key": "n_llamadas", "score": 2}


def test_las_dos_configuraciones_difieren_en_el_tope_de_herramientas():
    assert ev.CONFIGURACIONES["con_tope"] == 4 and ev.CONFIGURACIONES["sin_tope"] > 4


def test_la_matriz_solo_espera_herramientas_que_el_agente_tiene():
    """Si una herramienta se renombra o se quita, la matriz debe cambiar con ella (antes seguía esperando `consultar_datos`)."""
    from taaml.agente import HERRAMIENTAS

    reales = {h.name for h in HERRAMIENTAS} | {"ninguna"}
    for ejemplo in ev.cargar_ejemplos():
        nombres = set(ejemplo["outputs"]["herramienta_esperada"].replace("+", "|").split("|"))
        assert nombres <= reales, (ejemplo["inputs"]["id"], nombres - reales)


def test_la_sintaxis_de_la_matriz_distingue_alternativas_y_obligatorias():
    ok = ev.matriz.enrutamiento_ok
    assert ok("a|b", {"b"}) and ok("a|b", {"a", "z"}) and not ok("a|b", {"z"}) and not ok("a|b", set())
    assert ok("a|b+c", {"b", "c"}) and not ok("a|b+c", {"a"}) and not ok("a|b+c", {"c"})
    assert ok("ninguna", set()) and not ok("ninguna", {"a"})
    assert ok("ninguna|a", set()) and ok("ninguna|a", {"a"}) and not ok("ninguna|a", {"a", "z"})
