import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from taaml.limite import TEXTO_LIMITE, LimitePorTelefono, limite_desde_entorno


class Reloj:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_deja_pasar_hasta_el_maximo_y_rechaza_el_siguiente_con_la_espera():
    reloj = Reloj()
    limite = LimitePorTelefono(3, 60, reloj)
    assert all(limite.revisar("573001").permitido for _ in range(3))
    reloj.t += 20
    d = limite.revisar("573001")
    assert not d.permitido and d.espera_s == 40  # el más antiguo sale de la ventana a los 60 s


def test_cada_telefono_cuenta_aparte_y_la_ventana_se_libera():
    reloj = Reloj()
    limite = LimitePorTelefono(1, 60, reloj)
    assert limite.revisar("573001").permitido and limite.revisar("573002").permitido
    assert not limite.revisar("573001").permitido
    reloj.t += 61
    assert limite.revisar("573001").permitido


def test_solo_el_primer_rechazo_de_la_ventana_pide_avisar():
    limite = LimitePorTelefono(1, 60, Reloj())
    limite.revisar("573001")
    assert limite.revisar("573001").avisar
    assert not limite.revisar("573001").avisar


def test_maximo_cero_lo_apaga_y_el_entorno_lo_configura(monkeypatch):
    assert all(LimitePorTelefono(0, 60).revisar("5730").permitido for _ in range(50))
    monkeypatch.setenv("LIMITE_MENSAJES", "2")
    monkeypatch.setenv("LIMITE_VENTANA_S", "30")
    limite = limite_desde_entorno()
    assert (limite.maximo, limite.ventana) == (2, 30)
    monkeypatch.setenv("LIMITE_MENSAJES", "mucho")  # ilegible: queda el valor por defecto
    assert limite_desde_entorno().maximo == 8


def test_no_guarda_el_numero_en_claro():
    limite = LimitePorTelefono(1, 60, Reloj())
    limite.revisar("573001234567")
    assert all("573001234567" not in clave for clave in limite._envios)


@pytest.fixture
def api_con_limite(monkeypatch):
    monkeypatch.setattr(api_main, "LIMITE", LimitePorTelefono(2, 60, Reloj()))
    monkeypatch.setattr(
        api_main, "responder_a_telefono", lambda tel, msg, canal="chat": api_main.RespuestaDelAgente(respuesta="ok", herramientas=[])
    )
    return TestClient(api_main.app)


def test_chat_responde_429_con_retry_after_al_pasarse(api_con_limite):
    cuerpo = {"mensaje": "hola", "telefono": "573001234567"}
    assert [api_con_limite.post("/chat", json=cuerpo).status_code for _ in range(2)] == [200, 200]
    r = api_con_limite.post("/chat", json=cuerpo)
    assert r.status_code == 429 and r.json()["detail"] == TEXTO_LIMITE and int(r.headers["Retry-After"]) > 0
    otro = api_con_limite.post("/chat", json={**cuerpo, "telefono": "573009999999"})
    assert otro.status_code == 200  # otro teléfono no se ve afectado


def test_whatsapp_avisa_una_sola_vez_y_no_llama_al_agente_al_pasarse(monkeypatch):
    enviados, preguntas = [], []
    monkeypatch.setattr(api_main, "LIMITE", LimitePorTelefono(1, 60, Reloj()))
    monkeypatch.setattr(api_main, "enviar_texto", lambda tel, texto: enviados.append(texto))
    monkeypatch.setattr(
        api_main,
        "responder_a_telefono",
        lambda tel, msg, canal="chat": preguntas.append(msg) or api_main.RespuestaDelAgente(respuesta="ok", herramientas=[]),
    )
    for _ in range(4):
        api_main.atender_mensaje_de_whatsapp("573001234567", "text", "hola")
    assert preguntas == ["hola"]  # el agente (y la cuota) solo se usó una vez
    assert enviados == ["ok", TEXTO_LIMITE]  # y el aviso salió una sola vez
