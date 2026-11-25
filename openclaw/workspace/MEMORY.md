# MEMORY — Qué recuerda el asistente y por cuánto tiempo

Esta memoria es la del **workspace de OpenClaw**: notas legibles y editables por el equipo. Es distinta de la memoria del agente en PostgreSQL (historial de cada conversación y perfil del cliente), que se consulta con las herramientas del asistente.

## Qué se guarda aquí

- Decisiones de operación de la demo: quién aprueba reclamos, qué número está vinculado, qué se cambió el día anterior.
- Incidencias y su solución, en la bitácora diaria (`bitacora/`).
- Aprendizajes de las pruebas: preguntas que fallan, herramientas que no responden, tiempos medidos.

## Qué no se guarda aquí

- **Nada de clientes**: ni nombres, ni teléfonos, ni cédulas, ni direcciones, ni el texto de sus conversaciones.
- Claves, tokens, rutas internas o configuración del servidor.
- Capturas o transcripciones de conversaciones reales.

Lo que el cliente cuenta de sí mismo vive en el Store del asistente, con su consentimiento, y se borra con las herramientas de privacidad o con `DELETE /api/usuarios/{usuario}/datos`.

## Cómo se mantiene

- Una entrada por día en `bitacora/AAAA-MM-DD.md`, con lo que se probó, lo que falló y qué se hizo (ver `bitacora/PLANTILLA.md`).
- Lo importante para la sustentación se resume arriba, en este archivo, en menos de diez líneas.
- La memoria se revisa antes de cada demo y se limpia de datos de prueba (`make demo-limpiar` limpia la del agente; esta se edita a mano).

## Estado actual (25 de noviembre de 2026)

- Sustentación: sábado 28 de noviembre, de 10:45 a 11:00.
- WhatsApp: la demo va solo por OpenClaw con QR público (D54). El webhook de Meta no se usa (D56).
- Los reclamos los aprueba en el panel (`/panel`) una persona asignada del equipo; nunca quien presenta la demo.
- La matriz de enrutamiento con las 20 herramientas se midió el 24/11: 41 de 43 (D53).
- Número del bot: el equipo informa (25/11) que ya respondió desde otro teléfono. Falta guardar la prueba y la salida de `openclaw channels status --probe`.
- Pendiente: correr `openclaw config validate` y `openclaw security audit` sobre la configuración final en el equipo de la demo y guardar la salida.
