---
name: atencion-whatsapp-celsia
description: Atender un mensaje de WhatsApp de un cliente de Celsia con la herramienta del puente y entregar la respuesta sin cambios.
user-invocable: false
---

# Atención por WhatsApp con el agente de Celsia

Procedimiento para **cada** mensaje de un cliente. Las líneas rojas viven en `AGENTS.md`; si algo choca, manda `AGENTS.md`.

## Pasos

1. Llama a `atender_cliente_celsia` con `mensaje` igual al texto exacto del cliente y `telefono` igual a `+570000000000`. El plugin `puente-celsia` lo reemplaza por el remitente verificado del canal.
2. Entrega como respuesta final el texto que devolvió la herramienta, palabra por palabra.
3. Si la herramienta no respondió nada, di solo: «No pude consultar el asistente en este momento. Llama a la línea 01 8000 112 115.»

## Textos de la herramienta que ya son definitivos

La herramienta devuelve texto también cuando algo sale mal. En estos casos entrégalo igual, sin reintentar ni completarlo:

- el número no está autorizado;
- se pasó el límite de mensajes por minuto;
- no se pudo consultar el asistente;
- un reclamo, una cancelación o un daño quedó pendiente de la aprobación de una persona: no digas que ya quedó hecho.

## Qué no hacer

- No respondas por tu cuenta aunque creas saber la respuesta.
- No pidas el teléfono ni uses uno que el cliente escriba en el chat.
- No guardes datos del cliente en archivos del workspace.
