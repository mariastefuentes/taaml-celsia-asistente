"""Panel `/panel` y `/api/actividad`: mensajes de chat web **y** WhatsApp, sin duplicar, persistentes, autenticados.

Todo con mensajes simulados; no se envÃ­a nada por WhatsApp real ni se consume cuota del modelo. La actividad persiste en
SQLite (`ACTIVIDAD_DB`, temporal en las pruebas) y sobrevive a reiniciar la app; no se borra ninguna conversaciÃ³n.
"""

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from api.main import app
from taaml import actividad, aprobaciones

cliente = TestClient(app)
CABECERA = {"X-Aprobador": "secreto-largo"}
CLIENTE = "573001234567"           # telÃ©fono simulado: nunca debe aparecer completo
CLIENTE2 = "573009998877"
TELEFONO_OCULTO = "573001234567"   # sin '+': tampoco debe salir


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setenv("APROBADOR_TOKEN", "secreto-largo")
    monkeypatch.setattr(api_main, "conversar", lambda mensaje, hilo, usuario: ("Respuesta del agente", []))
    monkeypatch.setattr(api_main, "pendiente_de_aprobacion", lambda hilo: None)
    monkeypatch.setattr(api_main, "calentar", lambda: None)
    # WhatsApp simulado: no se manda nada a Meta real.
    monkeypatch.setattr(api_main, "enviar_texto", lambda telefono, texto: True)
    monkeypatch.setattr(api_main, "enviar_botones", lambda telefono, texto, botones: True)
    monkeypatch.setattr(api_main, "marcar_leido", lambda id_mensaje: True)
    monkeypatch.setenv("WHATSAPP_ALLOWLIST", "*")
    monkeypatch.delenv("WHATSAPP_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_PHONE_NUMBER_ID", raising=False)
    monkeypatch.setenv("LIMITE_MENSAJES", "0")
    monkeypatch.setattr(api_main, "LIMITE", api_main.limite_desde_entorno())
    aprobaciones.vaciar()


def _actividad(cabecera=CABECERA, **kw):
    return cliente.get("/api/actividad", headers=cabecera, params=kw).json()["filas"]


def _hilo_web() -> str:
    return uuid4().hex


# --- mensaje entrante de WhatsApp -------------------------------------------------
def test_mensaje_entrante_de_whatsapp_queda_registrado():
    r = cliente.post("/chat", json={"mensaje": "Â¿CuÃ¡les son sus sedes?", "telefono": CLIENTE, "canal": "whatsapp"})
    assert r.status_code == 200
    filas = _actividad()
    assert len(filas) == 1
    fila = filas[0]
    assert fila["canal"] == "whatsapp"
    assert fila["mensaje"] == "Â¿CuÃ¡les son sus sedes?"
    assert fila["quien"] == actividad.quien(CLIENTE)
    assert fila["conversacion"] == f"whatsapp:{fila['fecha']}:{fila['quien']}"
    # No se expone el nÃºmero completo ni credenciales.
    assert CLIENTE not in json.dumps(fila) and TELEFONO_OCULTO not in json.dumps(fila)
    assert CLIENTE not in str(fila["conversacion"])


def test_mensaje_entrante_por_webhook_whatsapp_queda_registrado(monkeypatch):
    import hashlib
    import hmac

    secreto = "secreto-meta"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secreto)
    monkeypatch.setattr(api_main, "conversar", lambda mensaje, hilo, usuario: ("ok", []))
    carga = {
        "entry": [{"changes": [{"value": {"messages": [
            {"id": "wamid.1", "from": CLIENTE, "type": "text", "text": {"body": "Hola por WhatsApp"}},
        ]}}]}],
    }
    cuerpo = json.dumps(carga).encode()
    firma = "sha256=" + hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()
    r = cliente.post("/webhook/whatsapp", content=cuerpo, headers={"X-Hub-Signature-256": firma, "Content-Type": "application/json"})
    assert r.status_code == 200 and r.json()["mensajes"] == 1
    filas = _actividad()
    assert any(f["canal"].startswith("whatsapp") and f["mensaje"] == "Hola por WhatsApp" for f in filas)
    assert CLIENTE not in json.dumps(filas)


# --- respuesta saliente de WhatsApp ----------------------------------------------

def test_respuesta_saliente_de_whatsapp_queda_registrada(monkeypatch):
    monkeypatch.setattr(api_main, "respuesta_rapida", lambda mensaje: None)
    monkeypatch.setattr(api_main, "conversar", lambda mensaje, hilo, usuario: ("Respuesta del agente", []))
    cliente.post("/chat", json={
        "mensaje": "hola",
        "telefono": CLIENTE,
        "canal": "whatsapp",
    })
    [fila] = _actividad()
    assert fila["mensaje"] == "hola"
    assert fila["respuesta"] == "Respuesta del agente"
    assert fila["canal"] == "whatsapp"
    assert fila["estado"] == "respondido"
def test_respuesta_saliente_por_webhook_whatsapp_se_envia_y_registra(monkeypatch):
    import hashlib
    import hmac

    enviados = []
    monkeypatch.setattr(api_main, "enviar_texto", lambda telefono, texto: enviados.append(texto) or True)
    secreto = "secreto-meta"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secreto)
    carga = {"entry": [{"changes": [{"value": {"messages": [
        {"id": "wamid.2", "from": CLIENTE, "type": "text", "text": {"body": "Â¿hay energÃ­a?"}},
    ]}}]}]}
    cuerpo = json.dumps(carga).encode()
    firma = "sha256=" + hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()
    cliente.post("/webhook/whatsapp", content=cuerpo, headers={"X-Hub-Signature-256": firma, "Content-Type": "application/json"})
    assert enviados and enviados[-1] == "Respuesta del agente"
    [fila] = [f for f in _actividad() if f["mensaje"] == "Â¿hay energÃ­a?"]
    assert fila["respuesta"] == "Respuesta del agente" and fila["canal"].startswith("whatsapp")


# --- mensaje enviado desde el chat web -------------------------------------------
def _evento_sse(lineas, tipo):
    return "".join(lineas)


def test_mensaje_del_chat_web_queda_registrado(monkeypatch):
    def falso(mensaje, hilo, usuario):
        yield {"tipo": "texto", "texto": "Hola web"}
        yield {"tipo": "fin", "costo_usd": 0.0}

    monkeypatch.setattr(api_main, "conversar_en_vivo", falso)
    hilo = _hilo_web()
    r = cliente.post("/api/chat", json={"mensaje": "pregunta web", "hilo": hilo})
    assert r.status_code == 200
    filas = _actividad()
    assert len(filas) == 1
    fila = filas[0]
    assert fila["canal"] == "web" and fila["mensaje"] == "pregunta web" and fila["respuesta"] == "Hola web"
    assert fila["conversacion"] == f"web:{fila['fecha']}:{fila['quien']}"
    assert hilo not in json.dumps(fila)


# --- consulta conjunta de ambos canales ------------------------------------------
def test_consulta_conjunta_de_ambos_canales(monkeypatch):
    cliente.post("/chat", json={"mensaje": "vÃ­a whatsapp", "telefono": CLIENTE, "canal": "whatsapp"})

    def falso(mensaje, hilo, usuario):
        yield {"tipo": "texto", "texto": "vÃ­a web"}

    monkeypatch.setattr(api_main, "conversar_en_vivo", falso)
    cliente.post("/api/chat", json={"mensaje": "vÃ­a web", "hilo": _hilo_web()})

    filas = _actividad()
    canales = {f["canal"] for f in filas}
    assert "whatsapp" in canales and "web" in canales
    assert {f["mensaje"] for f in filas} >= {"vÃ­a whatsapp", "vÃ­a web"}
    # orden cronolÃ³gico por n creciente
    assert [f["n"] for f in filas] == sorted(f["n"] for f in filas)


def test_chat_sin_canal_explicito_cuenta_como_web_no_whatsapp():
    cliente.post("/chat", json={"mensaje": "hola", "telefono": CLIENTE})  # canal por defecto 'chat' -> Web
    [fila] = _actividad()
    assert fila["canal"] == "chat"  # no es WhatsApp; el panel lo muestra como Web


# --- separaciÃ³n de conversaciones ------------------------------------------------
def test_separacion_de_conversaciones_por_canal_dia_y_usuario():
    cliente.post("/chat", json={"mensaje": "uno", "telefono": CLIENTE, "canal": "whatsapp"})
    cliente.post("/chat", json={"mensaje": "dos", "telefono": CLIENTE2, "canal": "whatsapp"})
    cliente.post("/chat", json={"mensaje": "tres", "telefono": CLIENTE, "canal": "chat"})
    filas = _actividad()
    convs = [f["conversacion"] for f in filas]
    assert len(set(convs)) == 3  # mismo telÃ©fono, otro canal = otra conversaciÃ³n; otro telÃ©fono = otra
    assert convs[0].split(":")[1] == convs[2].split(":")[1] == filas[0]["fecha"]  # mismo dÃ­a
    # la conversaciÃ³n de WhatsApp de un usuario no se mezcla con la del otro ni con la web
    mismo_usuario = {f["quien"] for f in filas if f["mensaje"] in ("uno", "tres")}
    assert len(mismo_usuario) == 1
    assert {f["conversacion"] for f in filas if f["mensaje"] in ("uno", "tres")} != {filas[1]["conversacion"]}
    assert CLIENTE not in json.dumps(filas) and CLIENTE2 not in json.dumps(filas)


# --- persistencia despuÃ©s de reiniciar la aplicaciÃ³n -----------------------------
def test_persistencia_despues_de_reiniciar_fastapi(tmp_path, monkeypatch):
    db = tmp_path / "actividad.sqlite"
    monkeypatch.setenv("ACTIVIDAD_DB", str(db))
    actividad.vaciar()
    monkeypatch.setattr(api_main, "calentar", lambda: None)
    with TestClient(app) as c1:
        c1.post("/chat", json={"mensaje": "recuerda esto", "telefono": CLIENTE, "canal": "whatsapp"})
    assert db.exists()
    antes = len(actividad.recientes())
    assert antes >= 1
    # "Reiniciar" la app: nueva app + memoria vacÃ­a, misma base; nada se borra.
    actividad._FILAS.clear()
    actividad._USADAS.clear()
    actividad._SIGUIENTE = 1
    with TestClient(app) as c2:
        filas = c2.get("/api/actividad", headers=CABECERA).json()["filas"]
    assert any(f["mensaje"] == "recuerda esto" and f["canal"] == "whatsapp" for f in filas)
    assert CLIENTE not in json.dumps(filas)
    assert len(filas) == antes  # sigue todo, sin duplicar


def test_actividad_cargar_restaura_orden_y_numeracion(tmp_path, monkeypatch):
    db = tmp_path / "a.sqlite"
    monkeypatch.setenv("ACTIVIDAD_DB", str(db))
    actividad.vaciar()
    actividad.registrar("whatsapp", CLIENTE, "a", "respondido", respuesta="ra")
    actividad.registrar("web", "hilo", "b", "respondido", respuesta="rb")
    actividad._FILAS.clear()
    actividad._USADAS.clear()
    actividad._SIGUIENTE = 1
    actividad.cargar()
    filas = actividad.recientes()
    assert [f["n"] for f in filas] == [1, 2] and [f["mensaje"] for f in filas] == ["a", "b"]
    nuevo = actividad.registrar("whatsapp", CLIENTE, "c", "respondido")
    assert nuevo["n"] == 3


# --- acceso autorizado y no autorizado -------------------------------------------
def test_actividad_requiere_aprobador():
    assert cliente.get("/api/actividad").status_code == 401
    assert cliente.get("/api/actividad", headers={"X-Aprobador": "otro"}).status_code == 401
    assert cliente.get("/api/actividad", headers=CABECERA).status_code == 200


def test_actividad_sin_aprobador_token_deshabilitado(monkeypatch):
    monkeypatch.delenv("APROBADOR_TOKEN", raising=False)
    assert cliente.get("/api/actividad", headers=CABECERA).status_code == 503


def test_panel_requiere_token_en_pantalla_pero_pagina_no_lleva_datos():
    r = cliente.get("/panel")
    assert r.status_code == 200 and "secreto-largo" not in r.text  # la pÃ¡gina no incluye secretos
    assert "Panel en vivo" in r.text and CLIENTE not in r.text
    assert "/api/actividad" in r.text and "X-Aprobador" in r.text
    # sin token no se entregan datos privados
    assert cliente.get("/api/actividad").status_code == 401
    assert cliente.get("/api/pendientes").status_code == 401


def test_pendientes_requiere_aprobador_y_no_trae_telefono():
    assert cliente.get("/api/pendientes").status_code == 401
    assert cliente.get("/api/pendientes", headers={"X-Aprobador": "otro"}).status_code == 401
    r = cliente.get("/api/pendientes", headers=CABECERA)
    assert r.status_code == 200
    assert CLIENTE not in r.text and TELEFONO_OCULTO not in r.text
    for p in r.json()["pendientes"]:
        assert "telefono" not in p and "hilo" not in p


# --- ausencia de mensajes duplicados ---------------------------------------------
def test_sin_mensajes_duplicados():
    cliente.post("/chat", json={"mensaje": "una sola vez", "telefono": CLIENTE, "canal": "whatsapp"})
    filas = _actividad()
    assert len(filas) == 1
    assert len({f["n"] for f in filas}) == len(filas)
    # consultar dos veces no duplica
    assert len(_actividad()) == 1
    # `desde` no re-emite lo ya visto
    assert _actividad(desde=filas[-1]["n"]) == []


def test_webhook_mensaje_repetido_no_duplica(monkeypatch):
    import hashlib
    import hmac

    secreto = "secreto-meta"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secreto)
    monkeypatch.setattr(api_main, "conversar", lambda mensaje, hilo, usuario: ("ok", []))
    api_main._AVISOS_VISTOS.clear()
    carga = {"entry": [{"changes": [{"value": {"messages": [
        {"id": "wamid.dup", "from": CLIENTE, "type": "text", "text": {"body": "hola"}},
    ]}}]}]}
    cuerpo = json.dumps(carga).encode()
    firma = "sha256=" + hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": firma, "Content-Type": "application/json"}
    cliente.post("/webhook/whatsapp", content=cuerpo, headers=headers)
    n1 = len([f for f in _actividad() if f["mensaje"] == "hola"])
    cliente.post("/webhook/whatsapp", content=cuerpo, headers=headers)  # reintento de Meta
    n2 = len([f for f in _actividad() if f["mensaje"] == "hola"])
    assert n1 == n2 == 1


def test_inbound_y_outbound_en_una_sola_fila_sin_duplicar(monkeypatch):
    cliente.post("/chat", json={"mensaje": "entrada", "telefono": CLIENTE, "canal": "whatsapp"})
    filas = _actividad()
    assert len(filas) == 1 and filas[0]["mensaje"] == "entrada" and filas[0]["respuesta"] == "Respuesta del agente"




