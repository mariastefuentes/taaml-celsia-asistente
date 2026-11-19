"""Menú con botones, /nuevo, «escribiendo…», banco de preguntas hostiles, chequeo previo y borrador del informe (todo sin red ni modelo)."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

import api.main as api_main
from api.main import RespuestaDelAgente
from taaml import actividad, agente, whatsapp

CLIENTE = "573001234567"
RAIZ = Path(__file__).resolve().parent.parent


def _script(nombre: str):
    espec = importlib.util.spec_from_file_location(nombre, RAIZ / "scripts" / f"{nombre}.py")
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(autouse=True)
def _limpio(monkeypatch):
    actividad.vaciar()
    monkeypatch.setattr(api_main, "marcar_leido", lambda id_mensaje: True)
    monkeypatch.setattr(api_main, "responder_a_telefono", lambda *a, **k: pytest.fail("este mensaje no debe llegar al modelo"))


def test_un_saludo_muestra_el_menu_con_tres_botones_sin_llamar_al_modelo(monkeypatch):
    enviados = []
    monkeypatch.setattr(api_main, "enviar_botones", lambda tel, texto, botones: enviados.append(botones) or True)
    for saludo in ("Hola", "¡Buenos días!", "MENÚ", "ayuda"):
        api_main.atender_mensaje_de_whatsapp(CLIENTE, "text", saludo)
    assert len(enviados) == 4 and all(len(b) == 3 and all(len(r) <= 20 for _, r in b) for b in enviados)
    assert actividad.recientes()[-1]["estado"] == "respondido"


def test_sin_botones_el_menu_llega_como_texto(monkeypatch):
    textos = []
    monkeypatch.setattr(api_main, "enviar_botones", lambda *a: False)
    monkeypatch.setattr(api_main, "enviar_texto", lambda tel, texto: textos.append(texto) or True)
    api_main.atender_mensaje_de_whatsapp(CLIENTE, "text", "hola")
    assert len(textos) == 1 and "sedes y canales" in textos[0]


def test_tocar_un_boton_del_menu_es_una_pregunta_normal_al_agente(monkeypatch):
    preguntas = []
    monkeypatch.setattr(api_main, "responder_a_telefono", lambda t, m, canal="chat": preguntas.append(m) or RespuestaDelAgente(respuesta="ok", herramientas=[]))
    monkeypatch.setattr(api_main, "enviar_texto", lambda *a: True)
    api_main.atender_mensaje_de_whatsapp(CLIENTE, "interactive", "menu:solar")
    assert preguntas == [api_main.PREGUNTA_DEL_BOTON["menu:solar"]]


def test_nuevo_reinicia_la_conversacion_y_avisa(monkeypatch):
    reiniciados, textos = [], []
    monkeypatch.setattr(api_main, "reiniciar_conversacion", lambda hilo: reiniciados.append(hilo) or True)
    monkeypatch.setattr(api_main, "enviar_texto", lambda tel, texto: textos.append(texto) or True)
    api_main.atender_mensaje_de_whatsapp(CLIENTE, "text", "/nuevo")
    assert reiniciados == [api_main.ids_del_telefono(CLIENTE)[0]] and "de cero" in textos[0]


def test_nuevo_no_reinicia_si_hay_un_reclamo_pendiente(monkeypatch):
    textos = []
    monkeypatch.setattr(api_main, "reiniciar_conversacion", lambda hilo: False)
    monkeypatch.setattr(api_main, "enviar_texto", lambda tel, texto: textos.append(texto) or True)
    api_main.atender_mensaje_de_whatsapp(CLIENTE, "text", "/nuevo")
    assert "esperando la revisión" in textos[0] and actividad.recientes()[-1]["estado"] == "pendiente de aprobación"


def test_un_mensaje_normal_si_llega_al_agente_y_se_marca_leido(monkeypatch):
    leidos = []
    monkeypatch.setattr(api_main, "marcar_leido", lambda id_mensaje: leidos.append(id_mensaje) or True)
    monkeypatch.setattr(api_main, "responder_a_telefono", lambda t, m, canal="chat": RespuestaDelAgente(respuesta="Hay 3 sedes", herramientas=[]))
    textos = []
    monkeypatch.setattr(api_main, "enviar_texto", lambda tel, texto: textos.append(texto) or True)
    api_main.atender_mensaje_de_whatsapp(CLIENTE, "text", "¿Qué sedes hay?", id_mensaje="wamid.1")
    assert leidos == ["wamid.1"] and textos == ["Hay 3 sedes"]


def test_marcar_leido_pide_el_indicador_de_escribiendo(monkeypatch):
    monkeypatch.setenv("WHATSAPP_TOKEN", "t")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123")
    visto = {}
    monkeypatch.setattr(whatsapp.requests, "post", lambda url, json, headers, timeout: visto.update(url=url, json=json) or SimpleNamespace(ok=True))
    assert whatsapp.marcar_leido("wamid.9")
    assert visto["json"]["status"] == "read" and visto["json"]["message_id"] == "wamid.9" and visto["json"]["typing_indicator"] == {"type": "text"}
    assert visto["url"].endswith("/123/messages")


def test_marcar_leido_no_hace_nada_sin_configurar_ni_id(monkeypatch):
    monkeypatch.delenv("WHATSAPP_TOKEN", raising=False)
    assert not whatsapp.marcar_leido("wamid.9")
    monkeypatch.setenv("WHATSAPP_TOKEN", "t")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123")
    assert not whatsapp.marcar_leido("")


def test_reiniciar_conversacion_borra_el_hilo_salvo_que_haya_algo_pendiente(monkeypatch):
    borrados = []
    falso = SimpleNamespace(checkpointer=SimpleNamespace(delete_thread=borrados.append))
    monkeypatch.setattr(agente, "pendiente_de_aprobacion", lambda hilo, modelo=None, agente=None: None)
    assert agente.reiniciar_conversacion("h1", agente=falso) and borrados == ["h1"]
    monkeypatch.setattr(agente, "pendiente_de_aprobacion", lambda hilo, modelo=None, agente=None: {"herramienta": "radicar_reclamo"})
    assert not agente.reiniciar_conversacion("h2", agente=falso) and borrados == ["h1"]


# --- scripts ---
def test_el_banco_hostil_detecta_respuestas_malas_y_deja_pasar_las_buenas():
    banco = _script("40_preguntas_hostiles")
    reglas = {nombre: falla for nombre, _, falla in banco.CASOS if falla}
    assert reglas["Ambigua sin contexto"]("Cuesta $54.900 al mes") and not reglas["Ambigua sin contexto"]("¿Qué servicio te interesa?")
    assert reglas["Celular del gerente"]("Su celular es 311 321 0000") and not reglas["Celular del gerente"]("No tengo esa información")
    assert reglas["Competencia"]("EPM es peor") and not reglas["Competencia"]("Solo puedo hablar de Celsia")
    assert len(banco.CASOS) >= 10 and len({n for n, _, _ in banco.CASOS}) == len(banco.CASOS)


def test_el_chequeo_previo_falla_sin_claves_y_no_imprime_secretos(monkeypatch, capsys):
    chequeo = _script("39_chequeo_whatsapp")
    for nombre in ("WHATSAPP_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN", "APROBADOR_TOKEN"):
        monkeypatch.delenv(nombre, raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "clave-secreta-123")
    chequeo.resultados.clear()
    chequeo.revisar_variables()
    chequeo.revisar_token_de_meta()
    assert sum(1 for e, _, _ in chequeo.resultados if e == "FALTA") >= 5
    assert "clave-secreta-123" not in "".join(que for _, que, _ in chequeo.resultados)


def test_el_chequeo_reconoce_un_token_de_meta_vencido(monkeypatch):
    chequeo = _script("39_chequeo_whatsapp")
    monkeypatch.setenv("WHATSAPP_TOKEN", "viejo")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "123")
    monkeypatch.setattr(chequeo, "pedir", lambda *a, **k: (401, "{}"))
    chequeo.resultados.clear()
    chequeo.revisar_token_de_meta()
    assert chequeo.resultados[-1][0] == "FALTA" and "venció" in chequeo.resultados[-1][1]


def test_el_borrador_del_informe_lista_las_decisiones_y_marca_lo_que_falta():
    borrador = _script("41_borrador_informe")
    titulos = borrador.decisiones()
    assert any(t.startswith("- **D1.**") for t in titulos) and len(titulos) >= 18
    assert borrador.scripts() and borrador.especificaciones()
