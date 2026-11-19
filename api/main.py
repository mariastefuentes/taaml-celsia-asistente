"""API del agente de Celsia: el frontend habla con esto por HTTP y nunca llama al modelo directamente.

Endpoints:
  GET  /api/salud                    estado, modelo del agente y dónde busca por significado (qdrant, numpy o ninguno)
  POST /api/chat                     un turno de conversación; responde por streaming (Server-Sent Events)
  POST /chat                         un turno por teléfono; responde un JSON (para WhatsApp, N8N o cualquier servicio externo); 429 si el teléfono escribe demasiado rápido
  GET/POST /webhook/whatsapp         WhatsApp (Meta): verificación del webhook y mensajes entrantes (se responde por WhatsApp en segundo plano)
  POST /aprobar                      una persona aprueba o rechaza lo que el agente dejó pendiente (necesita el encabezado X-Aprobador)
  GET  /api/hilos/{hilo}/mensajes    la conversación guardada, para recuperarla al recargar la página
  GET  /api/usuarios/{usuario}/datos    lo que el agente recuerda del cliente (memoria de largo plazo)
  DELETE /api/usuarios/{usuario}/datos  borra todo lo que el agente recuerda del cliente
  GET  /panel                        página del panel en vivo de la demostración (pide el token del aprobador en la pantalla)
  GET  /api/actividad                lo que hizo el agente en los últimos turnos (necesita X-Aprobador; lo lee el panel)
Uso:  uv run uvicorn api.main:app --reload --port 8000
"""

import hashlib
import json
import logging
import os
import re
import secrets
import threading
import time
import unicodedata
from collections.abc import Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field, model_validator

from taaml.agente import (
    MODELO_AGENTE,
    calentar,
    conversar,
    conversar_en_vivo,
    datos_del_cliente,
    historial_visible,
    olvidar_cliente,
    pendiente_de_aprobacion,
    reiniciar_conversacion,
    resolver_aprobacion,
)
from taaml import actividad, voz
from taaml.limite import TEXTO_LIMITE, limite_desde_entorno
from taaml.recuperacion import almacen_vectorial
from taaml.whatsapp import (
    TEXTO_NO_SOPORTADO,
    descargar_audio,
    enviar_botones,
    enviar_texto,
    firma_valida,
    marcar_leido,
    mensajes_entrantes,
)

log = logging.getLogger("taaml.api")
LIMITE = limite_desde_entorno()  # mensajes por teléfono y minuto (ver taaml/limite.py): protege la cuota del modelo
ORIGENES = ["http://localhost:5173", "http://127.0.0.1:5173"]  # el servidor de desarrollo del frontend
HILO = re.compile(
    r"^[0-9a-f]{32}$"
)  # los hilos y los clientes son uuid4 en hexadecimal: no se acepta otra cosa como id

@asynccontextmanager
async def _ciclo_de_vida(_: FastAPI):
    """Al arrancar, calienta el agente y Ollama en segundo plano para que la primera pregunta no tarde ~15 s; la API ya responde mientras tanto."""
    threading.Thread(target=calentar, name="calentamiento", daemon=True).start()
    yield


app = FastAPI(title="Agente Celsia", version="1.0", lifespan=_ciclo_de_vida)
app.add_middleware(
    CORSMiddleware, allow_origins=ORIGENES, allow_methods=["GET", "POST"], allow_headers=["Content-Type"]
)


class Pregunta(BaseModel):
    """Cuerpo de POST /api/chat: la pregunta del cliente y, opcionalmente, su conversación y su identificador."""

    mensaje: str = Field(min_length=1, max_length=1000, description="Lo que escribe el cliente")
    hilo: str | None = Field(default=None, description="Identificador de la conversación; si falta se crea uno nuevo")
    usuario: str | None = Field(
        default=None, description="Identificador del cliente (para su memoria de largo plazo); si falta es anónimo"
    )


def _evento(tipo: str, datos: dict) -> str:
    """Un evento Server-Sent Events: `event: <tipo>` y `data: <json>`."""
    return f"event: {tipo}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n"


def _turno(mensaje: str, hilo: str, usuario: str) -> Iterator[str]:
    """Un turno del agente como secuencia de eventos; un fallo del modelo sale como evento `error` sin detalles internos."""
    yield _evento("hilo", {"hilo": hilo})
    try:
        for e in conversar_en_vivo(mensaje, hilo, usuario=usuario):
            yield _evento(e["tipo"], {k: v for k, v in e.items() if k != "tipo"})
    except Exception:  # el detalle va al registro del servidor; el cliente recibe un mensaje que no filtra nada interno
        log.exception("falló el turno del hilo %s", hilo)
        yield _evento(
            "error",
            {
                "mensaje": "No pude responder en este momento. Intenta de nuevo; si sigue fallando, llama a la línea 01 8000 112 115."
            },
        )


@app.get("/api/salud")
def salud() -> dict:
    """Estado de la API, modelo que usa el agente, la base donde busca por significado (Qdrant) y la de la memoria (PostgreSQL o SQLite)."""
    return {
        "estado": "ok",
        "modelo": MODELO_AGENTE,
        "almacen": almacen_vectorial(),
        "memoria": "postgresql" if os.environ.get("DATABASE_URL") else "sqlite",
    }


@app.post("/api/chat")
def chat(pregunta: Pregunta) -> StreamingResponse:
    """Un turno de conversación por streaming; crea el hilo si falta y rechaza identificadores que no sean uuid4 hexadecimal."""
    hilo = pregunta.hilo or uuid4().hex
    if not HILO.match(hilo) or (pregunta.usuario and not HILO.match(pregunta.usuario)):
        raise HTTPException(status_code=422, detail="Identificador inválido")
    return StreamingResponse(
        _turno(pregunta.mensaje, hilo, pregunta.usuario or "anonimo"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class MensajeEntrante(BaseModel):
    """Cuerpo de POST /chat: lo que escribió la persona y su número de teléfono, que identifica su conversación y su memoria."""

    mensaje: str = Field(min_length=1, max_length=1000, description="Lo que escribe el cliente")
    telefono: str = Field(pattern=r"^\+?[0-9]{7,15}$", description="Número del cliente, con indicativo (por ejemplo 573001234567)")


class RespuestaDelAgente(BaseModel):
    """Respuesta de POST /chat: el texto para el cliente y las herramientas que usó el agente."""

    respuesta: str
    herramientas: list[str]
    ok: bool = True
    pendiente: dict | None = None  # algo que una persona debe aprobar (herramienta y argumentos); lo decide POST /aprobar


MENSAJE_DE_FALLO = "En este momento no pude responder. Intenta de nuevo en unos minutos; si sigue fallando, llama a la línea 01 8000 112 115."


def ids_del_telefono(telefono: str) -> tuple[str, str]:
    """(hilo, usuario) estables para un teléfono: el mismo número siempre vuelve a su conversación y a su memoria.

    Se guardan como un hash de 32 caracteres hexadecimales, el formato que ya aceptan el agente y su memoria, así el número
    no queda escrito en la base de datos.
    """
    digitos = "".join(c for c in telefono if c.isdigit())
    return (
        hashlib.sha256(f"hilo:{digitos}".encode()).hexdigest()[:32],
        hashlib.sha256(f"usuario:{digitos}".encode()).hexdigest()[:32],
    )


@app.post("/chat")
def chat_por_telefono(entrada: MensajeEntrante) -> RespuestaDelAgente:
    """Un turno del agente, sin streaming: recibe mensaje y teléfono y devuelve la respuesta en JSON.

    Si el modelo o una herramienta fallan responde con un mensaje cortés (`ok` en falso) en vez de un error, porque quien llama
    (WhatsApp) tiene que poder reenviar algo al cliente.
    """
    decision = LIMITE.revisar(entrada.telefono)
    if not decision.permitido:
        actividad.registrar("chat", entrada.telefono, entrada.mensaje, "límite")
        raise HTTPException(status_code=429, detail=TEXTO_LIMITE, headers={"Retry-After": str(decision.espera_s)})
    return responder_a_telefono(entrada.telefono, entrada.mensaje)


def responder_a_telefono(telefono: str, mensaje: str, canal: str = "chat") -> RespuestaDelAgente:
    """Un turno del agente para ese teléfono (lo usan POST /chat y el webhook de WhatsApp); un fallo sale como mensaje cortés."""
    hilo, usuario = ids_del_telefono(telefono)
    inicio = time.monotonic()
    try:
        texto, llamadas = conversar(mensaje, hilo, usuario=usuario)
    except Exception:  # el detalle va al registro; al cliente no se le filtra nada interno
        log.exception("falló el turno del hilo %s", hilo)
        actividad.registrar(canal, telefono, mensaje, "error", segundos=time.monotonic() - inicio)
        return RespuestaDelAgente(respuesta=MENSAJE_DE_FALLO, herramientas=[], ok=False)
    pendiente = pendiente_de_aprobacion(hilo)
    if pendiente:
        log.info("pendiente de aprobación en el hilo %s: %s", hilo, pendiente["herramienta"])
    herramientas = [ll["herramienta"] for ll in llamadas]
    estado = "pendiente de aprobación" if pendiente else "respondido"
    actividad.registrar(canal, telefono, mensaje, estado, herramientas, time.monotonic() - inicio)
    return RespuestaDelAgente(respuesta=texto, herramientas=herramientas, pendiente=pendiente)


class Decision(BaseModel):
    """Cuerpo de POST /aprobar: de qué teléfono es la conversación y qué decide la persona."""

    telefono: str = Field(pattern=r"^\+?[0-9]{7,15}$")
    decision: Literal["aprobar", "rechazar", "responder"]
    mensaje: str | None = Field(default=None, max_length=500)  # lo que se le dice al cliente cuando la decisión es «responder»

    @model_validator(mode="after")
    def _responder_lleva_mensaje(self) -> "Decision":
        if self.decision == "responder" and not (self.mensaje or "").strip():
            raise ValueError("responder necesita un mensaje")
        return self


@app.post("/aprobar")
def aprobar(decision: Decision, x_aprobador: str | None = Header(default=None)) -> dict:
    """Una persona de Celsia aprueba, rechaza o responde lo que el agente dejó pausado (por ejemplo, radicar un reclamo).

    Solo funciona con el encabezado `X-Aprobador` igual a la variable `APROBADOR_TOKEN` del servidor; sin esa variable queda
    deshabilitado, para que nadie pueda aprobar por su cuenta.
    """
    _exigir_aprobador(x_aprobador)
    return _decidir(decision.telefono, decision.decision, decision.mensaje)


def _exigir_aprobador(x_aprobador: str | None) -> None:
    """Deja pasar solo con el encabezado `X-Aprobador` igual a `APROBADOR_TOKEN`; sin esa variable queda deshabilitado."""
    esperado = os.environ.get("APROBADOR_TOKEN")
    if not esperado:
        raise HTTPException(status_code=503, detail="La aprobación no está habilitada en este servidor")
    if not secrets.compare_digest((x_aprobador or "").encode(), esperado.encode()):
        raise HTTPException(status_code=401, detail="No autorizado")


def _decidir(telefono: str, decision: str, mensaje: str | None = None) -> dict:
    """Aplica la decisión de la persona sobre lo pendiente de ese teléfono y le avisa al cliente por WhatsApp (si está configurado)."""
    hilo, usuario = ids_del_telefono(telefono)
    if not pendiente_de_aprobacion(hilo):
        raise HTTPException(status_code=404, detail="No hay nada pendiente de aprobación para ese teléfono")
    texto, _ = resolver_aprobacion(hilo, decision, usuario=usuario, **({"mensaje": mensaje} if mensaje else {}))
    avisado = enviar_texto(telefono, texto)  # el cliente se entera por WhatsApp (si está configurado)
    actividad.registrar("aprobación", telefono, f"decisión: {decision}", "aprobación")
    return {"decision": decision, "respuesta": texto, "avisado_por_whatsapp": avisado}


PANEL = Path(__file__).with_name("panel.html")


@app.get("/panel", response_class=HTMLResponse)
def panel() -> str:
    """La página del panel en vivo. No lleva datos: los pide a /api/actividad con el token que se escribe en la pantalla."""
    return PANEL.read_text(encoding="utf-8")


@app.get("/api/actividad")
def lo_que_hizo_el_agente(desde: int = Query(default=0, ge=0), x_aprobador: str | None = Header(default=None)) -> dict:
    """Los turnos recientes del agente (herramientas, tiempo, estado), de más vieja a más nueva. Muestra lo que escriben los clientes, por eso pide el token."""
    _exigir_aprobador(x_aprobador)
    filas = actividad.recientes(desde)
    return {"filas": filas, "ultimo": filas[-1]["n"] if filas else desde}


@app.get("/api/hilos/{hilo}/mensajes")
def mensajes(hilo: str) -> dict:
    """La conversación guardada de un hilo, para recuperarla al recargar la página."""
    if not HILO.match(hilo):
        raise HTTPException(status_code=422, detail="Identificador de hilo inválido")
    return {"hilo": hilo, "mensajes": historial_visible(hilo)}


def _usuario_valido(usuario: str) -> str:
    """Devuelve el identificador del cliente o responde 422 si no es un uuid4 hexadecimal."""
    if not HILO.match(usuario):
        raise HTTPException(status_code=422, detail="Identificador de cliente inválido")
    return usuario


@app.get("/api/usuarios/{usuario}/datos")
def datos(usuario: str) -> dict:
    """Lo que el agente recuerda del cliente (memoria de largo plazo)."""
    return {"datos": datos_del_cliente(_usuario_valido(usuario))}


@app.delete("/api/usuarios/{usuario}/datos")
def borrar_datos(usuario: str) -> dict:
    """Borra todo lo que el agente recuerda del cliente y dice cuántos datos eran."""
    return {"borrados": olvidar_cliente(_usuario_valido(usuario))}


# --- WhatsApp (API Cloud de Meta) ---
MAX_AVISOS_VISTOS = 2000
_AVISOS_VISTOS: dict[str, None] = {}  # Meta reintenta si no recibe 200 y puede repetir avisos: cada mensaje se atiende una sola vez


def _ya_atendido(id_mensaje: str) -> bool:
    """Marca el mensaje como visto; True si ya se había atendido. Guarda solo los últimos MAX_AVISOS_VISTOS."""
    if id_mensaje in _AVISOS_VISTOS:
        return True
    _AVISOS_VISTOS[id_mensaje] = None
    while len(_AVISOS_VISTOS) > MAX_AVISOS_VISTOS:
        _AVISOS_VISTOS.pop(next(iter(_AVISOS_VISTOS)))
    return False


BOTON_DE_APROBACION = re.compile(r"^(aprobar|rechazar):([0-9]{7,15})$")


def _digitos(telefono: str) -> str:
    return "".join(c for c in telefono if c.isdigit())


def _es_el_aprobador(telefono: str) -> bool:
    """¿Este teléfono es la persona de Celsia que aprueba con botones (`APROBADOR_WHATSAPP`)? Solo ella puede decidir por WhatsApp."""
    configurado = _digitos(os.environ.get("APROBADOR_WHATSAPP", ""))
    return bool(configurado) and secrets.compare_digest(_digitos(telefono).encode(), configurado.encode())


def _pedir_aprobacion(telefono_cliente: str, pendiente: dict) -> None:
    """Le manda a la persona que aprueba el reclamo con dos botones. Sin `APROBADOR_WHATSAPP`, o si Meta no entrega el mensaje, queda POST /aprobar."""
    aprobador = _digitos(os.environ.get("APROBADOR_WHATSAPP", ""))
    if not aprobador:
        return
    detalle = "\n".join(f"{k}: {v}" for k, v in (pendiente.get("args") or {}).items())[:700]
    digitos = _digitos(telefono_cliente)
    texto = f"Reclamo pendiente de aprobación (cliente {actividad.quien(telefono_cliente)}):\n{detalle}"
    if not enviar_botones(aprobador, texto, [(f"aprobar:{digitos}", "Aprobar"), (f"rechazar:{digitos}", "Rechazar")]):
        log.warning("no se pudo enviar los botones al aprobador: queda POST /aprobar")


def _decidir_por_boton(aprobador: str, identificador: str) -> None:
    """La persona tocó «Aprobar» o «Rechazar»: se aplica la decisión y se le confirma. Cualquier otro botón se ignora."""
    partes = BOTON_DE_APROBACION.match(identificador)
    if not partes:
        return
    try:
        resultado = _decidir(partes.group(2), "aprobar" if partes.group(1) == "aprobar" else "rechazar")
        enviar_texto(aprobador, f"Hecho: {resultado['decision']}. Al cliente se le avisó por WhatsApp: {'sí' if resultado['avisado_por_whatsapp'] else 'no'}.")
    except HTTPException:  # ya no había nada pendiente (otra persona lo decidió, o se repitió el toque)
        enviar_texto(aprobador, "Ese reclamo ya no está pendiente.")


SALUDOS = {"hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "menu", "/menu", "ayuda", "/ayuda", "inicio", "/inicio"}
COMANDOS_NUEVO = {"/nuevo", "/reiniciar"}
TEXTO_MENU = "Hola, soy el asistente virtual de Celsia. ¿Con qué te ayudo? Elige una opción o escríbeme tu pregunta. Con /nuevo empezamos una conversación desde cero."
BOTONES_MENU = [("menu:sedes", "Sedes y canales"), ("menu:reclamo", "Poner un reclamo"), ("menu:solar", "Celsia Solar")]
# Lo que se le pregunta al agente cuando la persona toca cada botón del menú (pasa por el agente como cualquier pregunta).
PREGUNTA_DEL_BOTON = {
    "menu:sedes": "¿Cuáles son las sedes y los canales de atención de Celsia?",
    "menu:reclamo": "Quiero poner un reclamo.",
    "menu:solar": "¿Qué es Celsia Solar y qué ofrece?",
}


def _normalizado(texto: str) -> str:
    """Minúsculas, sin tildes ni signos, para reconocer saludos y comandos escritos de cualquier forma."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9/ ]", "", sin_tildes).strip()


def _responder_comando(telefono: str, texto: str) -> bool:
    """Atiende `/nuevo` y los saludos (menú con botones) sin llamar al modelo. Devuelve True si el mensaje era uno de ellos."""
    clave = _normalizado(texto)
    if clave in COMANDOS_NUEVO:
        hilo, _ = ids_del_telefono(telefono)
        reiniciado = reiniciar_conversacion(hilo)
        enviar_texto(
            telefono,
            "Listo, empezamos de cero. Lo que me hayas contado de ti (tu nombre, por ejemplo) lo sigo recordando."
            if reiniciado
            else "Tu reclamo está esperando la revisión de una persona de Celsia; hasta que la tome no puedo empezar de cero.",
        )
        actividad.registrar("whatsapp", telefono, texto, "respondido" if reiniciado else "pendiente de aprobación")
        return True
    if clave in SALUDOS:
        if not enviar_botones(telefono, TEXTO_MENU, BOTONES_MENU):  # sin botones (ventana de 24 h, Meta caído) el menú va como texto
            enviar_texto(telefono, TEXTO_MENU + "\nPor ejemplo: «sedes y canales», «poner un reclamo» o «qué es Celsia Solar».")
        actividad.registrar("whatsapp", telefono, texto, "respondido")
        return True
    return False


def atender_mensaje_de_whatsapp(telefono: str, tipo: str, texto: str, audio: str = "", id_mensaje: str = "") -> None:
    """Responde un mensaje de WhatsApp: pregunta al agente y envía su respuesta. Corre en segundo plano, después de contestarle 200 a Meta."""
    try:
        if tipo == "interactive" and _es_el_aprobador(telefono) and BOTON_DE_APROBACION.match(texto):
            _decidir_por_boton(telefono, texto)
            return
        marcar_leido(id_mensaje)  # palomitas azules y «escribiendo…» mientras el agente piensa
        if tipo == "interactive" and texto in PREGUNTA_DEL_BOTON:  # el cliente tocó un botón del menú
            tipo, texto = "text", PREGUNTA_DEL_BOTON[texto]
        decision = LIMITE.revisar(telefono)
        if not decision.permitido:
            log.warning("límite de mensajes alcanzado; reintento en %s s", decision.espera_s)
            actividad.registrar("whatsapp", telefono, "(mensaje rechazado por el límite)", "límite")
            if decision.avisar:  # un solo aviso por ventana, para no contestar spam con más mensajes
                enviar_texto(telefono, TEXTO_LIMITE)
            return
        canal = "whatsapp"
        if tipo == "audio" and audio and voz.activa():  # tentativo: ver taaml/voz.py
            descargado = descargar_audio(audio)
            transcrito = voz.transcribir(*descargado) if descargado else None
            if transcrito:
                tipo, texto, canal = "text", transcrito, "whatsapp (voz)"
        if tipo != "text" or not texto.strip():
            actividad.registrar("whatsapp", telefono, f"({tipo or 'mensaje'} sin texto)", "no soportado")
            enviar_texto(telefono, TEXTO_NO_SOPORTADO)
            return
        if canal == "whatsapp" and _responder_comando(telefono, texto):
            return
        respuesta = responder_a_telefono(telefono, texto.strip()[:1000], canal=canal)
        enviar_texto(telefono, respuesta.respuesta)
        if respuesta.pendiente:
            _pedir_aprobacion(telefono, respuesta.pendiente)
    except Exception:  # un fallo aquí no puede perderse en silencio ni tumbar al servidor
        log.exception("falló la atención de un mensaje de WhatsApp")


@app.get("/webhook/whatsapp", response_class=PlainTextResponse)
def verificar_webhook_de_whatsapp(
    modo: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    desafio: str | None = Query(default=None, alias="hub.challenge"),
) -> str:
    """Meta comprueba que el servidor es nuestro: si el token coincide, devuelve el desafío tal cual."""
    esperado = os.environ.get("WHATSAPP_VERIFY_TOKEN")
    if not esperado:
        raise HTTPException(status_code=503, detail="El webhook de WhatsApp no está habilitado en este servidor")
    if modo != "subscribe" or desafio is None or not secrets.compare_digest((token or "").encode(), esperado.encode()):
        raise HTTPException(status_code=403, detail="Verificación rechazada")
    return desafio


@app.post("/webhook/whatsapp")
async def recibir_de_whatsapp(peticion: Request, segundo_plano: BackgroundTasks) -> dict:
    """Avisos de Meta: comprueba la firma, atiende cada mensaje nuevo en segundo plano y responde 200 enseguida.

    El agente tarda de 5 a 25 s; si el 200 esperara a la respuesta, Meta reintentaría el aviso. Los reintentos repetidos se
    descartan por el id del mensaje. Sin `WHATSAPP_APP_SECRET` queda deshabilitado, para no aceptar avisos sin firma.
    """
    secreto = os.environ.get("WHATSAPP_APP_SECRET")
    if not secreto:
        raise HTTPException(status_code=503, detail="El webhook de WhatsApp no está habilitado en este servidor")
    cuerpo = await peticion.body()
    if not firma_valida(cuerpo, peticion.headers.get("X-Hub-Signature-256"), secreto):
        raise HTTPException(status_code=401, detail="Firma inválida")
    try:
        carga = json.loads(cuerpo)
    except ValueError:
        raise HTTPException(status_code=400, detail="Cuerpo inválido") from None
    nuevos = 0
    for m in mensajes_entrantes(carga if isinstance(carga, dict) else {}):
        if _ya_atendido(m["id"]):
            continue
        nuevos += 1
        segundo_plano.add_task(atender_mensaje_de_whatsapp, m["telefono"], m["tipo"], m["texto"], m.get("audio", ""), m["id"])
    return {"ok": True, "mensajes": nuevos}
