import importlib.util
from pathlib import Path

RUTA = Path(__file__).resolve().parent.parent / "scripts" / "30_limpiar_memoria_demo.py"


def _modulo():
    spec = importlib.util.spec_from_file_location("limpiar", RUTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _almacen_con_datos(tmp_path):
    from taaml.agente import almacen_de_largo_plazo

    almacen = almacen_de_largo_plazo(tmp_path / "lp.sqlite")
    almacen.put(("perfil", "ana"), "a1", {"dato": "Trabaja en Carvajal"})
    almacen.put(("perfil", "luis"), "l1", {"dato": "Vive en Cali"})
    return almacen


def test_sin_borrar_solo_lista_y_no_toca_nada(tmp_path):
    almacen = _almacen_con_datos(tmp_path)
    antes = _modulo().limpiar(almacen, borrar=False)
    assert antes == {"ana": ["Trabaja en Carvajal"], "luis": ["Vive en Cali"]}
    assert len(almacen.search(("perfil", "ana"))) == 1


def test_con_borrar_deja_la_memoria_vacia_y_devuelve_lo_que_habia(tmp_path):
    almacen = _almacen_con_datos(tmp_path)
    modulo = _modulo()
    assert modulo.limpiar(almacen, borrar=True) == {"ana": ["Trabaja en Carvajal"], "luis": ["Vive en Cali"]}
    assert modulo.clientes_con_datos(almacen) == []
