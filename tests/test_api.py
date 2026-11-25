import json
import threading
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app
from taaml.agente import MODELO_AGENTE

cliente = TestClient(app)
HILO = "a" * 32


def _eventos(texto: str) -> list[tuple[str, dict]]:
    salida = []
    for bloque in texto.strip().split("\n\n"):
        tipo, datos = bloque.split("\n")
        salida.append((tipo.removeprefix("event: "), json.loads(datos.removeprefix("data: "))))
    return salida


def test_salud_dice_el_modelo():
    r = cliente.get("/api/salud")
    assert r.status_code == 200 and r.json()["estado"] == "ok" and r.json()["modelo"] == MODELO_AGENTE
    assert r.json()["almacen"] in {"qdrant", "numpy", "ninguno"}


def test_salud_dice_que_memoria_usa_la_api(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert cliente.get("/api/salud").json()["memoria"] == "sqlite"
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/x")
    assert cliente.get("/api/salud").json()["memoria"] == "postgresql"
    monkeypatch.setenv("DATABASE_URL", "")  # lo que hace `make api-sqlite`: vacía, no cuenta
    assert cliente.get("/api/salud").json()["memoria"] == "sqlite"


def test_el_qr_de_whatsapp_se_sirve_para_el_chat_y_el_panel():
    r = cliente.get("/qr-whatsapp.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert "/qr-whatsapp.png" in cliente.get("/panel").text


def test_si_falta_el_qr_lo_dice(monkeypatch):
    monkeypatch.setattr("api.main.QR_WHATSAPP", Path("no-existe.png"))
    r = cliente.get("/qr-whatsapp.png")
    assert r.status_code == 404 and "make qr-whatsapp" in r.json()["detail"]


def test_chat_transmite_los_eventos_del_agente(monkeypatch):
    def falso(mensaje, hilo, usuario):
        yield {"tipo": "herramienta", "herramienta": "consultar_datos", "args": {"tabla": "sedes"}}
        yield {"tipo": "texto", "texto": "Hola"}
        yield {"tipo": "fin", "usadas": "Usó: x", "tokens_entrada": 1, "tokens_salida": 2, "costo_usd": 0.1}

    monkeypatch.setattr("api.main.conversar_en_vivo", falso)
    r = cliente.post("/api/chat", json={"mensaje": "hola", "hilo": HILO})
    assert r.headers["content-type"].startswith("text/event-stream")
    assert [t for t, _ in _eventos(r.text)] == ["hilo", "herramienta", "texto", "fin"]
    assert _eventos(r.text)[0][1] == {"hilo": HILO}


def test_chat_sin_hilo_crea_uno_nuevo(monkeypatch):
    monkeypatch.setattr("api.main.conversar_en_vivo", lambda m, h, usuario: iter([{"tipo": "fin"}]))
    hilo = _eventos(cliente.post("/api/chat", json={"mensaje": "hola"}).text)[0][1]["hilo"]
    assert len(hilo) == 32


def test_un_error_del_modelo_llega_como_evento_sin_detalles_internos(monkeypatch):
    def roto(mensaje, hilo, usuario):
        raise RuntimeError("clave secreta rota")
        yield

    monkeypatch.setattr("api.main.conversar_en_vivo", roto)
    texto = cliente.post("/api/chat", json={"mensaje": "hola", "hilo": HILO}).text
    tipo, datos = _eventos(texto)[-1]
    assert tipo == "error" and "secreta" not in texto and "01 8000" in datos["mensaje"]


def test_rechaza_mensajes_vacios_demasiado_largos_o_hilos_inventados():
    assert cliente.post("/api/chat", json={"mensaje": ""}).status_code == 422
    assert cliente.post("/api/chat", json={"mensaje": "x" * 1001}).status_code == 422
    assert cliente.post("/api/chat", json={"mensaje": "hola", "hilo": "../../etc"}).status_code == 422
    assert cliente.get("/api/hilos/no-es-un-hilo/mensajes").status_code == 422


def test_chat_por_telefono_responde_json_y_mantiene_la_conversacion(monkeypatch):
    recibido = []

    def falso(mensaje, hilo, usuario):
        recibido.append((mensaje, hilo, usuario))
        return "Hola", [{"herramienta": "consultar_datos", "args": {"tabla": "sedes"}}]

    monkeypatch.setattr("api.main.conversar", falso)
    monkeypatch.setattr("api.main.pendiente_de_aprobacion", lambda hilo: None)
    r = cliente.post("/chat", json={"mensaje": "hola", "telefono": "573001234567"})
    assert r.status_code == 200
    assert r.json() == {"respuesta": "Hola", "herramientas": ["consultar_datos"], "ok": True, "pendiente": None}
    cliente.post("/chat", json={"mensaje": "y su teléfono?", "telefono": "+573001234567"})
    cliente.post("/chat", json={"mensaje": "hola", "telefono": "573009999999"})
    assert recibido[0][1:] == recibido[1][1:]  # el mismo número, con o sin +, vuelve a la misma conversación y memoria
    assert recibido[0][1] != recibido[2][1] and recibido[0][2] != recibido[2][2]  # otro número, otra conversación
    assert "573001234567" not in "".join(recibido[0][1:])  # el número no queda escrito en los identificadores


def test_chat_por_telefono_responde_con_cortesia_si_el_agente_falla(monkeypatch):
    def falla(mensaje, hilo, usuario):
        raise RuntimeError("clave secreta rota")

    monkeypatch.setattr("api.main.conversar", falla)
    r = cliente.post("/chat", json={"mensaje": "hola", "telefono": "573001234567"})
    assert r.status_code == 200 and r.json()["ok"] is False
    assert "clave secreta" not in r.text and r.json()["respuesta"].startswith("En este momento no pude responder")


def test_chat_por_telefono_rechaza_telefonos_y_mensajes_invalidos():
    assert cliente.post("/chat", json={"mensaje": "hola", "telefono": "abc"}).status_code == 422
    assert cliente.post("/chat", json={"mensaje": "", "telefono": "573001234567"}).status_code == 422
    assert cliente.post("/chat", json={"mensaje": "x" * 1001, "telefono": "573001234567"}).status_code == 422


def test_historial_devuelve_la_conversacion_guardada(monkeypatch):
    monkeypatch.setattr("api.main.historial_visible", lambda hilo: [{"rol": "user", "texto": "hola"}])
    assert cliente.get(f"/api/hilos/{HILO}/mensajes").json() == {
        "hilo": HILO,
        "mensajes": [{"rol": "user", "texto": "hola"}],
    }


def test_el_chat_pasa_el_cliente_al_agente(monkeypatch):
    recibido = {}

    def falso(mensaje, hilo, usuario):
        recibido["usuario"] = usuario
        yield {"tipo": "fin"}

    monkeypatch.setattr("api.main.conversar_en_vivo", falso)
    cliente.post("/api/chat", json={"mensaje": "hola", "usuario": "b" * 32})
    assert recibido["usuario"] == "b" * 32
    cliente.post("/api/chat", json={"mensaje": "hola"})
    assert recibido["usuario"] == "anonimo"
    assert cliente.post("/api/chat", json={"mensaje": "hola", "usuario": "../x"}).status_code == 422


def test_ver_y_borrar_lo_que_el_agente_recuerda(monkeypatch):
    monkeypatch.setattr("api.main.datos_del_cliente", lambda u: ["Vive en Cali"])
    monkeypatch.setattr("api.main.olvidar_cliente", lambda u: 1)
    assert cliente.get(f"/api/usuarios/{'c' * 32}/datos").json() == {"datos": ["Vive en Cali"]}
    assert cliente.delete(f"/api/usuarios/{'c' * 32}/datos").json() == {"borrados": 1}
    assert cliente.get("/api/usuarios/no-valido/datos").status_code == 422


def test_al_arrancar_la_api_calienta_el_agente_en_segundo_plano(monkeypatch):
    llamado = threading.Event()
    monkeypatch.setattr("api.main.calentar", llamado.set)
    with TestClient(app) as c:
        assert c.get("/api/salud").status_code == 200
        assert llamado.wait(timeout=5)


# --- aprobación humana ---
def test_chat_por_telefono_informa_lo_que_queda_pendiente_de_aprobacion(monkeypatch):
    pendiente = {"herramienta": "radicar_reclamo", "args": {"ciudad": "Ibagué"}}
    monkeypatch.setattr("api.main.conversar", lambda m, h, usuario: ("En revisión", []))
    monkeypatch.setattr("api.main.pendiente_de_aprobacion", lambda hilo: pendiente)
    r = cliente.post("/chat", json={"mensaje": "radica mi reclamo", "telefono": "573001234567"})
    assert r.json()["pendiente"] == pendiente and r.json()["ok"] is True
    monkeypatch.setattr("api.main.pendiente_de_aprobacion", lambda hilo: None)
    assert cliente.post("/chat", json={"mensaje": "hola", "telefono": "573001234567"}).json()["pendiente"] is None


def test_aprobar_esta_deshabilitado_sin_clave_y_rechaza_una_equivocada(monkeypatch):
    cuerpo = {"telefono": "573001234567", "decision": "aprobar"}
    monkeypatch.delenv("APROBADOR_TOKEN", raising=False)
    assert cliente.post("/aprobar", json=cuerpo, headers={"X-Aprobador": "x"}).status_code == 503
    monkeypatch.setenv("APROBADOR_TOKEN", "secreto-largo")
    assert cliente.post("/aprobar", json=cuerpo).status_code == 401
    assert cliente.post("/aprobar", json=cuerpo, headers={"X-Aprobador": "otro"}).status_code == 401


def test_aprobar_decide_lo_pendiente_o_dice_que_no_hay_nada(monkeypatch):
    monkeypatch.setenv("APROBADOR_TOKEN", "secreto-largo")
    cabecera = {"X-Aprobador": "secreto-largo"}
    cuerpo = {"telefono": "573001234567", "decision": "rechazar"}
    monkeypatch.setattr("api.main.pendiente_de_aprobacion", lambda hilo: None)
    assert cliente.post("/aprobar", json=cuerpo, headers=cabecera).status_code == 404
    recibido = {}

    def falso(hilo, decision, usuario):
        recibido.update(hilo=hilo, decision=decision, usuario=usuario)
        return "No se radicó.", []

    monkeypatch.setattr("api.main.pendiente_de_aprobacion", lambda hilo: {"herramienta": "radicar_reclamo", "args": {}})
    monkeypatch.setattr("api.main.resolver_aprobacion", falso)
    r = cliente.post("/aprobar", json=cuerpo, headers=cabecera)
    assert r.json() == {"decision": "rechazar", "respuesta": "No se radicó.", "avisado_por_whatsapp": False}
    assert recibido["decision"] == "rechazar" and "573001234567" not in recibido["hilo"] + recibido["usuario"]
    assert cliente.post("/aprobar", json={"telefono": "abc", "decision": "aprobar"}, headers=cabecera).status_code == 422
    assert cliente.post("/aprobar", json={**cuerpo, "decision": "tal vez"}, headers=cabecera).status_code == 422


def test_aprobar_con_responder_pasa_el_mensaje_y_lo_exige(monkeypatch):
    monkeypatch.setenv("APROBADOR_TOKEN", "secreto-largo")
    cabecera = {"X-Aprobador": "secreto-largo"}
    recibido = {}
    monkeypatch.setattr("api.main.pendiente_de_aprobacion", lambda hilo: {"herramienta": "radicar_reclamo", "args": {}})
    monkeypatch.setattr("api.main.resolver_aprobacion", lambda hilo, decision, usuario, mensaje=None: recibido.update(d=decision, m=mensaje) or ("Falta la dirección.", []))
    cuerpo = {"telefono": "573001234567", "decision": "responder"}
    assert cliente.post("/aprobar", json=cuerpo, headers=cabecera).status_code == 422  # sin mensaje no se acepta
    r = cliente.post("/aprobar", json={**cuerpo, "mensaje": "Falta la dirección del predio."}, headers=cabecera)
    assert r.status_code == 200 and recibido == {"d": "responder", "m": "Falta la dirección del predio."}


def test_aprobar_avisa_al_cliente_por_whatsapp(monkeypatch):
    monkeypatch.setenv("APROBADOR_TOKEN", "secreto-largo")
    enviados = []
    monkeypatch.setattr("api.main.pendiente_de_aprobacion", lambda hilo: {"herramienta": "radicar_reclamo", "args": {}})
    monkeypatch.setattr("api.main.resolver_aprobacion", lambda hilo, decision, usuario: ("Reclamo radicado.", []))
    monkeypatch.setattr("api.main.enviar_texto", lambda tel, texto: enviados.append((tel, texto)) or True)
    cuerpo = {"telefono": "573001234567", "decision": "aprobar"}
    r = cliente.post("/aprobar", json=cuerpo, headers={"X-Aprobador": "secreto-largo"})
    assert r.json()["avisado_por_whatsapp"] is True and enviados == [("573001234567", "Reclamo radicado.")]


def test_el_chat_web_se_sirve_desde_la_api_sin_tapar_las_rutas(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.main import montar_frontend

    (tmp_path / "index.html").write_text("<html>Chat Celsia</html>", encoding="utf-8")
    aplicacion = FastAPI()

    @aplicacion.get("/api/salud")
    def salud():
        return {"estado": "ok"}

    assert montar_frontend(aplicacion, tmp_path) is True
    cliente = TestClient(aplicacion)
    assert "Chat Celsia" in cliente.get("/").text
    assert cliente.get("/api/salud").json() == {"estado": "ok"}  # la montura en «/» no tapa las rutas de la API
    assert "Chat Celsia" in cliente.get("/c/0123456789abcdef0123456789abcdef").text  # recargar la página de una conversación devuelve el chat
    assert cliente.get("/api/no-existe").status_code == 404

    monkeypatch.setenv("SERVIR_FRONTEND", "0")
    assert montar_frontend(FastAPI(), tmp_path) is False


def test_el_chat_web_no_se_monta_si_falta_el_frontend_compilado(tmp_path):
    from fastapi import FastAPI

    from api.main import montar_frontend

    assert montar_frontend(FastAPI(), tmp_path) is False


def test_salud_dice_cuantos_numeros_estan_autorizados(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ALLOWLIST", "+573001112233,+573104445566")
    assert cliente.get("/api/salud").json()["allowlist_whatsapp"] == 2
    monkeypatch.delenv("WHATSAPP_ALLOWLIST", raising=False)
    assert cliente.get("/api/salud").json()["allowlist_whatsapp"] == "abierta"
