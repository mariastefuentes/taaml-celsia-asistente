"""API del agente de Celsia: el frontend habla con esto por HTTP y nunca llama al modelo directamente.

Endpoints:
  GET  /api/salud                    estado, modelo del agente y dónde busca por significado (qdrant, numpy o ninguno)
  POST /api/chat                     un turno de conversación; responde por streaming (Server-Sent Events)
  POST /chat                         un turno por teléfono; responde un JSON (para WhatsApp, N8N o cualquier servicio externo)
  GET/POST /webhook/whatsapp         WhatsApp (Meta): verificación del webhook y mensajes entrantes (se responde por WhatsApp en segundo plano)
  POST /aprobar                      una persona aprueba o rechaza lo que el agente dejó pendiente (necesita el encabezado X-Aprobador)
  GET  /api/hilos/{hilo}/mensajes    la conversación guardada, para recuperarla al recargar la página
  GET  /api/usuarios/{usuario}/datos    lo que el agente recuerda del cliente (memoria de largo plazo)
  DELETE /api/usuarios/{usuario}/datos  borra todo lo que el agente recuerda del cliente
Uso:  uv run uvicorn api.main:app --reload --port 8000
"""

import hashlib
import json
import logging
import os
import re
import secrets
import threading
from collections.abc import Iterator
from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from taaml.agente import (
    MODELO_AGENTE,
    calentar,
    conversar,
    conversar_en_vivo,
    datos_del_cliente,
    historial_visible,
    olvidar_cliente,
    pendiente_de_aprobacion,
    resolver_aprobacion,
)
from taaml.recuperacion import almacen_vectorial
from taaml.whatsapp import TEXTO_NO_SOPORTADO, enviar_texto, firma_valida, mensajes_entrantes

log = logging.getLogger("taaml.api")
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
    """Estado de la API, modelo que usa el agente y la base donde busca por significado (para mostrar en la terminal que es Qdrant)."""
    return {"estado": "ok", "modelo": MODELO_AGENTE, "almacen": almacen_vectorial()}


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
    return responder_a_telefono(entrada.telefono, entrada.mensaje)


def responder_a_telefono(telefono: str, mensaje: str) -> RespuestaDelAgente:
    """Un turno del agente para ese teléfono (lo usan POST /chat y el webhook de WhatsApp); un fallo sale como mensaje cortés."""
    hilo, usuario = ids_del_telefono(telefono)
    try:
        texto, llamadas = conversar(mensaje, hilo, usuario=usuario)
    except Exception:  # el detalle va al registro; al cliente no se le filtra nada interno
        log.exception("falló el turno del hilo %s", hilo)
        return RespuestaDelAgente(respuesta=MENSAJE_DE_FALLO, herramientas=[], ok=False)
    pendiente = pendiente_de_aprobacion(hilo)
    if pendiente:
        log.info("pendiente de aprobación en el hilo %s: %s", hilo, pendiente["herramienta"])
    return RespuestaDelAgente(respuesta=texto, herramientas=[ll["herramienta"] for ll in llamadas], pendiente=pendiente)


class Decision(BaseModel):
    """Cuerpo de POST /aprobar: de qué teléfono es la conversación y qué decide la persona."""

    telefono: str = Field(pattern=r"^\+?[0-9]{7,15}$")
    decision: Literal["aprobar", "rechazar"]


@app.post("/aprobar")
def aprobar(decision: Decision, x_aprobador: str | None = Header(default=None)) -> dict:
    """Una persona de Celsia aprueba o rechaza lo que el agente dejó pausado (por ejemplo, radicar un reclamo).

    Solo funciona con el encabezado `X-Aprobador` igual a la variable `APROBADOR_TOKEN` del servidor; sin esa variable queda
    deshabilitado, para que nadie pueda aprobar por su cuenta.
    """
    esperado = os.environ.get("APROBADOR_TOKEN")
    if not esperado:
        raise HTTPException(status_code=503, detail="La aprobación no está habilitada en este servidor")
    if not secrets.compare_digest((x_aprobador or "").encode(), esperado.encode()):
        raise HTTPException(status_code=401, detail="No autorizado")
    hilo, usuario = ids_del_telefono(decision.telefono)
    if not pendiente_de_aprobacion(hilo):
        raise HTTPException(status_code=404, detail="No hay nada pendiente de aprobación para ese teléfono")
    texto, _ = resolver_aprobacion(hilo, decision.decision, usuario=usuario)
    avisado = enviar_texto(decision.telefono, texto)  # el cliente se entera por WhatsApp (si está configurado)
    return {"decision": decision.decision, "respuesta": texto, "avisado_por_whatsapp": avisado}


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


def atender_mensaje_de_whatsapp(telefono: str, tipo: str, texto: str) -> None:
    """Responde un mensaje de WhatsApp: pregunta al agente y envía su respuesta. Corre en segundo plano, después de contestarle 200 a Meta."""
    try:
        if tipo != "text" or not texto.strip():
            enviar_texto(telefono, TEXTO_NO_SOPORTADO)
            return
        respuesta = responder_a_telefono(telefono, texto.strip()[:1000])
        enviar_texto(telefono, respuesta.respuesta)
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
        segundo_plano.add_task(atender_mensaje_de_whatsapp, m["telefono"], m["tipo"], m["texto"])
    return {"ok": True, "mensajes": nuevos}
