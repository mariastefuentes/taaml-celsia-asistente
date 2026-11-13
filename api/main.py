"""API del agente de Celsia: el frontend habla con esto por HTTP y nunca llama al modelo directamente.

Endpoints:
  GET  /api/salud                    estado y modelo del agente
  POST /api/chat                     un turno de conversación; responde por streaming (Server-Sent Events)
  GET  /api/hilos/{hilo}/mensajes    la conversación guardada, para recuperarla al recargar la página
Uso:  uv run uvicorn api.main:app --reload --port 8000
"""
import json
import logging
import re
from collections.abc import Iterator
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from taaml.agente import MODELO_AGENTE, conversar_en_vivo, historial_visible

log = logging.getLogger("taaml.api")
ORIGENES = ["http://localhost:5173", "http://127.0.0.1:5173"]  # el servidor de desarrollo del frontend
HILO = re.compile(r"^[0-9a-f]{32}$")  # los hilos son uuid4 en hexadecimal: no se acepta otra cosa como id

app = FastAPI(title="Agente Celsia", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=ORIGENES, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


class Pregunta(BaseModel):
    mensaje: str = Field(min_length=1, max_length=1000, description="Lo que escribe el cliente")
    hilo: str | None = Field(default=None, description="Identificador de la conversación; si falta se crea uno nuevo")


def _evento(tipo: str, datos: dict) -> str:
    return f"event: {tipo}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n"


def _turno(mensaje: str, hilo: str) -> Iterator[str]:
    yield _evento("hilo", {"hilo": hilo})
    try:
        for e in conversar_en_vivo(mensaje, hilo):
            yield _evento(e["tipo"], {k: v for k, v in e.items() if k != "tipo"})
    except Exception:  # el detalle va al registro del servidor; el cliente recibe un mensaje que no filtra nada interno
        log.exception("falló el turno del hilo %s", hilo)
        yield _evento("error", {"mensaje": "No pude responder en este momento. Intenta de nuevo; si sigue fallando, llama a la línea 01 8000 112 115."})


@app.get("/api/salud")
def salud() -> dict:
    return {"estado": "ok", "modelo": MODELO_AGENTE}


@app.post("/api/chat")
def chat(pregunta: Pregunta) -> StreamingResponse:
    hilo = pregunta.hilo or uuid4().hex
    if not HILO.match(hilo):
        raise HTTPException(status_code=422, detail="Identificador de hilo inválido")
    return StreamingResponse(_turno(pregunta.mensaje, hilo), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/hilos/{hilo}/mensajes")
def mensajes(hilo: str) -> dict:
    if not HILO.match(hilo):
        raise HTTPException(status_code=422, detail="Identificador de hilo inválido")
    return {"hilo": hilo, "mensajes": historial_visible(hilo)}
