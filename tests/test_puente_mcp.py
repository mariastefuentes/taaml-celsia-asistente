"""Puente OpenClaw → agente de Celsia: el MCP de una herramienta y el plugin que fija quién escribe."""

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from taaml import puente_mcp
from taaml.puente_mcp import MENSAJE_DE_FALLO, MENSAJE_NO_AUTORIZADO, atender

RAIZ = Path(__file__).resolve().parents[1]
PLUGIN = RAIZ / "openclaw" / "plugins" / "puente-celsia.js"


class _Respuesta:
    def __init__(self, estado=200, cuerpo=None):
        self.status_code = estado
        self._cuerpo = cuerpo or {}

    def json(self):
        return self._cuerpo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture(autouse=True)
def _entorno(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ALLOWLIST", "573001112233")
    monkeypatch.setenv("CHAT_TOKEN", "token-de-prueba")
    monkeypatch.delenv("CELSIA_API_URL", raising=False)


def test_la_herramienta_pasa_el_mensaje_al_agente_y_devuelve_su_respuesta(monkeypatch):
    enviado = {}

    def falso_post(url, json, headers, timeout):
        enviado.update(url=url, json=json, headers=headers, timeout=timeout)
        return _Respuesta(cuerpo={"respuesta": "La línea es 01 8000 112 115.", "herramientas": [], "ok": True})

    monkeypatch.setattr(puente_mcp.requests, "post", falso_post)
    assert atender("¿Cuál es la línea?", "+573001112233") == "La línea es 01 8000 112 115."
    assert enviado["url"] == "http://127.0.0.1:8000/chat"
    assert enviado["json"] == {"mensaje": "¿Cuál es la línea?", "telefono": "+573001112233", "canal": "whatsapp"}
    assert enviado["headers"] == {"X-Api-Key": "token-de-prueba"}


def test_un_numero_fuera_de_la_allowlist_o_mal_escrito_no_llega_al_agente(monkeypatch):
    monkeypatch.setattr(puente_mcp.requests, "post", lambda *a, **k: pytest.fail("no debía llamar al agente"))
    assert atender("hola", "+573009998877") == MENSAJE_NO_AUTORIZADO  # no está en la lista
    assert atender("hola", "3001112233") == MENSAJE_NO_AUTORIZADO  # sin formato E.164
    assert atender("hola", "+570000000000") == MENSAJE_NO_AUTORIZADO  # el comodín que escribe el modelo se reemplaza antes en el plugin


def test_con_la_lista_abierta_cualquier_numero_valido_pasa(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ALLOWLIST", "*")
    enviado = {}

    def falso_post(url, json, headers, timeout):
        enviado.update(json=json)
        return _Respuesta(cuerpo={"respuesta": "Hola, ¿en qué te ayudo?"})

    monkeypatch.setattr(puente_mcp.requests, "post", falso_post)
    assert atender("hola", "+573009998877") == "Hola, ¿en qué te ayudo?"
    assert enviado["json"]["telefono"] == "+573009998877"


def test_si_el_agente_falla_el_cliente_recibe_un_mensaje_cortes_sin_detalles(monkeypatch):
    def caido(*a, **k):
        raise ConnectionError("connection refused 127.0.0.1:8000")

    monkeypatch.setattr(puente_mcp.requests, "post", caido)
    texto = atender("hola", "+573001112233")
    assert texto == MENSAJE_DE_FALLO and "127.0.0.1" not in texto
    monkeypatch.setattr(puente_mcp.requests, "post", lambda *a, **k: _Respuesta(500))
    assert atender("hola", "+573001112233") == MENSAJE_DE_FALLO


def test_el_limite_por_telefono_se_le_dice_al_cliente(monkeypatch):
    monkeypatch.setattr(
        puente_mcp.requests, "post", lambda *a, **k: _Respuesta(429, {"detail": "Vas muy rápido: espera un momento."})
    )
    assert atender("hola", "+573001112233") == "Vas muy rápido: espera un momento."


def test_un_mensaje_largo_se_recorta_al_limite_de_la_api(monkeypatch):
    enviado = {}
    monkeypatch.setattr(
        puente_mcp.requests,
        "post",
        lambda url, json, headers, timeout: enviado.update(json) or _Respuesta(cuerpo={"respuesta": "ok"}),
    )
    atender("a" * 5000, "+573001112233")
    assert len(enviado["mensaje"]) == 1000


def test_el_servidor_expone_una_sola_herramienta():
    import asyncio

    herramientas = asyncio.run(puente_mcp.servidor.list_tools())
    assert [h.name for h in herramientas] == ["atender_cliente_celsia"]


@pytest.mark.skipif(shutil.which("node") is None, reason="necesita Node (viene con OpenClaw)")
def test_el_plugin_reemplaza_el_telefono_por_el_remitente_verificado(tmp_path):
    """Ejecuta el gancho real con un `definePluginEntry` de mentira: el teléfono que escribe el modelo se descarta.

    En las herramientas MCP, OpenClaw 2026.11.6 no entrega `requester`: ahí el número sale del nombre del chat directo (D52).
    """
    sdk = tmp_path / "node_modules" / "openclaw" / "plugin-sdk"
    sdk.mkdir(parents=True)
    (tmp_path / "node_modules" / "openclaw" / "package.json").write_text(
        '{"name":"openclaw","type":"module","exports":{"./plugin-sdk/plugin-entry":"./plugin-sdk/plugin-entry.js"}}'
    )
    (sdk / "plugin-entry.js").write_text("export const definePluginEntry = (x) => x;")
    (tmp_path / "puente-celsia.js").write_text(PLUGIN.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "package.json").write_text('{"type":"module"}')
    (tmp_path / "prueba.mjs").write_text(
        textwrap.dedent(
            """
            import { fijarRemitente, remitenteE164 } from "./puente-celsia.js";
            const salida = {
              verificado: fijarRemitente(
                { toolName: "puente__atender_cliente_celsia", params: { mensaje: "hola", telefono: "+573009998877" } },
                { requester: { channel: "whatsapp", senderId: "573001112233" } }),
              con_mas: remitenteE164({ senderId: "+57 300 111 2233" }),
              sin_remitente: fijarRemitente({ toolName: "puente__atender_cliente_celsia", params: { mensaje: "hola" } }, {}),
              otra_herramienta: fijarRemitente({ toolName: "celsia__consultar_sedes_celsia", params: {} }, {}) ?? null,
              basura: remitenteE164({ senderId: "abc" }),
            };
            const conSesion = (sessionKey, resto = {}) => fijarRemitente(
              { toolName: "puente__atender_cliente_celsia", params: { mensaje: "hola", telefono: "+573009998877" } },
              { sessionKey, ...resto });
            salida.por_sesion = conSesion("agent:main:whatsapp:direct:+573001112233");
            salida.requester_invalido = conSesion("agent:main:whatsapp:direct:+573001112233", { requester: { senderId: "abc" } });
            salida.sesiones_sin_cliente = [
              "agent:main:main",
              "agent:main:whatsapp:group:120363000000000000@g.us",
              "agent:main:whatsapp:direct:123456789012345@lid",
              "agent:main:whatsapp:direct:573001112233",
              "agent:main:telegram:direct:573001112233",
              "agent:main:subagent:agent:main:whatsapp:direct:+573001112233",
              "agent:main:whatsapp:direct:+573001112233:otro",
            ].map((clave) => conSesion(clave));
            console.log(JSON.stringify(salida));
            """
        )
    )
    resultado = subprocess.run(["node", "prueba.mjs"], cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert resultado.returncode == 0, resultado.stderr
    import json

    salida = json.loads(resultado.stdout)
    assert salida["verificado"] == {"params": {"mensaje": "hola", "telefono": "+573001112233"}}  # gana el remitente, no lo que pidió el modelo
    assert salida["con_mas"] == "+573001112233"
    assert salida["sin_remitente"]["block"] is True
    assert salida["otra_herramienta"] is None
    assert salida["basura"] == ""
    assert salida["por_sesion"] == {"params": {"mensaje": "hola", "telefono": "+573001112233"}}  # sin requester: el chat directo de WhatsApp
    assert salida["requester_invalido"]["block"] is True  # si OpenClaw entrega un remitente, no se busca otro
    assert [r.get("block") for r in salida["sesiones_sin_cliente"]] == [True] * 7  # terminal, grupo, sin número, otro canal o subagente


def test_telefono_vacio_o_sin_formato_no_llega_al_agente(monkeypatch):
    monkeypatch.setattr(puente_mcp.requests, "post", lambda *a, **k: pytest.fail("no debía llamar al agente"))
    assert atender("hola", "") == MENSAJE_NO_AUTORIZADO
    assert atender("hola", "   ") == MENSAJE_NO_AUTORIZADO
    assert atender("hola", None) == MENSAJE_NO_AUTORIZADO  # sin número no se consulta al agente


def test_respuesta_sin_texto_y_429_sin_detalle_reciben_el_mensaje_de_fallo(monkeypatch):
    monkeypatch.setattr(puente_mcp.requests, "post", lambda *a, **k: _Respuesta(cuerpo={}))
    assert atender("hola", "+573001112233") == MENSAJE_DE_FALLO  # falta la clave «respuesta»
    monkeypatch.setattr(puente_mcp.requests, "post", lambda *a, **k: _Respuesta(429))
    assert atender("hola", "+573001112233") == MENSAJE_DE_FALLO  # sin detalle del proveedor


def test_url_con_barra_final_no_duplica_el_slash_y_respuesta_no_texto_no_rompe(monkeypatch):
    enviado = {}

    def falso_post(url, json, headers, timeout):
        enviado.update(url=url)
        return _Respuesta(cuerpo={"respuesta": 12345})  # lo convierte a texto

    monkeypatch.setattr(puente_mcp.requests, "post", falso_post)
    monkeypatch.setenv("CELSIA_API_URL", "http://127.0.0.1:8000/")
    assert atender("hola", "+573001112233") == "12345"
    assert enviado["url"] == "http://127.0.0.1:8000/chat"
