"""API del agente de Celsia: el frontend habla con esto por HTTP y nunca llama al modelo directamente.

Endpoints:
  GET  /api/salud                    estado, modelo del agente y dónde busca por significado (qdrant, numpy o ninguno)
  POST /api/chat                     un turno de conversación; responde por streaming (Server-Sent Events)
  POST /chat                         un turno por teléfono; responde un JSON (para N8N o cualquier servicio externo); 429 si el teléfono escribe demasiado rápido;
                                     con CHAT_TOKEN definida exige el encabezado X-Api-Key (401 si falta o no coincide)
  GET/POST /webhook/whatsapp         WhatsApp (Meta): verificación del webhook y mensajes entrantes (se responde por WhatsApp en segundo plano)
  POST /aprobar                      una persona aprueba o rechaza lo que el agente dejó pendiente (necesita el encabezado X-Aprobador)
  GET/POST /api/pendientes[/{código}] lo que espera a una persona y su decisión sin conocer el teléfono (X-Aprobador; lo usa el panel)
  GET  /api/hilos/{hilo}/mensajes    la conversación guardada, para recuperarla al recargar la página
  GET  /api/usuarios/{usuario}/datos    lo que el agente recuerda del cliente (memoria de largo plazo)
  DELETE /api/usuarios/{usuario}/datos  borra todo lo que el agente recuerda del cliente
  GET  /panel                        página del panel en vivo de la demostración (pide el token del aprobador en la pantalla)
  GET  /api/actividad                lo que hizo el agente en los últimos turnos (necesita X-Aprobador; lo lee el panel)
  GET  /api/semaforo                 si la búsqueda, la memoria y el puente de WhatsApp contestan (X-Aprobador; lo lee el panel)
  GET  /qr-whatsapp.png             el QR de WhatsApp del bot que muestran el chat web y el panel (assets/whatsapp_qr.png)
  GET  /                             el chat web (frontend compilado en frontend/dist), si existe y SERVIR_FRONTEND no es 0: el público lo abre desde su celular
Uso:  uv run uvicorn api.main:app --reload --port 8000
"""

import hashlib
import json
import logging
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from uuid import uuid4

import requests
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as ErrorHTTP
from pydantic import BaseModel, Field, model_validator

from taaml.agente import (
    HERRAMIENTAS,
    MODELO_AGENTE,
    almacen_compartido,
    aviso_de_datos_dudosos,
    calentar,
    costo_del_turno,
    conversar,
    conversar_en_vivo,
    datos_del_cliente,
    fuentes_del_turno,
    historial_visible,
    olvidar_cliente,
    pendiente_de_aprobacion,
    reiniciar_conversacion,
    resolver_aprobacion,
)
from taaml import actividad, aprobaciones, avisos_openclaw, voz
from taaml.atajos import normalizar, respuesta_rapida
from taaml.citas import pide_la_fuente, texto_de_fuentes
from taaml.limite import TEXTO_LIMITE, limite_desde_entorno
from taaml.recuperacion import almacen_vectorial, cargar_fragmentos
from taaml.whatsapp import (
    TEXTO_NO_SOPORTADO,
    autorizado,
    descargar_audio,
    enviar_botones,
    enviar_texto,
    estados_fallidos,
    firma_valida,
    marcar_leido,
    mensajes_entrantes,
    numeros_autorizados,
)

log = logging.getLogger("taaml.api")
LIMITE = limite_desde_entorno()  # mensajes por teléfono y minuto (ver taaml/limite.py): protege la cuota del modelo
ORIGENES = ["http://localhost:5173", "http://127.0.0.1:5173"]  # el servidor de desarrollo del frontend
# Las rutas del navegador no piden clave: solo aceptan un uuid4 en hexadecimal (al azar, imposible de adivinar) como hilo o como
# cliente. Los identificadores de un teléfono se pueden calcular sabiendo el número, y por eso nunca tienen esta forma (D73).
ID_WEB = re.compile(r"^[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$")


def mostrar_trazas_en_la_terminal() -> None:
    """Hace visibles las líneas informativas del proyecto, como las herramientas de cada turno (la traza que se muestra en la demostración).

    uvicorn solo configura sus propios registros: sin esto, de los de `taaml` salen únicamente las advertencias y los errores.
    """
    registro = logging.getLogger("taaml")
    if not registro.handlers:
        manejador = logging.StreamHandler()
        manejador.setFormatter(logging.Formatter("%(levelname)s:     %(message)s"))
        registro.addHandler(manejador)
    registro.setLevel(logging.INFO)


@asynccontextmanager
async def _ciclo_de_vida(_: FastAPI):
    """Al arrancar, muestra las trazas en la terminal y calienta el agente en segundo plano para que la primera pregunta no tarde ~15 s; la API ya responde mientras tanto."""
    mostrar_trazas_en_la_terminal()
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
    inicio = time.monotonic()
    estado, herramientas, nota, costo = "respondido", [], False, None  # lo que queda en la fila del panel
    trozos, fuentes = [], []
    try:
        previo = aprobaciones.tomar_sin_entregar(hilo)  # lo que una persona decidió desde el último mensaje
        if previo:
            yield _evento("texto", {"texto": f"{previo}\n\n"})
        # Lo trivial no despierta al agente; con un reclamo pendiente sí, para no saltarse la aprobación.
        atajo = respuesta_rapida(mensaje) if not previo else None
        if atajo and pendiente_de_aprobacion(hilo):
            atajo = None
        if atajo:
            trozos.append(atajo.texto)
            costo = 0.0
            yield _evento("texto", {"texto": atajo.texto})
            yield _evento(
                "fin",
                {"usadas": f"atajo: {atajo.intencion}", "tokens_entrada": 0, "tokens_salida": 0, "costo_usd": 0.0},
            )
        else:
            for e in conversar_en_vivo(mensaje, hilo, usuario=usuario):
                if e["tipo"] == "pendiente":  # queda a la vista en el panel para que una persona decida
                    aprobaciones.registrar(hilo, usuario, e, "web")
                    estado = "pendiente de aprobación"
                elif e["tipo"] == "texto":
                    trozos.append(e["texto"])
                elif e["tipo"] == "fuentes":
                    fuentes += e["fuentes"]
                elif e["tipo"] == "herramienta":
                    herramientas.append(e["herramienta"])
                elif e["tipo"] == "aviso":
                    nota = True
                elif e["tipo"] == "fin":
                    costo = e.get("costo_usd")
                yield _evento(e["tipo"], {k: v for k, v in e.items() if k != "tipo"})
    except Exception:  # el detalle va al registro del servidor; el cliente recibe un mensaje que no filtra nada interno
        log.exception("falló el turno del hilo %s", hilo)
        estado = "error"
        yield _evento(
            "error",
            {
                "mensaje": "No pude responder en este momento. Intenta de nuevo; si sigue fallando, llama a la línea 01 8000 112 115."
            },
        )
    actividad.registrar(
        "web", hilo, mensaje, estado, herramientas, time.monotonic() - inicio, nota=nota, costo=costo,
        respuesta="".join(trozos), fuentes=fuentes,
    )


@app.get("/api/salud")
def salud() -> dict:
    """Estado de la API, modelo que usa el agente, la base donde busca por significado (Qdrant) y la de la memoria (PostgreSQL o SQLite)."""
    return {
        "estado": "ok",
        "modelo": MODELO_AGENTE,
        "almacen": almacen_vectorial(),
        "memoria": "postgresql" if os.environ.get("DATABASE_URL") else "sqlite",
        "allowlist_whatsapp": len(numeros_autorizados()) or "abierta",
        "avisos_openclaw": avisos_openclaw.activos(),  # ¿se le puede escribir al cliente cuando una persona decide su reclamo?
    }


# --- WhatsApp – Conectar agente: estado del gateway de OpenClaw, QR y página del QR ---
RAIZ = Path(__file__).resolve().parents[1]
NUMERO_AGENTE = "+573150154664"  # el bot del canal de OpenClaw que esta interfaz permite vincular (no se toma de archivos ni de stdin)
QR_PAGINA = RAIZ / "qr_whatsapp.html"
QR_PNG = RAIZ / "qr_whatsapp.png"
GATEWAY_HEALTH = "http://127.0.0.1:18789/health"  # health del gateway de OpenClaw (puerto de la plantilla); no pide credenciales


def _estado_openclaw() -> dict:
    """Probamos el health del gateway de OpenClaw: responde `{"ok":true,"status":"live"}` si está levantado."""
    try:
        r = requests.get(GATEWAY_HEALTH, timeout=5)
        detalle = r.json().get("status", "") if r.ok else ""
        return {"conectado": r.ok, "detalle": detalle}
    except requests.RequestException:
        return {"conectado": False, "detalle": ""}


@app.get("/api/whatsapp/estado")
def estado_whatsapp() -> dict:
    """Estado real de la conexión de WhatsApp, consultando el health del gateway de OpenClaw."""
    probado = _estado_openclaw()
    return {
        "estado": "conectado" if probado["conectado"] else "desconectado",
        "numero": NUMERO_AGENTE,
        "gateway": probado["detalle"],
    }


def _comando_qr() -> list[str]:
    """El comando que genera el QR; `--app` deja el mismo código en assets para el chat web y el panel."""
    return [sys.executable, str(RAIZ / "scripts" / "48_qr_whatsapp.py"), NUMERO_AGENTE, "--html", "--app"]


@app.post("/api/whatsapp/qr")
def generar_qr_whatsapp(peticion: Request) -> dict:
    """Genera el QR con el mecanismo existente (`make qr-whatsapp ARGS="+573150154664 --html --app"`).

    Solo se permite desde la interfaz local de este servidor (el origen es loopback); el número del bot es el fijo.
    """
    if peticion.client.host not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(status_code=403, detail="Solo se genera el QR desde la interfaz local de este servidor")
    try:
        salida = subprocess.run(_comando_qr(), capture_output=True, text=True, timeout=60, check=False)
    except subprocess.TimeoutExpired:
        log.exception("la generación del QR de WhatsApp se acabó")
        raise HTTPException(status_code=500, detail="La generación del QR tardó demasiado; intenta de nuevo")
    if salida.returncode != 0 or not QR_PAGINA.is_file():
        log.error("falló al generar el QR (rc=%s): %s", salida.returncode, (salida.stderr or "")[:300])
        raise HTTPException(status_code=500, detail="No se pudo generar el QR; intenta de nuevo")
    return {"ok": True, "url": "/api/whatsapp/qr-pagina"}


@app.get("/api/whatsapp/qr-pagina", response_class=HTMLResponse)
def qr_whatsapp_pagina() -> str:
    """La página HTML del QR generada por `scripts/48_qr_whatsapp.py`; su `<img>` apunta a `/api/whatsapp/qr-png`."""
    if not QR_PAGINA.is_file():
        raise HTTPException(status_code=404, detail="Falta qr_whatsapp.html: genera el QR desde la interfaz")
    return QR_PAGINA.read_text(encoding="utf-8").replace('src="qr_whatsapp.png"', 'src="/api/whatsapp/qr-png"')


@app.get("/api/whatsapp/qr-png")
def qr_whatsapp_png() -> FileResponse:
    """El QR (qr_whatsapp.png) que muestra la página de arriba."""
    if not QR_PNG.is_file():
        raise HTTPException(status_code=404, detail="Falta qr_whatsapp.png: genera el QR desde la interfaz")
    return FileResponse(QR_PNG, media_type="image/png")


def _origen(peticion: Request) -> str:
    """Quién llama, para limitar a quien no trae teléfono: la dirección que Cloudflare pone en `Cf-Connecting-Ip` (por el túnel) o la del cliente directo."""
    return peticion.headers.get("cf-connecting-ip") or (peticion.client.host if peticion.client else "desconocido")


@app.post("/api/chat")
def chat(pregunta: Pregunta, peticion: Request) -> StreamingResponse:
    """Un turno de conversación por streaming; crea el hilo si falta y rechaza identificadores que no sean uuid4 hexadecimal.

    No trae teléfono ni clave (la usa el frontend del navegador), así que se limita por origen para que nadie gaste la cuota del modelo.
    """
    decision = LIMITE.revisar(f"origen:{_origen(peticion)}")
    if not decision.permitido:
        raise HTTPException(status_code=429, detail=TEXTO_LIMITE, headers={"Retry-After": str(decision.espera_s)})
    hilo = pregunta.hilo or uuid4().hex
    if not ID_WEB.match(hilo) or (pregunta.usuario and not ID_WEB.match(pregunta.usuario)):
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

    Se guardan como un hash de 32 caracteres hexadecimales, así el número no queda escrito en la base de datos. Como
    cualquiera que sepa el número puede calcularlos, nunca tienen forma de uuid4: las rutas del navegador los rechazan.
    """
    digitos = "".join(c for c in telefono if c.isdigit())
    return _id_de_telefono(f"hilo:{digitos}"), _id_de_telefono(f"usuario:{digitos}")


def _id_de_telefono(semilla: str) -> str:
    """El hash de siempre; si por azar sale con forma de uuid4 (1 de cada 64), se le cambia el carácter que la marca."""
    identificador = hashlib.sha256(semilla.encode()).hexdigest()[:32]
    return identificador[:12] + "0" + identificador[13:] if ID_WEB.match(identificador) else identificador


def _exigir_clave_del_chat(x_api_key: str | None, peticion: Request) -> None:
    """Con `CHAT_TOKEN` en el servidor, deja pasar solo con el encabezado `X-Api-Key` igual a ella. Sin la variable, `/chat`
    atiende únicamente llamadas directas: lo que llega por un túnel o un proxy se rechaza, porque bastaría un número ajeno."""
    esperado = os.environ.get("CHAT_TOKEN")
    if esperado:
        if not secrets.compare_digest((x_api_key or "").encode(), esperado.encode()):
            raise HTTPException(status_code=401, detail="No autorizado")
    elif "cf-connecting-ip" in peticion.headers or "x-forwarded-for" in peticion.headers:
        raise HTTPException(status_code=401, detail="No autorizado")


@app.post("/chat")
def chat_por_telefono(
    entrada: MensajeEntrante, peticion: Request, x_api_key: str | None = Header(default=None)
) -> RespuestaDelAgente:
    """Un turno del agente, sin streaming: recibe mensaje y teléfono y devuelve la respuesta en JSON.

    Con `CHAT_TOKEN` definida en el servidor exige el encabezado `X-Api-Key`; sin ella no atiende lo que llega por un túnel. El webhook de WhatsApp no pasa por aquí: se protege con la firma de Meta.

    Si el modelo o una herramienta fallan responde con un mensaje cortés (`ok` en falso) en vez de un error, porque quien llama
    (WhatsApp) tiene que poder reenviar algo al cliente.
    """
    _exigir_clave_del_chat(x_api_key, peticion)
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
        if pide_la_fuente(mensaje) and not pendiente_de_aprobacion(hilo):  # la contesta el programa con lo guardado, sin llamar al modelo
            textos = {f["chunk_id"]: f["texto"] for f in cargar_fragmentos()}
            texto = texto_de_fuentes(historial_visible(hilo), textos)
            actividad.registrar(canal, telefono, mensaje, "respondido", segundos=time.monotonic() - inicio, costo=0.0, respuesta=texto)
            return RespuestaDelAgente(respuesta=texto, herramientas=[])
        # Lo trivial no despierta al agente, salvo que haya un reclamo pendiente o una decisión sin entregar.
        atajo = respuesta_rapida(mensaje)
        if atajo and (pendiente_de_aprobacion(hilo) or aprobaciones.hay_sin_entregar(hilo)):
            atajo = None
        if atajo:
            actividad.registrar(canal, telefono, mensaje, "respondido", segundos=time.monotonic() - inicio, costo=0.0, respuesta=atajo.texto)
            return RespuestaDelAgente(respuesta=atajo.texto, herramientas=[])
        texto, llamadas = conversar(mensaje, hilo, usuario=usuario)
    except Exception:  # el detalle va al registro; al cliente no se le filtra nada interno
        log.exception("falló el turno del hilo %s", hilo)
        actividad.registrar(canal, telefono, mensaje, "error", segundos=time.monotonic() - inicio)
        return RespuestaDelAgente(respuesta=MENSAJE_DE_FALLO, herramientas=[], ok=False)
    pendiente = pendiente_de_aprobacion(hilo)
    nota = "" if pendiente else aviso_de_datos_dudosos(hilo, texto)  # un dato sin respaldo en la respuesta queda avisado (por WhatsApp no hay otro lugar)
    texto += nota
    if pendiente:
        log.info("pendiente de aprobación en el hilo %s: %s", hilo[:8], pendiente["herramienta"])
        aprobaciones.registrar(hilo, usuario, pendiente, canal, telefono)
    else:
        aprobaciones.quitar(hilo)
        if previo := aprobaciones.tomar_sin_entregar(hilo):  # la decisión que no se le pudo enviar va con esta respuesta
            texto = f"{previo}\n\n{texto}"
    herramientas = [ll["herramienta"] for ll in llamadas]
    estado = "pendiente de aprobación" if pendiente else "respondido"
    actividad.registrar(
        canal, telefono, mensaje, estado, herramientas, time.monotonic() - inicio, nota=bool(nota), costo=costo_del_turno(hilo),
        respuesta=texto, fuentes=fuentes_del_turno(hilo) if "buscar_en_base" in herramientas else [],
    )
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
    anotado = aprobaciones.por_hilo(hilo)
    return _resolver(hilo, usuario, telefono, anotado.canal if anotado else "chat", decision, mensaje)


def _resolver(hilo: str, usuario: str, telefono: str | None, canal: str, decision: str, mensaje: str | None = None) -> dict:
    """Aplica la decisión sobre una conversación pausada y le hace llegar el resultado al cliente.

    Si no se le puede enviar (chat web, o el envío falla), el resultado queda guardado: el chat web lo muestra solo al leer el
    historial y, en los demás canales, sale con su siguiente mensaje.
    """
    if not aprobaciones.empezar_decision(hilo):
        raise HTTPException(status_code=409, detail="Esa decisión ya se está aplicando")
    try:
        anotado = aprobaciones.por_hilo(hilo)
        if not pendiente_de_aprobacion(hilo):
            aprobaciones.quitar(hilo)
            raise HTTPException(status_code=404, detail="No hay nada pendiente de aprobación en esa conversación")
        texto, _ = resolver_aprobacion(hilo, decision, usuario=usuario, **({"mensaje": mensaje} if mensaje else {}))
        aprobaciones.quitar(hilo)
        if anotado and (otro := pendiente_de_aprobacion(hilo)):  # al seguir, el agente pidió aprobar algo más
            aprobaciones.registrar(hilo, usuario, otro, canal, telefono)
        avisado = bool(telefono) and _avisar_al_cliente(telefono, texto, canal)
        if anotado and not avisado:
            aprobaciones.guardar_sin_entregar(hilo, texto, canal)
        actividad.registrar("aprobación", telefono or hilo, f"decisión: {decision}", "aprobación")
        return {"decision": decision, "respuesta": texto, "avisado_por_whatsapp": avisado}
    finally:
        aprobaciones.terminar_decision(hilo)


def _avisar_al_cliente(telefono: str, texto: str, canal: str) -> bool:
    """Por el mismo WhatsApp por el que escribió: OpenClaw (entra por POST /chat) o la API de Meta (entra por el webhook)."""
    if not canal.startswith("whatsapp") and avisos_openclaw.activos():
        return avisos_openclaw.enviar(telefono, texto)
    return enviar_texto(telefono, texto)


@app.get("/api/pendientes")
def pendientes(x_aprobador: str | None = Header(default=None)) -> dict:
    """Lo que espera la decisión de una persona. Trae lo que pidió el cliente (por eso pide el token), pero no su teléfono."""
    _exigir_aprobador(x_aprobador)
    ahora = time.time()
    return {
        "avisos_openclaw": avisos_openclaw.activos(),
        "pendientes": [
            {
                "codigo": p.codigo,
                "herramienta": p.herramienta,
                "args": p.args,
                "canal": p.canal,
                "quien": actividad.quien(p.telefono or p.hilo),
                "hace_s": int(ahora - p.desde),
            }
            for p in aprobaciones.todos()
        ],
    }


class DecisionDelPanel(BaseModel):
    """Cuerpo de POST /api/pendientes/{código}."""

    decision: Literal["aprobar", "rechazar"]


@app.post("/api/pendientes/{codigo}")
def decidir_pendiente(codigo: str, cuerpo: DecisionDelPanel, x_aprobador: str | None = Header(default=None)) -> dict:
    """Una persona de Celsia aprueba o rechaza desde el panel uno de los pendientes de la lista."""
    _exigir_aprobador(x_aprobador)
    p = aprobaciones.por_codigo(codigo)
    if not p:
        raise HTTPException(status_code=404, detail="Ese pendiente ya no está en la lista")
    return {"canal": p.canal, **_resolver(p.hilo, p.usuario, p.telefono, p.canal, cuerpo.decision)}


PANEL = Path(__file__).with_name("panel.html")
QR_WHATSAPP = Path(__file__).resolve().parent.parent / "assets" / "whatsapp_qr.png"


@app.get("/panel", response_class=HTMLResponse)
def panel() -> str:
    """La página del panel en vivo. No lleva datos: los pide a /api/actividad con el token que se escribe en la pantalla."""
    return PANEL.read_text(encoding="utf-8")


@app.get("/qr-whatsapp.png", include_in_schema=False)
def qr_whatsapp() -> FileResponse:
    """El QR de WhatsApp del bot que muestran el chat web y el panel en vivo.

    El archivo lo deja `make qr-whatsapp ARGS="+57... --app"`; si falta, se avisa en vez de devolver un hueco.
    """
    if not QR_WHATSAPP.is_file():
        raise HTTPException(status_code=404, detail="Falta assets/whatsapp_qr.png: genéralo con make qr-whatsapp ARGS=\"+57... --app\"")
    return FileResponse(QR_WHATSAPP, media_type="image/png")


@app.get("/api/actividad")
def lo_que_hizo_el_agente(desde: int = Query(default=0, ge=0), x_aprobador: str | None = Header(default=None)) -> dict:
    """Los turnos recientes del agente (respuesta, fuentes, herramientas, tiempo, estado), de más viejo a más nuevo, y qué herramientas distintas
    se han usado. Muestra lo que escriben los clientes, por eso pide el token."""
    _exigir_aprobador(x_aprobador)
    filas = actividad.recientes(desde)
    return {
        "filas": filas,
        "ultimo": filas[-1]["n"] if filas else desde,
        "usadas": actividad.herramientas_usadas(),
        "total_herramientas": len(HERRAMIENTAS),
    }


def _funciona(prueba) -> bool:
    """Si una comprobación termina bien; cualquier fallo cuenta como apagado (el detalle va al registro)."""
    try:
        return bool(prueba())
    except Exception:  # noqa: BLE001
        log.warning("falló una comprobación del semáforo", exc_info=True)
        return False


@app.get("/api/semaforo")
def semaforo(x_aprobador: str | None = Header(default=None)) -> dict:
    """Las luces del panel: comprueba de verdad que la búsqueda y la memoria contestan y que el puente de WhatsApp de este equipo responde.

    No llama al modelo. El puente encendido no garantiza que el celular siga vinculado.
    """
    _exigir_aprobador(x_aprobador)
    luces = [
        ("Asistente", True),
        ("Búsqueda", _funciona(lambda: almacen_vectorial() != "ninguno")),
        ("Memoria", _funciona(lambda: almacen_compartido().search(("semaforo",), limit=1) is not None)),
        ("Puente de WhatsApp", _funciona(lambda: _estado_openclaw()["conectado"])),
    ]
    return {"luces": [{"nombre": nombre, "encendida": encendida} for nombre, encendida in luces]}


@app.get("/api/hilos/{hilo}/estado")
def estado_del_hilo(hilo: str) -> dict:
    """Si la conversación espera la decisión de una persona. No expone los argumentos ni consume la decisión.

    Sigue «pendiente» mientras la decisión se está aplicando: la respuesta para el cliente todavía no está lista.
    """
    if not ID_WEB.match(hilo):
        raise HTTPException(status_code=422, detail="Identificador de hilo inválido")
    pendiente = pendiente_de_aprobacion(hilo)
    if not pendiente and aprobaciones.decidiendo(hilo):
        anotado = aprobaciones.por_hilo(hilo)
        pendiente = {"herramienta": anotado.herramienta if anotado else ""}
    return {"pendiente": {"herramienta": pendiente["herramienta"]} if pendiente else None}


@app.get("/api/hilos/{hilo}/mensajes")
def mensajes(hilo: str) -> dict:
    """La conversación guardada de un hilo, para recuperarla al recargar la página o mostrar lo que decidió una persona."""
    if not ID_WEB.match(hilo):
        raise HTTPException(status_code=422, detail="Identificador de hilo inválido")
    if not aprobaciones.decidiendo(hilo):  # antes de leer: lo que se descarta aquí ya está en el historial que sale
        aprobaciones.entregada_en_la_web(hilo)
    return {"hilo": hilo, "mensajes": historial_visible(hilo)}


def _usuario_valido(usuario: str) -> str:
    """Devuelve el identificador del cliente o responde 422 si no es un uuid4 hexadecimal."""
    if not ID_WEB.match(usuario):
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


def _responder_comando(telefono: str, texto: str) -> bool:
    """Atiende `/nuevo` y los saludos (menú con botones) sin llamar al modelo. Devuelve True si el mensaje era uno de ellos."""
    clave = normalizar(texto)
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
    for fallo in estados_fallidos(carga if isinstance(carga, dict) else {}):
        log.error("Meta no pudo entregar un mensaje (%s)", fallo)
    nuevos = 0
    for m in mensajes_entrantes(carga if isinstance(carga, dict) else {}):
        repetido = _ya_atendido(m["id"])
        # Solo el final del identificador (no el teléfono ni el texto): sirve para distinguir un reintento de Meta de un mensaje nuevo
        log.info("mensaje de WhatsApp ...%s (tipo %s), repetido: %s", m["id"][-8:], m["tipo"] or "?", "sí" if repetido else "no")
        if repetido:
            continue
        # Allowlist E.164: si está definida, un número ajeno no llega ni al agente ni al modelo (el aprobador es la excepción)
        if not autorizado(m["telefono"]) and not _es_el_aprobador(m["telefono"]):
            log.warning("mensaje de WhatsApp de un número fuera de la lista de autorizados: se ignora")
            continue
        nuevos += 1
        segundo_plano.add_task(atender_mensaje_de_whatsapp, m["telefono"], m["tipo"], m["texto"], m.get("audio", ""), m["id"])
    return {"ok": True, "mensajes": nuevos}


FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "dist"


class _PaginaUnica(StaticFiles):
    """Archivos estáticos con respaldo a `index.html`: el chat cambia su dirección a `/c/<hilo>` y, si la persona recarga, el servidor debe devolver la misma página. Lo que empieza por `api/` sigue dando 404."""

    async def get_response(self, path: str, scope):
        try:
            respuesta = await super().get_response(path, scope)
        except ErrorHTTP as e:
            if e.status_code != 404 or path.replace("\\", "/").startswith("api/"):
                raise
            return await super().get_response("index.html", scope)
        return respuesta


def montar_frontend(aplicacion: FastAPI, carpeta: Path = FRONTEND) -> bool:
    """Sirve el chat web (el frontend compilado) desde la misma dirección de la API, para que el público lo abra con un QR.

    Es el respaldo de WhatsApp: no tiene el límite de 5 destinatarios del número de prueba de Meta. El frontend llama a `/api/...` con rutas
    relativas, así que desde la misma dirección no necesita CORS. Se monta en «/» **al final del archivo**, después de todas las rutas, para
    no taparlas. No se monta si falta `index.html` (hay que correr `make chat-web`) o si `SERVIR_FRONTEND=0`.
    """
    if os.environ.get("SERVIR_FRONTEND", "1") == "0" or not (carpeta / "index.html").is_file():
        return False
    aplicacion.mount("/", _PaginaUnica(directory=carpeta, html=True), name="chat-web")
    return True


montar_frontend(app)
