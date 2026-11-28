# Spec 018 - Pendientes de aprobación persistentes

- **Estado:** aprobada para la sustentación del 28 de noviembre de 2026.
- **Módulo:** 3.
- **Rúbrica que atiende:** 4.1 (calidad y continuidad) y la aprobación humana de D56.

## Problema

El checkpointer conserva la conversación pausada, pero el índice que usa el panel (`aprobaciones._PENDIENTES`) vive en memoria. Si se reinicia la API, el panel no muestra el pendiente; en el chat web el cliente sigue bloqueado y no hay forma de aprobarlo. F5 no causa el problema: solo recarga el navegador.

## Objetivo

1. Persistir el índice de pendientes en el Store de LangGraph (PostgreSQL o SQLite según la API).
2. Recuperarlo al arrancar, para que el panel y `POST /api/pendientes/{codigo}` sigan funcionando.
3. Borrar los pendientes cuando se resuelven o cuando se borran los datos del cliente.
4. Mantener el flujo actual: no cambia el agente, la aprobación ni el panel.

## Fuera de alcance

- Compartir reclamos o radicados entre web y WhatsApp.
- Persistir `_SIN_ENTREGAR`; sigue en memoria.
- TTL automático: un pendiente vencido dejaría la conversación bloqueada sin aparecer en el panel.
- Varios workers de la API: el diseño actual es de un proceso.

## Criterios de aceptación

- [ ] Con PostgreSQL o SQLite, un pendiente registrado se recupera después de vaciar la caché de memoria y volver a configurar el Store.
- [ ] `GET /api/pendientes` muestra el pendiente recuperado y no expone el teléfono.
- [ ] `POST /api/pendientes/{codigo}` puede resolverlo con el mismo código.
- [ ] `quitar` elimina el pendiente del Store.
- [ ] `olvidar_usuario` borra solo los pendientes de ese cliente.
- [ ] Sin Store configurado, todo sigue funcionando en memoria (scripts y pruebas).
- [ ] Si el Store falla, la API sigue en memoria y registra el error.
- [ ] La suite pasa sin modelos, sin red y sin PostgreSQL real.
