"""Conexión con la API Cloud de WhatsApp (Meta): verificar la firma, leer los mensajes que llegan y enviar la respuesta.

Meta avisa de cada mensaje con un POST a nuestro webhook. Este módulo no sabe nada del agente: solo traduce entre el formato de
Meta y el nuestro, así se prueba sin red ni claves. Las claves viven en el `.env` del servidor:
  WHATSAPP_VERIFY_TOKEN     palabra que inventamos y que Meta nos devuelve al registrar el webhook (verificación GET)
  WHATSAPP_APP_SECRET       secreto de la app de Meta: con él se comprueba la firma de cada aviso
  WHATSAPP_TOKEN            token de acceso para enviar mensajes
  WHATSAPP_PHONE_NUMBER_ID  identificador del número de WhatsApp Business desde el que se responde
  WHATSAPP_API_VERSION      versión de la API de Graph (opcional; por defecto la de VERSION_API)
"""

import hashlib
import hmac
import logging
import os
from typing import Any

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
                texto = (m.get("text") or {}).get("body", "") if m.get("type") == "text" else ""
                salida.append({"id": m["id"], "telefono": m["from"], "tipo": m.get("type", ""), "texto": texto})
    return salida


def configurado() -> bool:
    """¿Hay con qué enviar mensajes? Sin token y sin número, el servidor responde por la API pero no por WhatsApp."""
    return bool(os.environ.get("WHATSAPP_TOKEN") and os.environ.get("WHATSAPP_PHONE_NUMBER_ID"))


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
