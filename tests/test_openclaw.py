"""La configuración versionada de OpenClaw: se resuelve, se valida el endurecimiento y se instala sin secretos."""

import json
import re

import pytest

from taaml.openclaw import RAIZ, ConfiguracionInvalida, configuracion, instalar, problemas

ENTORNO = {
    "OPENCLAW_GATEWAY_TOKEN": "token-de-prueba",
    "WHATSAPP_ALLOWLIST": "+573001112233, +573104445566",
    "REPO_CELSIA": "C:/ruta/al/repo",
}


def test_la_plantilla_cumple_el_endurecimiento_de_la_rubrica():
    config = configuracion(ENTORNO)
    assert problemas(config) == []
    assert config["gateway"]["bind"] == "loopback"
    assert config["tools"]["fs"]["workspaceOnly"] is True
    assert config["channels"]["whatsapp"]["dmScope"] == "per-channel-peer"


def test_la_plantilla_no_trae_secretos_versionados():
    texto = (RAIZ / "openclaw" / "openclaw.example.json").read_text(encoding="utf-8")
    assert not re.search(r"(sk-|AIza|ghp_|xoxb-)", texto)
    for clave in ("token", "apiKey", "api_key"):
        for valor in re.findall(rf'"{clave}"\s*:\s*"([^"]+)"', texto):
            assert valor.startswith("${") or valor == "token", f"valor no parametrizado: {valor}"


def test_falta_una_variable_y_lo_dice():
    with pytest.raises(ConfiguracionInvalida, match="OPENCLAW_GATEWAY_TOKEN"):
        configuracion({**ENTORNO, "OPENCLAW_GATEWAY_TOKEN": ""})


def test_una_allowlist_que_no_es_e164_se_marca():
    config = configuracion({**ENTORNO, "WHATSAPP_ALLOWLIST": "3001112233"})
    assert any("E.164" in fallo for fallo in problemas(config))


def test_un_endurecimiento_debilitado_se_detecta():
    config = configuracion(ENTORNO)
    config["gateway"]["bind"] = "0.0.0.0"
    config["tools"]["deny"] = []
    config["tools"]["fs"]["workspaceOnly"] = False
    fallos = problemas(config)
    assert len(fallos) >= 3


def test_instalar_escribe_configuracion_y_respeta_lo_existente(tmp_path):
    escritos = instalar(tmp_path, ENTORNO)
    archivo = tmp_path / "openclaw.json"
    assert archivo in escritos and json.loads(archivo.read_text(encoding="utf-8"))["gateway"]["bind"] == "loopback"
    with pytest.raises(ConfiguracionInvalida, match="Ya existe"):
        instalar(tmp_path, ENTORNO)
    instalar(tmp_path, ENTORNO, forzar=True)
    assert (tmp_path / "openclaw.json.bak").exists()


def test_el_script_existe_y_la_plantilla_esta_versionada():
    assert (RAIZ / "scripts" / "47_openclaw_instalar.py").exists()
    assert (RAIZ / "openclaw" / "openclaw.example.json").exists()
