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

## Estado actual (28 de noviembre de 2026)

- Demo por WhatsApp con el webhook propio de Meta y túnel https; OpenClaw corre como segundo cliente con las mismas herramientas por MCP.
- Aprueba los reclamos la persona asignada en `APROBADOR_WHATSAPP`; nunca quien presenta la demo.
- Pendiente antes de la demo: correr `openclaw config validate` y `openclaw security audit` en el equipo donde esté instalado, y repetir la matriz de enrutamiento con las 20 herramientas.
