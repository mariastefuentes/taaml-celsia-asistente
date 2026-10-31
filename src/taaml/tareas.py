"""Las tres tareas del asistente con LangChain: Resumen, FAQ y Q&A.

Las tres usan el mismo modelo (Gemini por defecto, temperature 0.0 y top_p 0.1; DeepSeek si el nombre empieza por «deepseek» u Ollama local si empieza por «ollama:») y prompts versionados en prompts/.
Resumen y FAQ devuelven salida estructurada (Pydantic); Q&A devuelve texto.
"""
import json
import os
import urllib.request
from datetime import date
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from taaml.base import cargar_base
from taaml.recuperacion import formatear_contexto, recuperar
from taaml.prompts import PARAMETROS_MODELO, construir_mensaje_usuario, construir_prompt_sistema, leer_prompt

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
# Trazabilidad opcional (LangSmith): solo se activa si hay una clave en el .env; sin clave no se envía nada a ningún servicio.
if os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY"):
    for _variable in ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"):
        os.environ.setdefault(_variable, "true")
    os.environ.setdefault("LANGSMITH_PROJECT", "taaml-celsia")
    os.environ.setdefault("LANGCHAIN_PROJECT", "taaml-celsia")
MODELO_POR_DEFECTO = "gemini-3.5-flash"  # el que se evaluó; el 3.6 ignora temperature y top_p (regla del proyecto)
URL_DEEPSEEK = "https://api.deepseek.com"  # formato OpenAI; el modelo se elige por nombre: «deepseek-flash», «deepseek-v4-pro»
OLLAMA_TAGS = "http://localhost:11434/api/tags"  # para resolver «llama3.2» al tag que de verdad está instalado («llama3.2:3b»)
MAX_TOKENS_SALIDA = 8192  # el "pensamiento" del modelo cuenta aquí: con 2048 el FAQ se cortó (gastó 1.967 pensando)
TIEMPO_MAXIMO_LOCAL = 300  # segundos: el modelo local corre en CPU y con 12 fragmentos puede tardar minutos; mejor un error claro que una demo colgada
VENTANA_CONTEXTO_LOCAL = 8192  # Ollama usa 4096 por defecto y recortaría el prompt (12 fragmentos son ~4.400 tokens)
MAX_CARACTERES_DOCUMENTO = 12_000  # Resumen y FAQ reciben como máximo esto de un documento (los hay de más de 30.000)


class ResumenDocumento(BaseModel):
    resumen: str = Field(description="Resumen para el cliente, máximo 5 líneas")
    puntos_clave: list[str] = Field(description="De 3 a 5 puntos clave cortos")
    canales: list[str] = Field(default_factory=list, description="Teléfonos, enlaces o canales oficiales que trae el documento")


class PreguntaFrecuente(BaseModel):
    pregunta: str
    respuesta: str


class FaqDocumento(BaseModel):
    preguntas: list[PreguntaFrecuente]


def _tag_instalado(nombre: str) -> str:
    """Resuelve el nombre de un modelo de Ollama al tag que está instalado.

    `ollama run llama3.2` funciona porque Ollama completa el tag, pero la API `/api/chat` es
    literal: `llama3.2` devuelve 404 si solo existe `llama3.2:3b`. Aquí se consulta `/api/tags`
    y se devuelve el tag real; si Ollama no responde o el modelo no está, se deja el nombre tal cual.
    """
    try:
        with urllib.request.urlopen(OLLAMA_TAGS, timeout=3) as respuesta:
            etiquetas = [m["name"] for m in json.loads(respuesta.read().decode("utf-8")).get("models", [])]
    except Exception:  # noqa: BLE001  Ollama apagado: que falle más adelante con un error entendible
        return nombre
    if nombre in etiquetas:
        return nombre
    for candidato in (f"{nombre}:latest", *sorted(e for e in etiquetas if e.startswith(f"{nombre}:"))):
        if candidato in etiquetas:
            return candidato
    return nombre


@lru_cache(maxsize=4)
def clave_faltante(modelo: str = MODELO_POR_DEFECTO) -> str | None:
    """La variable de entorno con la clave que falta para responder con `modelo`; None si la configuración alcanza (los modelos locales no la usan)."""
    if modelo.startswith("ollama:"):
        return None
    clave = "DEEPSEEK_API_KEY" if modelo.startswith("deepseek") else "GOOGLE_API_KEY"
    return None if os.environ.get(clave) else clave


def obtener_modelo(nombre: str = MODELO_POR_DEFECTO) -> BaseChatModel:
    """Gemini por defecto; si el nombre empieza por «deepseek» usa DeepSeek con el razonamiento apagado.

    DeepSeek solo respeta temperature con el razonamiento apagado y deja top_p fijo en 1,0 (lo dice su documentación).
    """
    if nombre.startswith("ollama:"):  # modelo local de respaldo (spec 003): sin clave y sin costo
        from langchain_ollama import ChatOllama
        return ChatOllama(model=_tag_instalado(nombre.removeprefix("ollama:")), temperature=PARAMETROS_MODELO["temperature"], top_p=PARAMETROS_MODELO["top_p"], num_ctx=VENTANA_CONTEXTO_LOCAL,
                          client_kwargs={"timeout": TIEMPO_MAXIMO_LOCAL})
    if nombre.startswith("deepseek"):
        if not os.environ.get("DEEPSEEK_API_KEY"):
            raise RuntimeError("Falta DEEPSEEK_API_KEY en el archivo .env")
        return ChatOpenAI(model=nombre, base_url=URL_DEEPSEEK, api_key=os.environ["DEEPSEEK_API_KEY"],
                          temperature=PARAMETROS_MODELO["temperature"], top_p=PARAMETROS_MODELO["top_p"], max_tokens=MAX_TOKENS_SALIDA, max_retries=2,
                          extra_body={"thinking": {"type": "disabled"}})
    if not os.environ.get("GOOGLE_API_KEY"):
        raise RuntimeError("Falta GOOGLE_API_KEY en el archivo .env")
    return ChatGoogleGenerativeAI(model=nombre, temperature=PARAMETROS_MODELO["temperature"],
                                  top_p=PARAMETROS_MODELO["top_p"], max_output_tokens=MAX_TOKENS_SALIDA, max_retries=2)


def _estructurado(modelo: str, esquema: type[BaseModel]):
    """Modelo con salida estructurada; DeepSeek y Ollama no usan el modo json_schema de Gemini, así que usan llamada a función."""
    llm = obtener_modelo(modelo)
    return llm.with_structured_output(esquema, method="function_calling") if modelo.startswith(("deepseek", "ollama:")) else llm.with_structured_output(esquema)


def responder_con_fuentes(pregunta: str, base: str = "rag", modelo: str = MODELO_POR_DEFECTO,
                          reordenar: bool = False) -> tuple[str, list[dict], dict]:
    """Q&A: responde con la base de conocimiento y devuelve también los fragmentos usados (vacío si `base` no es «rag»).

    base «rag»: solo los fragmentos más relevantes a la pregunta (recomendado). «completa» y «compacta» pegan la base entera.
    reordenar: recupera más candidatos y un modelo elige los mejores (una llamada más; ver reordenar.py).

    Devuelve `(respuesta, fragmentos, métricas)`: las métricas de la recuperación (cuántos fragmentos, con qué
    método y el tiempo en ms) solo se miden cuando la pregunta se busca en la base («rag»); si la recuperación
    falla, se propaga el error para que el respaldo y el mensaje al usuario lo manejen.
    """
    if base == "rag" and reordenar:
        from taaml.reordenar import buscar_reordenado_con_metricas, modelo_reordenador  # import tardío: reordenar usa obtener_modelo de este módulo
        fragmentos, metricas = buscar_reordenado_con_metricas(pregunta, modelo=modelo_reordenador(modelo))
    elif base == "rag":
        fragmentos, metricas = recuperar(pregunta)
    else:
        fragmentos, metricas = [], {"encontrados": 0, "metodo": base, "tiempo_ms": 0}
    if metricas.get("error") is not None:
        raise RuntimeError(metricas["error"])
    contexto = formatear_contexto(fragmentos) if base == "rag" else cargar_base(base)
    mensajes = [SystemMessage(construir_prompt_sistema(contexto)), HumanMessage(construir_mensaje_usuario(pregunta))]
    config = {"run_name": "qa_celsia", "tags": ["rag", base], "metadata": {"fragmentos": [f["chunk_id"] for f in fragmentos], "reordenar": reordenar}}
    return obtener_modelo(modelo).invoke(mensajes, config=config).text.strip(), fragmentos, metricas


def responder(pregunta: str, base: str = "rag", modelo: str = MODELO_POR_DEFECTO, reordenar: bool = False) -> str:
    """Q&A: responde la pregunta de un cliente usando solo la base de conocimiento."""
    return responder_con_fuentes(pregunta, base, modelo, reordenar)[0]


def _preparar(plantilla: str, documento: str, publicado: str) -> str:
    return (leer_prompt(plantilla).replace("{documento}", documento[:MAX_CARACTERES_DOCUMENTO])
            .replace("{hoy}", date.today().isoformat()).replace("{publicado}", publicado or "no disponible"))


def resumir(documento: str, publicado: str = "", modelo: str = MODELO_POR_DEFECTO) -> ResumenDocumento:
    """Resumen: sintetiza una página oficial para un cliente."""
    prompt = _preparar("v2_resumen.md", documento, publicado)
    return _estructurado(modelo, ResumenDocumento).invoke([HumanMessage(prompt)], config={"run_name": "resumen_celsia", "tags": ["resumen"]})


def generar_faq(documento: str, cantidad: int = 5, publicado: str = "", modelo: str = MODELO_POR_DEFECTO) -> FaqDocumento:
    """FAQ: arma `cantidad` preguntas frecuentes con su respuesta a partir de una página oficial."""
    prompt = _preparar("v2_faq.md", documento, publicado).replace("{n}", str(cantidad))
    return _estructurado(modelo, FaqDocumento).invoke([HumanMessage(prompt)], config={"run_name": "faq_celsia", "tags": ["faq"]})
