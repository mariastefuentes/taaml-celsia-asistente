import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("evaluar_en_langsmith", RAIZ / "scripts" / "24_evaluar_en_langsmith.py")
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)


def test_el_dataset_sale_de_la_matriz_con_las_25_preguntas():
    ejemplos = ev.cargar_ejemplos()
    assert len(ejemplos) == 25
    r01 = ejemplos[0]
    assert r01["inputs"]["id"] == "R01" and r01["outputs"]["herramienta_esperada"] == "consultar_datos"
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
    )  # R20 exige «No tengo esa información»
    assert ev.detalle_ok({"id": "R20"}, _salida(respuesta="No tengo esa información."), sin_exigencias)["score"] == 1


def test_n_llamadas_cuenta_las_herramientas_pedidas():
    assert ev.n_llamadas({}, _salida("buscar_en_base", "consultar_datos"), {}) == {"key": "n_llamadas", "score": 2}


def test_las_dos_configuraciones_difieren_en_el_tope_de_herramientas():
    assert ev.CONFIGURACIONES["con_tope"] == 4 and ev.CONFIGURACIONES["sin_tope"] > 4
