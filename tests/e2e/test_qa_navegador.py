"""Revisión de calidad con Playwright (anuncio 008): la app en un navegador de verdad, la API y el webhook de WhatsApp.

Se corre con `make qa`; `make test` no la incluye (ver tests/conftest.py). Necesita el chat web compilado (`make chat-web`).

- Sin `QA_URL` levanta su propio servidor en este equipo con un agente simulado: no llama a ningún modelo, no manda nada a Meta y
  no cuesta nada. Así se repite antes de cada push.
- Con `QA_URL=http://127.0.0.1:8000` revisa la app ya encendida. La pregunta al modelo real (centavos) solo se hace si además está
  `QA_MODELO_REAL=1`, una sola vez.

Usa el navegador Edge del equipo; `QA_CANAL=chrome` usa Chrome. `QA_CAPTURAS=carpeta` guarda una foto de cada pantalla.
Playwright no entra a WhatsApp: la conversación real se prueba desde un teléfono.
"""

import hashlib
import hmac
import json
import os
import re
import socket
import threading
import time
import uuid
from pathlib import Path

import pytest
import requests
from playwright.sync_api import expect, sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
URL_DESPLEGADA = os.environ.get("QA_URL", "").rstrip("/")
MODELO_REAL = os.environ.get("QA_MODELO_REAL") == "1"
TAMANOS = {"celular": {"width": 390, "height": 844}, "escritorio": {"width": 1366, "height": 768}}
PREGUNTA = "¿Qué es una granja solar?"
SECRETO, VERIFICACION = "secreto-solo-de-prueba", "verificacion-solo-de-prueba"
ESPERA_RESPUESTA_MS = 120_000 if MODELO_REAL else 15_000


def _agente_simulado(mensaje, hilo, usuario):
    """Los mismos tipos de evento que manda el agente real, sin llamar a ningún modelo."""
    yield {"tipo": "herramienta", "herramienta": "buscar_en_base", "args": {"consulta": mensaje}}
    fuente = {"chunk_id": "qa-1", "documento": "Granjas solares", "fragmento": 1, "fuente": "https://www.celsia.com/", "extracto": "Texto de prueba."}
    yield {"tipo": "fuentes", "fuentes": [fuente]}
    yield {"tipo": "texto", "texto": "Respuesta de prueba: una **granja solar** reúne muchos paneles."}
    yield {"tipo": "fin", "usadas": "Usó: buscó en el texto del sitio", "tokens_entrada": 10, "tokens_salida": 5, "costo_usd": 0.0}


@pytest.fixture(scope="module")
def servidor():
    """(dirección, avisos de WhatsApp recibidos). `avisos` es None cuando se revisa una app ya encendida."""
    if URL_DESPLEGADA:
        yield URL_DESPLEGADA, None
        return
    if not (RAIZ / "frontend" / "dist" / "index.html").is_file():
        pytest.fail("Falta el chat web compilado: corre `make chat-web`")
    import uvicorn

    import api.main as api

    avisos = []
    with pytest.MonkeyPatch.context() as parche:
        parche.setattr(api, "conversar_en_vivo", _agente_simulado)
        parche.setattr(api, "pendiente_de_aprobacion", lambda hilo: None)
        parche.setattr(api, "calentar", lambda: None)
        parche.setattr(api, "atender_mensaje_de_whatsapp", lambda *datos: avisos.append(datos))
        parche.setenv("WHATSAPP_APP_SECRET", SECRETO)
        parche.setenv("WHATSAPP_VERIFY_TOKEN", VERIFICACION)
        parche.setenv("WHATSAPP_ALLOWLIST", "*")
        with socket.socket() as libre:
            libre.bind(("127.0.0.1", 0))
            puerto = libre.getsockname()[1]
        prueba = uvicorn.Server(uvicorn.Config(api.app, host="127.0.0.1", port=puerto, log_level="warning"))
        hilo = threading.Thread(target=prueba.run, daemon=True)
        hilo.start()
        limite = time.monotonic() + 30
        while not prueba.started:
            assert hilo.is_alive() and time.monotonic() < limite, "el servidor de prueba no arrancó"
            time.sleep(0.1)
        yield f"http://127.0.0.1:{puerto}", avisos
        prueba.should_exit = True
        hilo.join(timeout=10)


@pytest.fixture(scope="module")
def navegador():
    with sync_playwright() as p:
        abierto = p.chromium.launch(channel=os.environ.get("QA_CANAL", "msedge"))
        yield abierto
        abierto.close()


@pytest.fixture(params=TAMANOS, ids=list(TAMANOS))
def pantalla(request, navegador, servidor):
    """Una pestaña limpia del tamaño pedido que anota los errores de consola y las respuestas fallidas; al final no debe haber ninguno."""
    tamano = request.param
    celular = tamano == "celular"
    contexto = navegador.new_context(base_url=servidor[0], viewport=TAMANOS[tamano], is_mobile=celular, has_touch=celular, locale="es-CO")
    pagina = contexto.new_page()
    problemas = []
    pagina.on("console", lambda m: m.type in ("error", "warning") and problemas.append(f"consola {m.type}: {m.text}"))
    pagina.on("pageerror", lambda e: problemas.append(f"error de la página: {e}"))
    pagina.on("requestfailed", lambda r: problemas.append(f"petición fallida: {r.url} {r.failure}"))
    pagina.on("response", lambda r: r.status >= 400 and problemas.append(f"respuesta {r.status}: {r.url}"))
    pagina.tamano = tamano
    yield pagina
    contexto.close()
    assert not problemas, "\n".join(problemas)


def _foto(pagina, nombre):
    if carpeta := os.environ.get("QA_CAPTURAS"):
        Path(carpeta).mkdir(parents=True, exist_ok=True)
        pagina.screenshot(path=str(Path(carpeta) / f"{nombre}-{pagina.tamano}.png"))


def _sin_desplazamiento_horizontal(pagina):
    sobra = pagina.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert sobra <= 0, f"la página se sale {sobra} px a lo ancho"


def test_la_portada_carga_completa(pantalla):
    pantalla.goto("/")
    expect(pantalla.get_by_role("heading", name="¿En qué te puedo ayudar?")).to_be_visible()
    expect(pantalla.locator("header .estado")).to_contain_text("En línea")
    expect(pantalla.locator("button.tarjeta")).to_have_count(4)
    expect(pantalla.get_by_role("textbox", name="Pregunta")).to_be_visible()
    qr = pantalla.get_by_role("img", name="Código QR para abrir el chat de WhatsApp del asistente")
    qr.scroll_into_view_if_needed()
    assert qr.evaluate("img => img.complete && img.naturalWidth > 0"), "el QR de WhatsApp no cargó"
    pantalla.wait_for_load_state("networkidle")
    _sin_desplazamiento_horizontal(pantalla)
    _foto(pantalla, "portada")


def test_el_flujo_del_pitch_responde_con_fuentes_y_herramienta(pantalla):
    if URL_DESPLEGADA and not (MODELO_REAL and pantalla.tamano == os.environ.get("QA_TAMANO_PITCH", "escritorio")):
        pytest.skip("en la app encendida solo se pregunta al modelo real una vez y con QA_MODELO_REAL=1")
    pantalla.goto("/")
    pantalla.get_by_role("button", name="Ver detalles técnicos").click()
    pantalla.get_by_role("textbox", name="Pregunta").fill(PREGUNTA)
    pantalla.get_by_role("button", name="Enviar").click()
    respuesta = pantalla.locator("article.burbuja.assistant")
    expect(respuesta.locator("p.pie")).to_be_visible(timeout=ESPERA_RESPUESTA_MS)  # tokens y costo: llegan con el fin del turno
    expect(respuesta.locator(".contenido")).to_contain_text("solar", ignore_case=True)
    expect(respuesta.locator("p.herramienta")).to_be_visible()
    expect(respuesta.locator("details.fuentes summary")).to_contain_text("Fuentes")
    expect(respuesta.locator("details.fuentes li").first).to_contain_text("fragmento")
    expect(pantalla.locator(".error")).to_have_count(0)
    _sin_desplazamiento_horizontal(pantalla)
    _foto(pantalla, "respuesta")


def test_los_botones_de_la_cabecera_funcionan(pantalla):
    pantalla.goto("/")
    pantalla.locator("header").get_by_role("button", name="Mis datos" if pantalla.tamano == "celular" else "Lo que recuerdo").click()
    expect(pantalla.get_by_role("region", name="Memoria de largo plazo")).to_contain_text("No tengo datos de tu perfil guardados")
    _sin_desplazamiento_horizontal(pantalla)
    pantalla.locator("header").get_by_role("button", name="Nueva" if pantalla.tamano == "celular" else "Nueva conversación").click()
    expect(pantalla.get_by_role("heading", name="¿En qué te puedo ayudar?")).to_be_visible()


def test_una_direccion_desconocida_vuelve_al_inicio(pantalla):
    pantalla.goto("/c/no-es-una-conversacion")
    expect(pantalla.get_by_role("heading", name="¿En qué te puedo ayudar?")).to_be_visible()
    expect(pantalla).to_have_url(re.compile(r"/$"))
    if not URL_DESPLEGADA:  # preguntar después de llegar así debe funcionar (con el agente simulado no cuesta)
        pantalla.get_by_role("textbox", name="Pregunta").fill(PREGUNTA)
        pantalla.get_by_role("button", name="Enviar").click()
        expect(pantalla.locator("article.burbuja.assistant .contenido")).to_contain_text("granja solar")
        expect(pantalla.locator(".error")).to_have_count(0)


def test_el_panel_abre_sin_errores(pantalla):
    pantalla.goto("/panel")
    expect(pantalla.get_by_role("button", name="Ver", exact=True)).to_be_visible()
    pantalla.wait_for_load_state("networkidle")
    _foto(pantalla, "panel")


def test_la_api_dice_que_esta_sana(servidor):
    r = requests.get(f"{servidor[0]}/api/salud", timeout=30)
    assert r.status_code == 200 and r.json()["estado"] == "ok"
    if URL_DESPLEGADA:
        assert r.json()["almacen"] == "qdrant", r.json()


def _webhook_propio(servidor):
    if servidor[1] is None:
        pytest.skip("el webhook se prueba en el servidor propio: aquí no se conoce el secreto de la app encendida")
    return servidor


def test_el_webhook_de_whatsapp_se_verifica(servidor):
    base, _ = _webhook_propio(servidor)
    parametros = {"hub.mode": "subscribe", "hub.verify_token": VERIFICACION, "hub.challenge": "12345"}
    r = requests.get(f"{base}/webhook/whatsapp", params=parametros, timeout=30)
    assert r.status_code == 200 and r.text == "12345"


def test_el_webhook_de_whatsapp_responde_200_a_un_aviso_firmado(servidor):
    base, avisos = _webhook_propio(servidor)
    mensaje = {"id": f"wamid.qa-{uuid.uuid4().hex}", "from": "573000000000", "type": "text", "text": {"body": PREGUNTA}}
    cuerpo = json.dumps({"object": "whatsapp_business_account", "entry": [{"changes": [{"field": "messages", "value": {"messages": [mensaje]}}]}]}).encode()
    firma = "sha256=" + hmac.new(SECRETO.encode(), cuerpo, hashlib.sha256).hexdigest()
    r = requests.post(f"{base}/webhook/whatsapp", data=cuerpo, headers={"X-Hub-Signature-256": firma}, timeout=30)
    assert r.status_code == 200 and r.json() == {"ok": True, "mensajes": 1}
    limite = time.monotonic() + 10
    while not avisos and time.monotonic() < limite:
        time.sleep(0.1)
    assert avisos and avisos[-1][2] == PREGUNTA, "el mensaje no llegó a quien lo atiende"


def test_el_webhook_de_whatsapp_rechaza_un_aviso_sin_firma(servidor):
    base, _ = _webhook_propio(servidor)
    assert requests.post(f"{base}/webhook/whatsapp", data=b"{}", timeout=30).status_code == 401
