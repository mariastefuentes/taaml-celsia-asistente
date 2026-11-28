"""Aprobación desde el panel y aviso al cliente por el WhatsApp de OpenClaw: sin modelos, sin red y sin enviar nada."""

import subprocess

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

import api.main as api  # noqa: E402
from taaml import actividad, aprobaciones, avisos_openclaw  # noqa: E402

cliente = TestClient(api.app)
CABECERA = {"X-Aprobador": "secreto-largo"}
TELEFONO = "573001234567"
RECLAMO = {"herramienta": "radicar_reclamo", "args": {"ciudad": "Ibagué", "descripcion": "Sin luz"}}


@pytest.fixture
def agente_pausado(monkeypatch):
    """Un agente falso que queda pausado al «radicar» y se libera cuando una persona decide."""
    estado = {"pendiente": None, "decisiones": []}

    def conversar(mensaje, hilo, usuario):
        if "radica" in mensaje:
            estado["pendiente"] = RECLAMO
        return ("Quedó en revisión." if estado["pendiente"] else "Respuesta normal."), []

    def resolver(hilo, decision, usuario, mensaje=None):
        estado["pendiente"] = None
        estado["decisiones"].append(decision)
        return "Reclamo radicado: RC-1.", []

    monkeypatch.setenv("APROBADOR_TOKEN", "secreto-largo")
    monkeypatch.setattr(api, "conversar", conversar)
    monkeypatch.setattr(api, "pendiente_de_aprobacion", lambda hilo: estado["pendiente"])
    monkeypatch.setattr(api, "resolver_aprobacion", resolver)
    monkeypatch.setattr(api, "enviar_texto", lambda telefono, texto: False)  # Meta sin configurar
    return estado


def _escribir(mensaje):
    return cliente.post("/chat", json={"mensaje": mensaje, "telefono": TELEFONO}, headers={"X-Api-Key": "clave"}).json()["respuesta"]


def _pendientes():
    return cliente.get("/api/pendientes", headers=CABECERA).json()["pendientes"]


def _activar_openclaw(monkeypatch, entrega=True):
    enviados = []
    monkeypatch.setenv("OPENCLAW_AVISOS", "1")
    monkeypatch.setenv("CHAT_TOKEN", "clave")
    monkeypatch.setattr(avisos_openclaw, "enviar", lambda telefono, texto: enviados.append((telefono, texto)) or entrega)
    return enviados


def test_la_lista_de_pendientes_pide_el_token_y_no_trae_el_telefono(agente_pausado):
    _escribir("radica mi reclamo")
    _escribir("¿ya?")  # escribir otra vez no lo duplica
    assert cliente.get("/api/pendientes").status_code == 401
    r = cliente.get("/api/pendientes", headers=CABECERA)
    [p] = r.json()["pendientes"]
    assert p["herramienta"] == "radicar_reclamo" and p["args"]["ciudad"] == "Ibagué" and p["canal"] == "chat"
    assert TELEFONO not in r.text


def test_aprobar_desde_el_panel_le_escribe_al_cliente_por_openclaw(agente_pausado, monkeypatch):
    enviados = _activar_openclaw(monkeypatch)
    _escribir("radica mi reclamo")
    [p] = _pendientes()
    assert cliente.post(f"/api/pendientes/{p['codigo']}", json={"decision": "aprobar"}).status_code == 401
    r = cliente.post(f"/api/pendientes/{p['codigo']}", json={"decision": "aprobar"}, headers=CABECERA)
    assert r.status_code == 200 and r.json()["avisado_por_whatsapp"] is True
    assert enviados == [(TELEFONO, "Reclamo radicado: RC-1.")] and agente_pausado["decisiones"] == ["aprobar"]
    assert _pendientes() == []
    assert _escribir("¿Qué sedes hay?") == "Respuesta normal."  # ya la recibió: no se repite
    assert cliente.post(f"/api/pendientes/{p['codigo']}", json={"decision": "aprobar"}, headers=CABECERA).status_code == 404


@pytest.mark.parametrize("entrega", [None, False], ids=["avisos apagados", "el envío falla"])
def test_si_no_se_le_puede_escribir_la_respuesta_sale_con_su_siguiente_mensaje(agente_pausado, monkeypatch, entrega):
    if entrega is not None:
        _activar_openclaw(monkeypatch, entrega)
    _escribir("radica mi reclamo")
    [p] = _pendientes()
    r = cliente.post(f"/api/pendientes/{p['codigo']}", json={"decision": "rechazar"}, headers=CABECERA)
    assert r.json()["avisado_por_whatsapp"] is False
    assert _escribir("hola") == "Reclamo radicado: RC-1.\n\nRespuesta normal."  # el atajo espera: hay una decisión sin entregar
    assert _escribir("¿Qué sedes hay?") == "Respuesta normal."


def test_dos_decisiones_sin_entregar_llegan_las_dos():
    aprobaciones.guardar_sin_entregar("hilo", "Reclamo radicado: RC-1.")
    aprobaciones.guardar_sin_entregar("hilo", "Daño radicado: DA-2.")
    assert aprobaciones.tomar_sin_entregar("hilo") == "Reclamo radicado: RC-1.\n\nDaño radicado: DA-2."
    assert aprobaciones.tomar_sin_entregar("hilo") is None


def test_aprobar_por_telefono_tambien_usa_openclaw(agente_pausado, monkeypatch):
    enviados = _activar_openclaw(monkeypatch)
    _escribir("radica mi reclamo")
    r = cliente.post("/aprobar", json={"telefono": TELEFONO, "decision": "aprobar"}, headers=CABECERA)
    assert r.json()["avisado_por_whatsapp"] is True and len(enviados) == 1 and _pendientes() == []


def test_lo_que_entro_por_meta_se_avisa_por_meta(agente_pausado, monkeypatch):
    enviados = _activar_openclaw(monkeypatch)
    por_meta = []
    monkeypatch.setattr(api, "enviar_texto", lambda telefono, texto: por_meta.append(telefono) or True)
    agente_pausado["pendiente"] = RECLAMO
    api.responder_a_telefono(TELEFONO, "radica mi reclamo", canal="whatsapp")
    [p] = _pendientes()
    cliente.post(f"/api/pendientes/{p['codigo']}", json={"decision": "aprobar"}, headers=CABECERA)
    assert por_meta == [TELEFONO] and enviados == []


def test_dos_decisiones_a_la_vez_no_radican_dos_veces(agente_pausado):
    _escribir("radica mi reclamo")
    [p] = _pendientes()
    hilo, _ = api.ids_del_telefono(TELEFONO)
    assert aprobaciones.empezar_decision(hilo)  # otra petición la está aplicando
    assert cliente.post(f"/api/pendientes/{p['codigo']}", json={"decision": "aprobar"}, headers=CABECERA).status_code == 409
    assert agente_pausado["decisiones"] == []


def test_el_chat_web_tambien_se_aprueba_desde_el_panel(agente_pausado, monkeypatch):
    def en_vivo(mensaje, hilo, usuario):
        if "radica" in mensaje:
            agente_pausado["pendiente"] = RECLAMO
            yield {"tipo": "pendiente", **RECLAMO}
        yield {"tipo": "texto", "texto": "Quedó en revisión." if agente_pausado["pendiente"] else "Respuesta normal."}

    monkeypatch.setattr(api, "conversar_en_vivo", en_vivo)
    hilo = "0123456789ab4def8123456789abcdef"
    cliente.post("/api/chat", json={"mensaje": "radica mi reclamo", "hilo": hilo})
    [p] = _pendientes()
    assert p["canal"] == "web"
    assert cliente.post(f"/api/pendientes/{p['codigo']}", json={"decision": "aprobar"}, headers=CABECERA).status_code == 200
    assert "Reclamo radicado: RC-1." in cliente.post("/api/chat", json={"mensaje": "¿ya?", "hilo": hilo}).text


HILO_WEB = "fedcba9876544210bedcba9876543210"


def _pausar_en_la_web(monkeypatch, agente_pausado):
    def en_vivo(mensaje, hilo, usuario):
        if "radica" in mensaje:
            agente_pausado["pendiente"] = RECLAMO
            yield {"tipo": "herramienta", "herramienta": "radicar_reclamo", "args": RECLAMO["args"]}
            yield {"tipo": "pendiente", **RECLAMO}
        yield {"tipo": "texto", "texto": "Quedó en revisión." if agente_pausado["pendiente"] else "Respuesta normal."}

    monkeypatch.setattr(api, "conversar_en_vivo", en_vivo)
    monkeypatch.setattr(api, "historial_visible", lambda hilo: [{"rol": "assistant", "texto": "Reclamo radicado: RC-1."}])
    cliente.post("/api/chat", json={"mensaje": "radica mi reclamo", "hilo": HILO_WEB})


def test_el_chat_web_recoge_la_decision_sin_escribir_y_no_se_repite(agente_pausado, monkeypatch):
    _pausar_en_la_web(monkeypatch, agente_pausado)
    [p] = _pendientes()
    cliente.post(f"/api/pendientes/{p['codigo']}", json={"decision": "aprobar"}, headers=CABECERA)
    assert cliente.get(f"/api/hilos/{HILO_WEB}/estado").json() == {"pendiente": None}
    assert "RC-1" in cliente.get(f"/api/hilos/{HILO_WEB}/mensajes").text  # el navegador la trae del historial
    respuesta = cliente.post("/api/chat", json={"mensaje": "¿ya?", "hilo": HILO_WEB}).text
    assert "Respuesta normal." in respuesta and "RC-1" not in respuesta


def test_mientras_se_aplica_la_decision_el_chat_web_sigue_en_revision(agente_pausado, monkeypatch):
    _pausar_en_la_web(monkeypatch, agente_pausado)
    vistos = []

    def resolver(hilo, decision, usuario, mensaje=None):
        agente_pausado["pendiente"] = None  # el agente ya no está pausado, pero todavía no hay respuesta que entregar
        vistos.append(cliente.get(f"/api/hilos/{hilo}/estado").json())
        return "Reclamo radicado: RC-1.", []

    monkeypatch.setattr(api, "resolver_aprobacion", resolver)
    [p] = _pendientes()
    cliente.post(f"/api/pendientes/{p['codigo']}", json={"decision": "aprobar"}, headers=CABECERA)
    assert vistos == [{"pendiente": {"herramienta": "radicar_reclamo"}}]


def test_abrir_el_historial_no_se_lleva_lo_que_espera_a_un_cliente_de_whatsapp(agente_pausado, monkeypatch):
    monkeypatch.setattr(api, "historial_visible", lambda hilo: [])
    _escribir("radica mi reclamo")
    [p] = _pendientes()
    cliente.post(f"/api/pendientes/{p['codigo']}", json={"decision": "aprobar"}, headers=CABECERA)
    hilo, _ = api.ids_del_telefono(TELEFONO)
    assert cliente.get(f"/api/hilos/{hilo}/mensajes").status_code == 422  # el id de un teléfono no entra por la web
    assert _escribir("hola") == "Reclamo radicado: RC-1.\n\nRespuesta normal."


def test_los_turnos_del_chat_web_salen_en_el_panel(agente_pausado, monkeypatch):
    actividad.vaciar()
    _pausar_en_la_web(monkeypatch, agente_pausado)
    [fila] = cliente.get("/api/actividad", headers=CABECERA).json()["filas"]
    assert fila["canal"] == "web" and fila["estado"] == "pendiente de aprobación"
    assert fila["mensaje"] == "radica mi reclamo" and fila["herramientas"] == ["radicar_reclamo"]
    assert fila["quien"] == _pendientes()[0]["quien"] and HILO_WEB not in str(fila)


def test_un_fallo_en_el_chat_web_tambien_queda_en_el_panel(agente_pausado, monkeypatch):
    def roto(mensaje, hilo, usuario):
        raise RuntimeError("clave secreta")
        yield

    actividad.vaciar()
    monkeypatch.setattr(api, "conversar_en_vivo", roto)
    cliente.post("/api/chat", json={"mensaje": "¿Qué sedes hay?", "hilo": HILO_WEB})
    [fila] = cliente.get("/api/actividad", headers=CABECERA).json()["filas"]
    assert fila["estado"] == "error" and "clave secreta" not in str(fila)


def test_los_avisos_exigen_activarlos_y_tener_clave_de_chat(monkeypatch):
    assert avisos_openclaw.activos() is False
    monkeypatch.setenv("OPENCLAW_AVISOS", "1")
    assert avisos_openclaw.activos() is False  # sin CHAT_TOKEN /chat está abierto: no se escribe a nadie
    monkeypatch.setenv("CHAT_TOKEN", "clave")
    assert avisos_openclaw.activos() is True
    assert cliente.get("/api/salud").json()["avisos_openclaw"] is True


def test_el_envio_pasa_el_texto_como_un_solo_argumento_y_nunca_lanza(monkeypatch):
    monkeypatch.setattr(avisos_openclaw, "comando", lambda: ["node", "openclaw.mjs"])
    llamadas = []

    def correr(orden, **opciones):
        llamadas.append((orden, opciones))
        return subprocess.CompletedProcess(orden, 0)

    monkeypatch.setattr(avisos_openclaw.subprocess, "run", correr)
    texto = '--help & echo "hola" | más'
    assert avisos_openclaw.enviar("57 300 123 4567", texto) is True
    [(orden, opciones)] = llamadas
    assert f"--message={texto}" in orden and "--target=+573001234567" in orden and "--dry-run" not in orden
    assert not opciones.get("shell")

    monkeypatch.setattr(avisos_openclaw.subprocess, "run", lambda orden, **o: subprocess.CompletedProcess(orden, 1))
    assert avisos_openclaw.enviar(TELEFONO, "hola") is False

    def tarda(orden, **opciones):
        raise subprocess.TimeoutExpired(orden, 60)

    monkeypatch.setattr(avisos_openclaw.subprocess, "run", tarda)
    assert avisos_openclaw.enviar(TELEFONO, "hola") is False
    monkeypatch.setattr(avisos_openclaw, "comando", lambda: None)
    assert avisos_openclaw.enviar(TELEFONO, "hola") is False
