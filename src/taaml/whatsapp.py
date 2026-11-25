"""Conexión con la API Cloud de WhatsApp (Meta): verificar la firma, leer los mensajes que llegan y enviar la respuesta.

Meta avisa de cada mensaje con un POST a nuestro webhook. Este módulo no sabe nada del agente: solo traduce entre el formato de
Meta y el nuestro, así se prueba sin red ni claves. Las claves viven en el `.env` del servidor:
  WHATSAPP_VERIFY_TOKEN     palabra que inventamos y que Meta nos devuelve al registrar el webhook (verificación GET)
  WHATSAPP_APP_SECRET       secreto de la app de Meta: con él se comprueba la firma de cada aviso
  WHATSAPP_TOKEN            token de acceso para enviar mensajes
  WHATSAPP_PHONE_NUMBER_ID  identificador del número de WhatsApp Business desde el que se responde
  WHATSAPP_API_VERSION      versión de la API de Graph (opcional; por defecto la de VERSION_API)
  WHATSAPP_ALLOWLIST        números autorizados (E.164, separados por comas); `*` o sin definir deja el canal abierto para el público
  APROBADOR_WHATSAPP        (opcional) teléfono de la persona de Celsia que aprueba reclamos con botones; sin él solo funciona POST /aprobar
"""

import hashlib
import hmac
import logging
import os
import re
from typing import Any
from urllib.parse import quote

import requests

log = logging.getLogger("taaml.whatsapp")
VERSION_API = "v23.0"  # la documentación de Meta muestra v23.0 y v27.0; se cambia con WHATSAPP_API_VERSION sin tocar código
LIMITE_TEXTO = 4096  # WhatsApp rechaza mensajes de texto más largos
TIEMPO_MAXIMO_ENVIO = 15
TEXTO_NO_SOPORTADO = "Por ahora solo puedo leer mensajes de texto. Escríbeme tu pregunta y con gusto te ayudo."


def firma_valida(cuerpo: bytes, cabecera: str | None, secreto: str) -> bool:
    """¿El aviso lo firmó Meta? La cabecera `X-Hub-Signature-256` trae `sha256=` y el HMAC-SHA256 del cuerpo exacto con el secreto de la app."""
    if not cabecera or not secreto or not cabecera.startswith("sha256="):
        return False
    esperada = hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, cabecera.removeprefix("sha256="))


def mensajes_entrantes(carga: dict[str, Any]) -> list[dict[str, str]]:
    """Los mensajes de clientes que trae un aviso de Meta: `{id, telefono, tipo, texto}`.

    Los avisos de estado (enviado, entregado, leído) llegan por el mismo camino pero sin `messages`: se ignoran.
    """
    salida = []
    for entrada in carga.get("entry", []) or []:
        for cambio in entrada.get("changes", []) or []:
            for m in (cambio.get("value") or {}).get("messages", []) or []:
                if not m.get("id") or not m.get("from"):
                    continue
                tipo = m.get("type", "")
                texto = (m.get("text") or {}).get("body", "") if tipo == "text" else ""
                if tipo == "interactive":  # la respuesta a un botón trae su identificador: es lo que `texto` guarda
                    texto = ((m.get("interactive") or {}).get("button_reply") or {}).get("id", "")
                audio = (m.get("audio") or {}).get("id", "") if tipo == "audio" else ""
                salida.append({"id": m["id"], "telefono": m["from"], "tipo": tipo, "texto": texto, "audio": audio})
    return salida


def estados_fallidos(carga: dict[str, Any]) -> list[str]:
    """Los avisos de estado «failed» de Meta, como «código: título»: dicen por qué un mensaje que Meta aceptó no llegó al cliente (sin teléfono ni texto)."""
    salida = []
    for entrada in carga.get("entry", []) or []:
        for cambio in entrada.get("changes", []) or []:
            for estado in (cambio.get("value") or {}).get("statuses", []) or []:
                if estado.get("status") == "failed":
                    for error in estado.get("errors", []) or [{}]:
                        salida.append(f"{error.get('code', '?')}: {error.get('title') or error.get('message', 'sin detalle')}")
    return salida


def configurado() -> bool:
    """¿Hay con qué enviar mensajes? Sin token y sin número, el servidor responde por la API pero no por WhatsApp."""
    return bool(os.environ.get("WHATSAPP_TOKEN") and os.environ.get("WHATSAPP_PHONE_NUMBER_ID"))


LISTA_ABIERTA = "*"  # modo público de la demo: cualquier número puede escribir (el límite por teléfono sigue aplicando)


def numeros_autorizados() -> set[str]:
    """Los teléfonos de `WHATSAPP_ALLOWLIST`, en dígitos (Meta manda `573001112233` sin «+»).

    Se acepta la lista separada por comas, punto y coma o espacios; los «+» y los espacios de cada número se ignoran.
    Con `*` devuelve el conjunto vacío: el canal está abierto y `/api/salud` lo informa como «abierta».
    """
    crudo = os.environ.get("WHATSAPP_ALLOWLIST", "")
    numeros = (re.sub(r"\D", "", n) for n in re.split(r"[,;]+", crudo))
    return {n for n in numeros if n}


def autorizado(telefono: str) -> bool:
    """¿Este teléfono puede usar el bot?

    Sin `WHATSAPP_ALLOWLIST` o con `*` queda abierto: es el modo público del auditorio (el límite por teléfono protege la cuota).
    Con una lista de números solo pasan esos; una lista que no trae ningún número válido **cierra** el canal en lugar de abrirlo.
    """
    crudo = os.environ.get("WHATSAPP_ALLOWLIST", "").strip()
    if not crudo or crudo == LISTA_ABIERTA:
        return True
    return re.sub(r"\D", "", telefono) in numeros_autorizados()


def enlace_wa_me(numero: str, saludo: str = "Hola") -> str:
    """Enlace `wa.me` del número del bot, con un saludo precargado, para el QR del auditorio.

    El número va con indicativo (`+57…`); se aceptan espacios, guiones y paréntesis. Falla si no parece E.164, en vez de adivinar.
    """
    digitos = re.sub(r"\D", "", numero or "")
    if not 8 <= len(digitos) <= 15:
        raise ValueError("El número del bot debe ir con indicativo y entre 8 y 15 dígitos (+57…).")
    return f"https://wa.me/{digitos}" + (f"?text={quote(saludo)}" if saludo else "")


def enviar_texto(telefono: str, texto: str) -> bool:
    """Envía un mensaje de texto por la API Cloud. Devuelve si Meta lo aceptó; un fallo se registra y no rompe a quien llama.

    Que Meta acepte la petición no dice que el cliente ya lo recibió: eso llega después como aviso de estado.
    """
    if not configurado():
        log.warning("WhatsApp sin configurar (falta WHATSAPP_TOKEN o WHATSAPP_PHONE_NUMBER_ID): no se envió la respuesta")
        return False
    version = os.environ.get("WHATSAPP_API_VERSION") or VERSION_API
    url = f"https://graph.facebook.com/{version}/{os.environ['WHATSAPP_PHONE_NUMBER_ID']}/messages"
    cuerpo = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": telefono,
        "type": "text",
        "text": {"body": texto[:LIMITE_TEXTO]},
    }
    try:
        r = requests.post(
            url,
            json=cuerpo,
            headers={"Authorization": f"Bearer {os.environ['WHATSAPP_TOKEN']}"},
            timeout=TIEMPO_MAXIMO_ENVIO,
        )
    except requests.RequestException:
        log.exception("no se pudo contactar a Meta para enviar la respuesta")
        return False
    if not r.ok:
        try:
            codigo = r.json().get("error", {}).get("code")
        except ValueError:
            codigo = None
        log.error("Meta rechazó el envío (HTTP %s, código %s)", r.status_code, codigo)  # sin el número ni el texto del cliente
        return False
    return True


def _cabeceras() -> dict[str, str]:
    return {"Authorization": f"Bearer {os.environ['WHATSAPP_TOKEN']}"}


def _url_graph(ruta: str) -> str:
    return f"https://graph.facebook.com/{os.environ.get('WHATSAPP_API_VERSION') or VERSION_API}/{ruta}"


def enviar_botones(telefono: str, texto: str, botones: list[tuple[str, str]]) -> bool:
    """Envía un mensaje con hasta 3 botones de respuesta rápida: cada botón es `(identificador, rótulo)`.

    Meta exige rótulos de 20 caracteres como máximo. Solo llega si la persona le escribió al número en las últimas 24 horas
    (fuera de esa ventana Meta pide una plantilla aprobada); si no llega, se registra y quien llama sigue con otro camino.
    """
    if not configurado() or not 1 <= len(botones) <= 3:
        return False
    cuerpo = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": texto[:1024]},
            "action": {"buttons": [{"type": "reply", "reply": {"id": i, "title": rotulo[:20]}} for i, rotulo in botones]},
        },
    }
    try:
        r = requests.post(
            _url_graph(f"{os.environ['WHATSAPP_PHONE_NUMBER_ID']}/messages"),
            json=cuerpo,
            headers=_cabeceras(),
            timeout=TIEMPO_MAXIMO_ENVIO,
        )
    except requests.RequestException:
        log.exception("no se pudo contactar a Meta para enviar los botones")
        return False
    if not r.ok:
        log.error("Meta rechazó los botones (HTTP %s)", r.status_code)  # sin el número ni el texto
        return False
    return True


def marcar_leido(id_mensaje: str) -> bool:
    """Marca el mensaje como leído y muestra «escribiendo…» al cliente mientras el agente piensa (5 a 25 s).

    Es solo cortesía: si Meta no lo acepta no pasa nada y se sigue. El indicador dura hasta 25 s o hasta que llegue la respuesta.
    """
    if not configurado() or not id_mensaje:
        return False
    cuerpo = {"messaging_product": "whatsapp", "status": "read", "message_id": id_mensaje, "typing_indicator": {"type": "text"}}
    try:
        r = requests.post(
            _url_graph(f"{os.environ['WHATSAPP_PHONE_NUMBER_ID']}/messages"), json=cuerpo, headers=_cabeceras(), timeout=TIEMPO_MAXIMO_ENVIO
        )
    except requests.RequestException:
        log.warning("no se pudo marcar como leído")
        return False
    return r.ok


def descargar_audio(id_audio: str) -> tuple[bytes, str] | None:
    """Baja una nota de voz de Meta: primero pide la dirección del archivo y luego lo descarga. Devuelve `(bytes, tipo MIME)` o None."""
    if not configurado():
        return None
    try:
        info = requests.get(_url_graph(id_audio), headers=_cabeceras(), timeout=TIEMPO_MAXIMO_ENVIO)
        if not info.ok:
            return None
        datos = info.json()
        archivo = requests.get(datos["url"], headers=_cabeceras(), timeout=TIEMPO_MAXIMO_ENVIO)
    except (requests.RequestException, ValueError, KeyError):
        log.exception("no se pudo descargar la nota de voz")
        return None
    return (archivo.content, datos.get("mime_type", "audio/ogg")) if archivo.ok else None
