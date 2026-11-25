"""El workspace de OpenClaw: identidad separada de los límites, memoria sin datos de clientes y bitácora."""

from pathlib import Path

from taaml.openclaw import RAIZ, configuracion, instalar
from taaml.skills import verificar_skills

WORKSPACE = RAIZ / "openclaw" / "workspace"
OBLIGATORIOS = ("SOUL.md", "AGENTS.md", "USER.md", "MEMORY.md")
SKILL = "atencion-whatsapp-celsia"


def test_el_workspace_tiene_los_cuatro_archivos_y_la_bitacora():
    for nombre in OBLIGATORIOS:
        assert (WORKSPACE / nombre).read_text(encoding="utf-8").strip(), nombre
    assert (WORKSPACE / "bitacora" / "PLANTILLA.md").exists()


def test_la_identidad_y_los_limites_estan_separados():
    alma = (WORKSPACE / "SOUL.md").read_text(encoding="utf-8")
    assert "Asistente Celsia" in alma and "proyecto académico" in alma
    assert "No eres un canal oficial de Celsia" in alma
    assert "vive en `AGENTS.md`" in alma  # la identidad remite a los límites
    assert "Líneas rojas" not in alma  # las red lines no se mezclan con el tono


def test_las_lineas_rojas_cubren_lo_que_evalua_la_rubrica():
    limites = (WORKSPACE / "AGENTS.md").read_text(encoding="utf-8").lower()
    for regla in ("no inventes", "cédulas", "contraseñas", "aprobación de una persona", "workspace", "deriva a una persona"):
        assert regla in limites, regla
    assert "no ejecutes comandos" in limites


def test_la_memoria_del_workspace_no_guarda_datos_de_clientes():
    memoria = (WORKSPACE / "MEMORY.md").read_text(encoding="utf-8")
    assert "Nada de clientes" in memoria and "cédulas" in memoria


def test_el_instalador_copia_tambien_la_bitacora(tmp_path):
    entorno = {"OPENCLAW_GATEWAY_TOKEN": "token", "WHATSAPP_ALLOWLIST": "+573001112233", "REPO_CELSIA": str(RAIZ)}
    escritos = instalar(tmp_path, entorno)
    destino = tmp_path / "workspace"
    for nombre in OBLIGATORIOS:
        assert destino / nombre in escritos
    assert (destino / "bitacora" / "PLANTILLA.md").exists()
    assert (destino / "skills" / SKILL / "SKILL.md").exists()
    assert Path(tmp_path / "openclaw.json").exists()


def test_la_skill_de_openclaw_es_valida_y_sigue_el_puente():
    assert verificar_skills(WORKSPACE / "skills") == []
    skill = (WORKSPACE / "skills" / SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "user-invocable: false" in skill  # ningún cliente la dispara como comando
    for pieza in ("atender_cliente_celsia", "puente-celsia", "01 8000 112 115", "AGENTS.md", "aprobación de una persona"):
        assert pieza in skill, pieza


def test_la_plantilla_deja_leer_solo_las_skills_del_proyecto():
    entorno = {"OPENCLAW_GATEWAY_TOKEN": "token", "WHATSAPP_ALLOWLIST": "*", "REPO_CELSIA": str(RAIZ)}
    config = configuracion(entorno)
    propias = sorted(p.parent.name for p in (WORKSPACE / "skills").glob("*/SKILL.md"))
    assert config["agents"]["defaults"]["skills"] == propias == [SKILL]  # sin las skills que trae OpenClaw
    assert "skills_read" in config["tools"]["alsoAllow"]
    assert "skills_read" in config["tools"]["sandbox"]["tools"]["alsoAllow"]
    assert "group:fs" in config["tools"]["deny"]  # leer la skill no abre el sistema de archivos
