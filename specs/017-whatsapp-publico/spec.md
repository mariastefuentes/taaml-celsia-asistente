# Spec 017 — WhatsApp público con QR para el auditorio

- **Estado:** aprobada por el equipo para la sustentación del 28 de noviembre de 2026.
- **Módulo:** 3 y sustentación final.
- **Rúbrica que atiende:** 3.2 (WhatsApp real desde un número vinculado, con allowlist E.164, 10 %).

## Problema

El canal de WhatsApp de OpenClaw quedó probado con el número personal de un integrante. Para la demo, cualquier persona del auditorio debe poder escribirle al bot desde su celular escaneando un código QR. Hoy hay dos bloqueos:

1. `WHATSAPP_ALLOWLIST` se exige al instalar y el puente responde «Este número no está autorizado» a cualquier número que no esté en la lista; no se conocen los teléfonos del público de antemano.
2. No hay un QR propio de WhatsApp: solo existe el del chat web (`make qr-chat-web`), que es otra vía.

## Objetivo

1. Permitir un **modo abierto explícito** de la allowlist (`WHATSAPP_ALLOWLIST=*`), sin que un valor mal escrito abra el canal por accidente.
2. Que la plantilla de OpenClaw instale el canal de WhatsApp **encendido** (`channels.whatsapp.enabled: true`), con `dmPolicy: open` y `allowFrom: ["*"]` ya vigentes.
3. Generar el **QR de WhatsApp** (`make qr-whatsapp ARGS="+57…"`) con el enlace `wa.me` y un saludo precargado, para proyectarlo o imprimirlo.
4. Mantener el límite por teléfono (`limite.py`) como única defensa de cuota y documentar el riesgo de la vía no oficial.

## Fuera de alcance

- Migrar al número oficial de WhatsApp Business (API Cloud) para el público: sigue siendo la vía alterna y ya está implementada.
- Autenticar a la persona: la allowlist autentica el número, no a quien escribe.
- Aprobar reclamos por el canal de OpenClaw: la aprobación sigue por la API y el camino de Meta.

## Criterios de aceptación

- [ ] `WHATSAPP_ALLOWLIST=*` deja abiertos el webhook propio y el puente; sin la variable también queda abierto; una lista mal escrita **cierra** el canal en vez de abrirlo.
- [ ] `make openclaw-check` acepta `*` y la plantilla exige `channels.whatsapp.enabled: true`.
- [ ] `make qr-whatsapp ARGS="+57…"` genera `qr_whatsapp.png` y muestra el enlace `wa.me`.
- [ ] `/api/salud` sigue informando `allowlist_whatsapp: "abierta"` en modo abierto.
- [ ] Las pruebas cubren el modo abierto, el cierre ante una lista inválida y el enlace `wa.me`.
- [ ] La guía de despliegue y el guion de la demo explican el QR, el número dedicado y el plan B.
