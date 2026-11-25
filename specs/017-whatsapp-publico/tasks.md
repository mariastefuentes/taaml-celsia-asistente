# Tareas 017 — WhatsApp público con QR

- [x] Modo abierto explícito en `src/taaml/whatsapp.py` (`*` abre; lista inválida cierra).
- [x] `enlace_wa_me()` y normalización del número.
- [x] Plantilla de OpenClaw con el canal encendido y validación del puente.
- [x] Script `scripts/48_qr_whatsapp.py` y objetivo `make qr-whatsapp`.
- [x] QR visible en el chat web (`frontend/`) y en el panel (`api/panel.html`), servido en `/qr-whatsapp.png`; `--app` lo actualiza desde el script.
- [x] Pruebas en `test_whatsapp.py`, `test_openclaw.py` y `test_puente_mcp.py`.
- [x] Documentación: guía de despliegue, guion de la demo, README, `.env.example` y decisión D54.
- [ ] En el equipo de la demo: número dedicado, perfil del bot, QR proyectado y prueba con dos teléfonos externos.
