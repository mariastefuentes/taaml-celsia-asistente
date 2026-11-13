import json

from fastapi.testclient import TestClient

from api.main import app

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
    assert r.status_code == 200 and r.json()["estado"] == "ok" and "gemini" in r.json()["modelo"]


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
