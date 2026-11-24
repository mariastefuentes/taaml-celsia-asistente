"""La configuración versionada de OpenClaw: se resuelve, se valida el endurecimiento y se instala sin secretos."""

import json
import re

import pytest

from taaml.openclaw import RAIZ, ConfiguracionInvalida, configuracion, instalar, problemas

ENTORMO = {
    "OPENCLAW_GATEWAY_TOKEN": "token-de-prueba",
    "WHATSAPP_ALLOWLIST": "+573001112233, +573104445566",
    "REPO_CELSIA": "C:/ruta/al/repo",
}

NAMES_MCP = [
    "buscar_informacion_celsia",
    "consultar_sedes_celsia",
    "consultar_contactos_celsia",
    "consultar_catalogo_celsia",
    "consultar_canales_de_atencion_celsia",
    "consultar_cobertura_celsia",
    "consultar_tramite_en_linea_celsia",
    "consultar_politica_de_datos_celsia",
    "verificar_canal_oficial_celsia",
    "calcular_factura_estimada_celsia",
]


def test_la_plantilla_cumple_el_endurecimiento_de_la_rubrica():
    config = configuracion(ENTORMO)
    assert problemas(config) == []
    assert config["gateway"]["mode"] == "local"
    assert config["gateway"]["bind"] == "loopback"
    assert config["tools"]["fs"]["workspaceOnly"] is True
    assert config["channels"]["whatsapp"]["dmPolicy"] == "open"
    assert config["channels"]["whatsapp"]["allowFrom"] == ["*"]
    assert config["session"]["dmScope"] == "per-channel-peer"
    assert config["agents"]["defaults"]["sandbox"]["mode"] == "all"
    assert config["agents"]["defaults"]["sandbox"]["backend"] == "docker"
    assert config["agents"]["defaults"]["sandbox"]["scope"] == "agent"
    assert config["agents"]["defaults"]["sandbox"]["workspaceAccess"] == "none"
    assert config["agents"]["defaults"]["sandbox"]["docker"]["image"] == "openclaw-sandbox:trixie-slim"
    assert config["agents"]["defaults"]["workspace"] == "~/.openclaw/workspace"
    assert set(config["agents"]["entries"]) == {"main"}
    assert config["agents"]["entries"]["main"]["workspace"] == "~/.openclaw/workspace"
    assert config["plugins"]["entries"]["whatsapp"]["enabled"] is True
    assert config["env"]["shellEnv"]["enabled"] is True
    assert set(config["mcp"]["servers"]["celsia"]["toolFilter"]["include"]) == set(NAMES_MCP)


def test_la_plantilla_no_trae_secretos_versionados():
    texto = (RAIZ / "openclaw" / "openclaw.example.json").read_text(encoding="utf-8")
    assert not re.search(r"(sk-|AIza|ghp_|xoxb-)", texto)
    for clave in ("token", "apiKey", "api_key"):
        for valor in re.findall(rf'"{clave}"\s*:\s*"([^"]+)"', texto):
            assert valor.startswith("${") or valor == "token", f"valor no parametrizado: {valor}"


def test_falta_una_variable_y_lo_dice():
    with pytest.raises(ConfiguracionInvalida, match="OPENCLAW_GATEWAY_TOKEN"):
        configuracion({**ENTORMO, "OPENCLAW_GATEWAY_TOKEN": ""})


def test_una_dm_policy_invalida_se_marca():
    config = configuracion(ENTORMO)
    config["channels"]["whatsapp"]["dmPolicy"] = "pairing"
    assert any("dmPolicy" in fallo for fallo in problemas(config))


def test_open_sin_asterisco_en_allowFrom_se_marca():
    config = configuracion(ENTORMO)
    config["channels"]["whatsapp"]["allowFrom"] = []
    assert any("«*»" in fallo for fallo in problemas(config))


def test_allowlist_que_no_es_e164_se_marca():
    config = configuracion(ENTORMO)
    config["channels"]["whatsapp"]["dmPolicy"] = "allowlist"
    config["channels"]["whatsapp"]["allowFrom"] = ["3001112233"]
    assert any("E.164" in fallo for fallo in problemas(config))


def test_un_endurecimiento_debilitado_se_detecta():
    config = configuracion(ENTORMO)
    config["gateway"]["bind"] = "0.0.0.0"
    config["tools"]["deny"] = []
    config["tools"]["fs"]["workspaceOnly"] = False
    fallos = problemas(config)
    assert len(fallos) >= 3


def test_instalar_escribe_configuracion_y_respeta_lo_existente(tmp_path):
    escritos = instalar(tmp_path, ENTORMO)
    archivo = tmp_path / "openclaw.json"
    assert archivo in escritos and json.loads(archivo.read_text(encoding="utf-8"))["gateway"]["bind"] == "loopback"
    with pytest.raises(ConfiguracionInvalida, match="Ya existe"):
        instalar(tmp_path, ENTORMO)
    instalar(tmp_path, ENTORMO, forzar=True)
    assert (tmp_path / "openclaw.json.bak").exists()


def test_el_script_existe_y_la_plantilla_esta_versionada():
    assert (RAIZ / "scripts" / "47_openclaw_instalar.py").exists()
    assert (RAIZ / "openclaw" / "openclaw.example.json").exists()


def _problemas_con_mutante(mutante):
    config = configuracion(ENTORMO)
    mutante(config)
    return problemas(config)


def test_eliminar_el_sandbox_completo_se_detecta():
    def mutante(config):
        sandbox = config["agents"]["defaults"]["sandbox"]
        sandbox["mode"] = "none"
        sandbox["backend"] = "local"
        sandbox["scope"] = "nope"
        sandbox["workspaceAccess"] = "workspace"
        sandbox["docker"] = {}

    fallos = _problemas_con_mutante(mutante)
    assert any("mode" in f for f in fallos) and any("backend" in f for f in fallos)
    assert any("scope" in f for f in fallos) and any("workspaceAccess" in f for f in fallos)
    assert any("docker.image" in f for f in fallos)


def test_herramientas_fuera_del_deny_exec_elevated_y_allowFrom_vacias_se_detectan():
    def mutante(config):
        config["tools"]["deny"] = []
        config["tools"]["exec"]["mode"] = "allow"
        config["tools"]["elevated"]["enabled"] = True
        config["channels"]["whatsapp"]["allowFrom"] = []

    fallos = _problemas_con_mutante(mutante)
    assert any("deny" in f for f in fallos)
    assert any("exec" in f for f in fallos) and any("elevated" in f for f in fallos)
    assert any("allowFrom" in f for f in fallos)


def test_servidor_puente_eliminado_o_plugin_desactivado_se_detectan():
    def mutante(config):
        del config["mcp"]["servers"]["puente"]
    assert any("puente" in f for f in _problemas_con_mutante(mutante))

    def mutante_plugin(config):
        config["plugins"]["entries"]["puente-celsia"]["enabled"] = False
    assert any("puente-celsia" in f for f in _problemas_con_mutante(mutante_plugin))


def test_tool_search_habilitado_se_detecta():
    def mutante(config):
        config["tools"]["toolSearch"] = True
    assert any("toolSearch" in f for f in _problemas_con_mutante(mutante))


def test_la_plantilla_vigente_no_tiene_fallos():
    assert problemas(configuracion(ENTORMO)) == []
