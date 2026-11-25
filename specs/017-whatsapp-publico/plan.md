# Plan 017 — WhatsApp público con QR

## Cambios

| Archivo | Cambio |
|---|---|
| `src/taaml/whatsapp.py` | `LISTA_ABIERTA = "*"`; `autorizado()` distingue lista vacía, `*` y lista con números; `enlace_wa_me()` arma el enlace con el saludo. |
| `src/taaml/openclaw.py` | La plantilla exige `channels.whatsapp.enabled: true`; valida la allowlist del puente (`*` o E.164). |
| `openclaw/openclaw.example.json` | `channels.whatsapp.enabled: true`. |
| `scripts/48_qr_whatsapp.py` | Nuevo: QR del número del bot (`wa.me`), salida `qr_whatsapp.png`. |
| `Makefile` | Objetivo `qr-whatsapp`. |
| `tests/test_whatsapp.py`, `tests/test_openclaw.py`, `tests/test_puente_mcp.py` | Pruebas del modo abierto, del cierre y del enlace. |
| `docs/guia_despliegue_openclaw.md`, `docs/guion_demo_whatsapp.md`, `docs/decisiones.md`, `openclaw/README.md`, `.env.example`, `README.md` | Procedimiento y decisión D54. |

## Riesgos

- **Costo y abuso:** cualquier número puede escribir. Se apoya en el límite por teléfono y en `LIMITE_MENSAJE`; se documenta.
- **Ban de WhatsApp:** la vía de OpenClaw no es oficial; número dedicado, nunca el personal, y plan B por el webhook de Meta.
- **Número mal escrito:** `enlace_wa_me` exige entre 8 y 15 dígitos y no adivina el indicativo.

## Verificación

`make check` (lint, pruebas y skills) y `make qr-whatsapp ARGS="+573001112233"` para comprobar el PNG.
