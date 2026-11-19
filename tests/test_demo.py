"""Panel en vivo, aprobación con botones de WhatsApp y notas de voz (tentativo)."""

import json

import pytest
import requests
from fastapi.testclient import TestClient

import api.main as api_main
from api.main import RespuestaDelAgente, app
from taaml import actividad, voz, whatsapp

cliente = TestClient(app)
CLIENTE = "573001234567"
APROBADOR = "573009998877"


@pytest.fixture(autouse=True)
def limpio(monkeypatch):
    actividad.vaciar()
    api_main._AVISOS_VISTOS.clear()
    monkeypatch.setenv("LIMITE_MENSAJES", "0")
    monkeypatch.setattr(api_main, "LIMITE", api_main.limite_desde_entorno())
    monkeypatch.delenv("APROBADOR_WHATSAPP", raising=False)
    monkeypatch.delenv("VOZ_ACTIVA", raising=False)
    monkeypatch.setenv("WHATSAPP_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123")


def _agente_falso(respuesta="ok", herramientas=None, pendiente=None):
    return lambda t, m, canal="chat": RespuestaDelAgente(respuesta=respuesta, herramientas=herramientas or [], pendiente=pendiente)


# --- panel en vivo ---
def test_la_actividad_guarda_lo_necesario_y_nunca_el_numero():
    fila = actividad.registrar("whatsapp", CLIENTE, "¿Qué sedes hay en Ibagué?", "respondido", ["consultar_datos"], 3.456)
    assert fila["herramientas"] == ["consultar_datos"] and fila["segundos"] == 3.5 and fila["canal"] == "whatsapp"
    assert CLIENTE not in json.dumps(actividad.recientes()) and fila["quien"] == actividad.quien("+57 300 123 4567")
    assert actividad.recientes(desde=fila["n"]) == []  # solo lo nuevo


def test_la_actividad_tiene_tope_y_recorta_el_mensaje():
    for _ in range(actividad.MAXIMO + 5):
        actividad.registrar("chat", CLIENTE, "x" * 500, "respondido")
    filas = actividad.recientes()
    assert len(filas) == actividad.MAXIMO and filas[0]["n"] == 6 and len(filas[0]["mensaje"]) == actividad.MAX_TEXTO


def test_el_panel_pide_token_y_muestra_los_turnos(monkeypatch):
    monkeypatch.delenv("APROBADOR_TOKEN", raising=False)
    assert cliente.get("/api/actividad").status_code == 503  # sin token configurado queda cerrado
    monkeypatch.setenv("APROBADOR_TOKEN", "secreto-largo")
    assert cliente.get("/api/actividad").status_code == 401
    assert cliente.get("/api/actividad", headers={"X-Aprobador": "otro"}).status_code == 401
    monkeypatch.setattr(api_main, "conversar", lambda m, h, usuario: ("Hola", [{"herramienta": "buscar_en_base"}]))
    monkeypatch.setattr(api_main, "pendiente_de_aprobacion", lambda hilo: None)
    assert cliente.post("/chat", json={"mensaje": "¿Qué es Celsia Solar?", "telefono": CLIENTE}).status_code == 200
    r = cliente.get("/api/actividad", headers={"X-Aprobador": "secreto-largo"}).json()
    assert r["filas"][0]["herramientas"] == ["buscar_en_base"] and r["filas"][0]["estado"] == "respondido"
    assert CLIENTE not in json.dumps(r) and r["ultimo"] == 1
    assert cliente.get("/api/actividad?desde=1", headers={"X-Aprobador": "secreto-largo"}).json()["filas"] == []


def test_el_limite_y_los_fallos_tambien_quedan_en_el_panel(monkeypatch):
    monkeypatch.setenv("LIMITE_MENSAJES", "1")
    monkeypatch.setattr(api_main, "LIMITE", api_main.limite_desde_entorno())

    def falla(m, h, usuario):
        raise RuntimeError("falla")

    monkeypatch.setattr(api_main, "conversar", falla)
    cliente.post("/chat", json={"mensaje": "uno", "telefono": CLIENTE})
    assert cliente.post("/chat", json={"mensaje": "dos", "telefono": CLIENTE}).status_code == 429
    assert [f["estado"] for f in actividad.recientes()] == ["error", "límite"]


def test_la_pagina_del_panel_se_sirve_sin_datos():
    r = cliente.get("/panel")
    assert r.status_code == 200 and "Panel en vivo" in r.text and "/api/actividad" in r.text and CLIENTE not in r.text


# --- botones de aprobación ---
def test_mensajes_entrantes_lee_botones_y_audios():
    boton = {"id": "w1", "from": APROBADOR, "type": "interactive", "interactive": {"button_reply": {"id": f"aprobar:{CLIENTE}", "title": "Aprobar"}}}
    nota = {"id": "w2", "from": CLIENTE, "type": "audio", "audio": {"id": "media-9", "mime_type": "audio/ogg"}}
    carga = {"entry": [{"changes": [{"value": {"messages": [boton, nota]}}]}]}
    boton_leido, nota_leida = whatsapp.mensajes_entrantes(carga)
    assert boton_leido["tipo"] == "interactive" and boton_leido["texto"] == f"aprobar:{CLIENTE}"
    assert nota_leida["tipo"] == "audio" and nota_leida["audio"] == "media-9" and nota_leida["texto"] == ""


def test_enviar_botones_arma_la_peticion_y_respeta_los_limites_de_meta(monkeypatch):
    enviados = []
    monkeypatch.setattr(requests, "post", lambda url, json, headers, timeout: enviados.append(json) or type("R", (), {"ok": True})())
    assert whatsapp.enviar_botones(APROBADOR, "¿Apruebas?", [("a", "Aprobar"), ("r", "Rechazar con un rótulo larguísimo")])
    cuerpo = enviados[0]
    assert cuerpo["type"] == "interactive" and cuerpo["interactive"]["type"] == "button"
    botones = cuerpo["interactive"]["action"]["buttons"]
    assert [b["reply"]["id"] for b in botones] == ["a", "r"] and all(len(b["reply"]["title"]) <= 20 for b in botones)
    assert not whatsapp.enviar_botones(APROBADOR, "x", [])  # Meta acepta de 1 a 3 botones
    assert not whatsapp.enviar_botones(APROBADOR, "x", [("1", "a"), ("2", "b"), ("3", "c"), ("4", "d")])


def test_un_reclamo_pendiente_le_llega_al_aprobador_con_dos_botones(monkeypatch):
    monkeypatch.setenv("APROBADOR_WHATSAPP", APROBADOR)
    botones = []
    pendiente = {"herramienta": "radicar_reclamo", "args": {"ciudad": "Cali"}}
    monkeypatch.setattr(api_main, "responder_a_telefono", _agente_falso("En revisión", ["radicar_reclamo"], pendiente))
    monkeypatch.setattr(api_main, "enviar_texto", lambda *a: True)
    monkeypatch.setattr(api_main, "enviar_botones", lambda tel, texto, b: botones.append((tel, texto, b)) or True)
    api_main.atender_mensaje_de_whatsapp(CLIENTE, "text", "Quiero poner un reclamo")
    destino, texto, lista = botones[0]
    assert destino == APROBADOR and "ciudad: Cali" in texto and CLIENTE not in texto  # el cliente se ve como un identificador corto
    assert lista == [(f"aprobar:{CLIENTE}", "Aprobar"), (f"rechazar:{CLIENTE}", "Rechazar")]


def test_sin_aprobador_configurado_no_se_mandan_botones(monkeypatch):
    monkeypatch.setattr(api_main, "responder_a_telefono", _agente_falso("En revisión", [], {"herramienta": "radicar_reclamo", "args": {}}))
    monkeypatch.setattr(api_main, "enviar_texto", lambda *a: True)
    monkeypatch.setattr(api_main, "enviar_botones", lambda *a: pytest.fail("no debía mandar botones"))
    api_main.atender_mensaje_de_whatsapp(CLIENTE, "text", "reclamo")


def test_tocar_aprobar_decide_y_avisa_al_cliente_y_al_aprobador(monkeypatch):
    monkeypatch.setenv("APROBADOR_WHATSAPP", APROBADOR)
    enviados, decisiones = [], []
    monkeypatch.setattr(api_main, "pendiente_de_aprobacion", lambda hilo: {"herramienta": "radicar_reclamo"})
    monkeypatch.setattr(api_main, "resolver_aprobacion", lambda hilo, decision, usuario, mensaje=None: decisiones.append(decision) or ("Radicado REC-1", []))
    monkeypatch.setattr(api_main, "enviar_texto", lambda tel, texto: enviados.append((tel, texto)) or True)
    api_main.atender_mensaje_de_whatsapp(APROBADOR, "interactive", f"aprobar:{CLIENTE}")
    assert decisiones == ["aprobar"]
    assert enviados[0] == (CLIENTE, "Radicado REC-1") and enviados[1][0] == APROBADOR and "Hecho: aprobar" in enviados[1][1]
    assert actividad.recientes()[-1]["estado"] == "aprobación"


def test_tocar_rechazar_rechaza(monkeypatch):
    monkeypatch.setenv("APROBADOR_WHATSAPP", APROBADOR)
    decisiones = []
    monkeypatch.setattr(api_main, "pendiente_de_aprobacion", lambda hilo: {"herramienta": "radicar_reclamo"})
    monkeypatch.setattr(api_main, "resolver_aprobacion", lambda hilo, decision, usuario, mensaje=None: decisiones.append(decision) or ("No se radicó", []))
    monkeypatch.setattr(api_main, "enviar_texto", lambda *a: True)
    api_main.atender_mensaje_de_whatsapp(APROBADOR, "interactive", f"rechazar:{CLIENTE}")
    assert decisiones == ["rechazar"]


def test_los_botones_de_otra_persona_no_deciden_nada(monkeypatch):
    monkeypatch.setenv("APROBADOR_WHATSAPP", APROBADOR)
    monkeypatch.setattr(api_main, "resolver_aprobacion", lambda *a, **k: pytest.fail("nadie más puede aprobar"))
    monkeypatch.setattr(api_main, "pendiente_de_aprobacion", lambda hilo: {"herramienta": "radicar_reclamo"})
    enviados = []
    monkeypatch.setattr(api_main, "enviar_texto", lambda tel, texto: enviados.append(texto) or True)
    api_main.atender_mensaje_de_whatsapp("573001112233", "interactive", f"aprobar:{CLIENTE}")  # no es el aprobador: mensaje no soportado
    assert enviados == [whatsapp.TEXTO_NO_SOPORTADO]
    monkeypatch.delenv("APROBADOR_WHATSAPP")
    api_main.atender_mensaje_de_whatsapp(APROBADOR, "interactive", f"aprobar:{CLIENTE}")  # sin aprobador configurado tampoco
    assert enviados == [whatsapp.TEXTO_NO_SOPORTADO] * 2


def test_un_boton_repetido_o_ajeno_se_responde_con_amabilidad(monkeypatch):
    monkeypatch.setenv("APROBADOR_WHATSAPP", APROBADOR)
    monkeypatch.setattr(api_main, "pendiente_de_aprobacion", lambda hilo: None)
    enviados = []
    monkeypatch.setattr(api_main, "enviar_texto", lambda tel, texto: enviados.append((tel, texto)) or True)
    api_main.atender_mensaje_de_whatsapp(APROBADOR, "interactive", f"aprobar:{CLIENTE}")
    api_main.atender_mensaje_de_whatsapp(APROBADOR, "interactive", "cualquier-otra-cosa")  # un identificador que no es nuestro no decide nada
    assert enviados == [(APROBADOR, "Ese reclamo ya no está pendiente."), (APROBADOR, whatsapp.TEXTO_NO_SOPORTADO)]


# --- notas de voz (tentativo) ---
def test_la_voz_esta_apagada_por_defecto():
    assert not voz.activa() and voz.transcribir(b"audio") is None


def test_una_nota_de_voz_se_transcribe_y_llega_al_agente_como_texto(monkeypatch):
    monkeypatch.setenv("VOZ_ACTIVA", "1")
    preguntas = []
    monkeypatch.setattr(api_main, "descargar_audio", lambda id_audio: (b"datos", "audio/ogg"))
    monkeypatch.setattr(api_main.voz, "transcribir", lambda audio, mime: "¿Qué sedes hay en Ibagué?")
    monkeypatch.setattr(api_main, "responder_a_telefono", lambda t, m, canal="chat": preguntas.append((m, canal)) or RespuestaDelAgente(respuesta="ok", herramientas=[]))
    monkeypatch.setattr(api_main, "enviar_texto", lambda *a: True)
    api_main.atender_mensaje_de_whatsapp(CLIENTE, "audio", "", audio="media-1")
    assert preguntas == [("¿Qué sedes hay en Ibagué?", "whatsapp (voz)")]


def test_si_la_voz_falla_el_cliente_recibe_el_aviso_de_solo_texto(monkeypatch):
    monkeypatch.setenv("VOZ_ACTIVA", "1")
    enviados = []
    monkeypatch.setattr(api_main, "descargar_audio", lambda id_audio: None)
    monkeypatch.setattr(api_main, "responder_a_telefono", lambda *a, **k: pytest.fail("sin texto no hay turno"))
    monkeypatch.setattr(api_main, "enviar_texto", lambda tel, texto: enviados.append(texto) or True)
    api_main.atender_mensaje_de_whatsapp(CLIENTE, "audio", "", audio="media-1")
    assert enviados == [whatsapp.TEXTO_NO_SOPORTADO] and actividad.recientes()[-1]["estado"] == "no soportado"


def test_transcribir_rechaza_audios_enormes_y_tolera_que_falte_la_biblioteca(monkeypatch):
    monkeypatch.setenv("VOZ_ACTIVA", "1")
    assert voz.transcribir(b"x" * (voz.MAX_BYTES + 1)) is None

    def sin_biblioteca():
        raise ImportError("falta faster_whisper")

    monkeypatch.setattr(voz, "_modelo", sin_biblioteca)
    assert voz.transcribir(b"audio") is None
