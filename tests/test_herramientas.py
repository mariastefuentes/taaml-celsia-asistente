"""El catálogo de las 20 herramientas: nombres únicos, descripción y esquema que ve el modelo."""

from pathlib import Path

from taaml.agente import APROBACION_HUMANA, HERRAMIENTAS

RAIZ = Path(__file__).resolve().parents[1]


def test_hay_veinte_con_nombres_unicos():
    nombres = [h.name for h in HERRAMIENTAS]
    assert len(nombres) == 20 and len(set(nombres)) == 20


def test_cada_herramienta_tiene_descripcion_y_esquema_para_el_modelo():
    for herramienta in HERRAMIENTAS:
        assert (herramienta.description or "").strip(), herramienta.name
        esquema = herramienta.tool_call_schema.model_json_schema()
        assert isinstance(esquema.get("properties", {}), dict), herramienta.name


def test_las_que_escriben_o_radican_piden_aprobacion_humana():
    assert {"radicar_reclamo", "cancelar_reclamo", "reportar_dano_electrico"} <= set(APROBACION_HUMANA)


def test_el_script_del_catalogo_existe():
    assert (RAIZ / "scripts" / "49_listar_herramientas.py").is_file()
