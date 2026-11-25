import hashlib
import hmac
import json

import pytest
import requests
from fastapi.testclient import TestClient

import api.main as api_main
from api.main import RespuestaDelAgente, app
from taaml import whatsapp

cliente = TestClient(app)
SECRETO = "secreto-de-prueba"


def _firmar(cuerpo: bytes, secreto: str = SECRETO) -> dict:
    return {"X-Hub-Signature-256": "sha256=" + hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()}


def _aviso(id_mensaje="wamid.1", telefono="573001234567", tipo="text", texto="¿Qué sedes hay?") -> bytes:
    mensaje = {"id": id_mensaje, "from": telefono, "type": tipo}
    if tipo == "text":
        mensaje["text"] = {"body": texto}
    carga = {"entry": [{"changes": [{"value": {"messages": [mensaje]}}]}]}
    return json.dumps(carga).encode()


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", SECRETO)
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "palabra-de-verificacion")
    api_main._AVISOS_VISTOS.clear()


# --- módulo whatsapp ---
def test_firma_valida_solo_con_el_secreto_y_el_cuerpo_exactos():
    cuerpo = b'{"a": 1}'
    cabecera = _firmar(cuerpo)["X-Hub-Signature-256"]
    assert whatsapp.firma_valida(cuerpo, cabecera, SECRETO)
    assert not whatsapp.firma_valida(cuerpo + b" ", cabecera, SECRETO)
    assert not whatsapp.firma_valida(cuerpo, cabecera, "otro")
    assert not whatsapp.firma_valida(cuerpo, None, SECRETO)
    assert not whatsapp.firma_valida(cuerpo, cabecera.removeprefix("sha256="), SECRETO)


def test_mensajes_entrantes_lee_texto_y_ignora_avisos_de_estado():
    carga = json.loads(_aviso(texto="¿Cuánto cuesta?"))
    assert whatsapp.mensajes_entrantes(carga) == [
        {"id": "wamid.1", "telefono": "573001234567", "tipo": "text", "texto": "¿Cuánto cuesta?", "audio": ""}
    ]
    estado = {"entry": [{"changes": [{"value": {"statuses": [{"id": "x", "status": "read"}]}}]}]}
    assert whatsapp.mensajes_entrantes(estado) == [] and whatsapp.mensajes_entrantes({}) == []
    imagen = whatsapp.mensajes_entrantes(json.loads(_aviso(tipo="image")))
    assert imagen[0]["tipo"] == "image" and imagen[0]["texto"] == ""


def test_enviar_texto_sin_configurar_no_llama_a_meta(monkeypatch):
    monkeypatch.delenv("WHATSAPP_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_PHONE_NUMBER_ID", raising=False)
    monkeypatch.setattr(whatsapp.requests, "post", lambda *a, **k: pytest.fail("no debía llamar a Meta"))
    assert whatsapp.enviar_texto("573001234567", "hola") is False


def test_enviar_texto_arma_la_peticion_y_recorta_el_texto(monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "tok")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "999")
    visto = {}

    class Respuesta:
        ok = True

    def falso(url, json, headers, timeout):
        visto.update(url=url, json=json, headers=headers)
        return Respuesta()

    monkeypatch.setattr(whatsapp.requests, "post", falso)
    assert whatsapp.enviar_texto("573001234567", "x" * 5000) is True
    assert visto["url"].endswith("/999/messages") and visto["headers"] == {"Authorization": "Bearer tok"}
    assert visto["json"]["to"] == "573001234567" and len(visto["json"]["text"]["body"]) == whatsapp.LIMITE_TEXTO


def test_enviar_texto_tolera_fallos_de_red_y_rechazos(monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "tok")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "999")

    def sin_red(*a, **k):
        raise requests.ConnectionError("caído")

    monkeypatch.setattr(whatsapp.requests, "post", sin_red)
    assert whatsapp.enviar_texto("573001234567", "hola") is False

    class Rechazo:
        ok = False
        status_code = 400
        text = "573001234567 hola"

        def json(self):
            return {"error": {"code": 131030}}

    monkeypatch.setattr(whatsapp.requests, "post", lambda *a, **k: Rechazo())
    assert whatsapp.enviar_texto("573001234567", "hola") is False


# --- rutas del webhook ---
def test_verificacion_devuelve_el_desafio_solo_con_el_token_correcto():
    base = {"hub.mode": "subscribe", "hub.challenge": "12345"}
    r = cliente.get("/webhook/whatsapp", params={**base, "hub.verify_token": "palabra-de-verificacion"})
    assert r.status_code == 200 and r.text == "12345"
    assert cliente.get("/webhook/whatsapp", params={**base, "hub.verify_token": "mala"}).status_code == 403
    assert cliente.get("/webhook/whatsapp", params={"hub.verify_token": "palabra-de-verificacion"}).status_code == 403


def test_verificacion_deshabilitada_sin_token_configurado(monkeypatch):
    monkeypatch.delenv("WHATSAPP_VERIFY_TOKEN")
    assert cliente.get("/webhook/whatsapp", params={"hub.mode": "subscribe", "hub.challenge": "1"}).status_code == 503


def test_recibir_exige_secreto_y_firma_valida(monkeypatch):
    cuerpo = _aviso()
    assert cliente.post("/webhook/whatsapp", content=cuerpo).status_code == 401
    assert cliente.post("/webhook/whatsapp", content=cuerpo, headers=_firmar(cuerpo, "falso")).status_code == 401
    monkeypatch.delenv("WHATSAPP_APP_SECRET")
    assert cliente.post("/webhook/whatsapp", content=cuerpo, headers=_firmar(cuerpo)).status_code == 503


def test_recibir_rechaza_cuerpos_que_no_son_json():
    cuerpo = b"no es json"
    assert cliente.post("/webhook/whatsapp", content=cuerpo, headers=_firmar(cuerpo)).status_code == 400


def test_un_mensaje_de_texto_llega_al_agente_y_la_respuesta_sale_por_whatsapp(monkeypatch):
    preguntas, enviados = [], []

    def agente(telefono, mensaje, canal="chat"):
        preguntas.append((telefono, mensaje))
        return RespuestaDelAgente(respuesta="Hola, soy el asistente", herramientas=[], ok=True)

    monkeypatch.setattr(api_main, "responder_a_telefono", agente)
    monkeypatch.setattr(api_main, "enviar_texto", lambda tel, texto: enviados.append((tel, texto)) or True)
    cuerpo = _aviso(texto="  ¿Dónde queda la sede de Cali?  ")
    r = cliente.post("/webhook/whatsapp", content=cuerpo, headers=_firmar(cuerpo))
    assert r.status_code == 200 and r.json() == {"ok": True, "mensajes": 1}
    assert preguntas == [("573001234567", "¿Dónde queda la sede de Cali?")]
    assert enviados == [("573001234567", "Hola, soy el asistente")]


def test_un_reintento_de_meta_no_se_atiende_dos_veces(monkeypatch):
    preguntas = []
    monkeypatch.setattr(
        api_main,
        "responder_a_telefono",
        lambda t, m, canal="chat": preguntas.append(m) or RespuestaDelAgente(respuesta="ok", herramientas=[], ok=True),
    )
    monkeypatch.setattr(api_main, "enviar_texto", lambda *a: True)
    cuerpo = _aviso(id_mensaje="wamid.repetido")
    for _ in range(3):
        cliente.post("/webhook/whatsapp", content=cuerpo, headers=_firmar(cuerpo))
    assert len(preguntas) == 1


def test_lo_que_no_es_texto_recibe_una_respuesta_amable_sin_llamar_al_agente(monkeypatch):
    enviados = []
    monkeypatch.setattr(api_main, "responder_a_telefono", lambda *a, **k: pytest.fail("no debía llamar al agente"))
    monkeypatch.setattr(api_main, "enviar_texto", lambda tel, texto: enviados.append(texto) or True)
    cuerpo = _aviso(tipo="image")
    assert cliente.post("/webhook/whatsapp", content=cuerpo, headers=_firmar(cuerpo)).status_code == 200
    assert enviados == [whatsapp.TEXTO_NO_SOPORTADO]


def test_los_avisos_de_estado_no_generan_respuesta(monkeypatch):
    monkeypatch.setattr(api_main, "enviar_texto", lambda *a: pytest.fail("no debía enviar nada"))
    cuerpo = json.dumps({"entry": [{"changes": [{"value": {"statuses": [{"id": "x", "status": "read"}]}}]}]}).encode()
    r = cliente.post("/webhook/whatsapp", content=cuerpo, headers=_firmar(cuerpo))
    assert r.status_code == 200 and r.json()["mensajes"] == 0


def test_un_fallo_al_atender_no_tumba_el_webhook(monkeypatch):
    def roto(*a, **k):
        raise RuntimeError("falla interna")

    monkeypatch.setattr(api_main, "responder_a_telefono", roto)
    cuerpo = _aviso()
    assert cliente.post("/webhook/whatsapp", content=cuerpo, headers=_firmar(cuerpo)).status_code == 200


def test_el_registro_de_avisos_vistos_tiene_tope(monkeypatch):
    monkeypatch.setattr(api_main, "MAX_AVISOS_VISTOS", 3)
    for i in range(10):
        api_main._ya_atendido(f"id{i}")
    assert len(api_main._AVISOS_VISTOS) == 3 and api_main._ya_atendido("id9") is True


def test_el_webhook_registra_el_id_corto_y_si_el_mensaje_es_repetido(caplog):
    cuerpo = _aviso(id_mensaje="wamid.HBgMNTczMDAxMjM0NTY3", texto="hola")
    with caplog.at_level("INFO", logger="taaml.api"):
        for _ in range(2):
            cliente.post("/webhook/whatsapp", content=cuerpo, headers=_firmar(cuerpo))
    lineas = [r.getMessage() for r in caplog.records if "mensaje de WhatsApp" in r.getMessage()]
    assert len(lineas) == 2 and "repetido: no" in lineas[0] and "repetido: sí" in lineas[1]
    assert all("NTczMDAxMjM0NTY3"[-8:] in l for l in lineas)
    assert not any("573001234567" in l or "hola" in l for l in lineas)  # ni el teléfono ni el texto van al registro


# --- allowlist E.164 ---


def test_sin_lista_el_canal_queda_abierto(monkeypatch):
    from taaml.whatsapp import autorizado, numeros_autorizados

    monkeypatch.delenv("WHATSAPP_ALLOWLIST", raising=False)
    assert numeros_autorizados() == set() and autorizado("573001112233")


def test_con_lista_solo_pasan_los_autorizados(monkeypatch):
    from taaml.whatsapp import autorizado, numeros_autorizados

    monkeypatch.setenv("WHATSAPP_ALLOWLIST", "+57 300 111 2233, +573104445566;573007778899")
    esperados = {"573001112233", "573104445566", "573007778899"}
    assert numeros_autorizados() == esperados
    assert autorizado("573001112233")  # Meta manda el número sin «+»
    assert autorizado("+57 300 111 2233")
    assert not autorizado("573009999999")
    assert not autorizado("")


def test_el_asterisco_abre_el_canal_para_el_auditorio(monkeypatch):
    from taaml.whatsapp import autorizado, numeros_autorizados

    monkeypatch.setenv("WHATSAPP_ALLOWLIST", " * ")
    assert numeros_autorizados() == set()
    assert autorizado("573001112233") and autorizado("+1 555 555 5555")


def test_una_lista_sin_numeros_validos_cierra_el_canal_en_vez_de_abrirlo(monkeypatch):
    from taaml.whatsapp import autorizado

    monkeypatch.setenv("WHATSAPP_ALLOWLIST", " , ; ")
    assert not autorizado("573001112233")


def test_el_enlace_wa_me_normaliza_el_numero_y_codifica_el_saludo():
    from taaml.whatsapp import enlace_wa_me

    assert enlace_wa_me(" +57 300-111 2233 ") == "https://wa.me/573001112233?text=Hola"
    assert enlace_wa_me("+573001112233", "Hola, quiero saber") == (
        "https://wa.me/573001112233?text=Hola%2C%20quiero%20saber"
    )
    with pytest.raises(ValueError):
        enlace_wa_me("300")
