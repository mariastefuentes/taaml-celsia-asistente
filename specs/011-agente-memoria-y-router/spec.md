---
estado: cumplida (pendiente de PR)
escrita: 2026-11-07
---
# Spec 011: agente con memoria conversacional, datos estructurados y router

Es el entregable 2 del proyecto integrador (Fase 2, 30 %): «agente con memoria conversacional, herramienta para datos estructurados (CSV/JSON) y router entre RAG y datos». Se escribe **antes** de programar. Parte del agente de la spec 002.

## Qué se necesita
1. **Memoria conversacional.** Que el agente recuerde los turnos anteriores de una misma conversación (por ejemplo «¿y en Ibagué?» después de preguntar por una sede).
2. **Herramienta de datos estructurados.** Una herramienta que consulte archivos que ya existen (`data/3_gold/sedes.json`, `data/5_extraccion/contactos.jsonl`, `data/3_gold/_catalogo.csv`) con filtros exactos, sin embeddings.
3. **Router entre RAG y datos.** El agente elige entre `buscar_en_base` (texto) y `consultar_datos` (datos exactos) según la pregunta.
4. **Modelo de pago.** El agente usa `gemini-3.8-flash` (indicación del profesor: API de pago y modelo reciente). Ollama queda solo como respaldo.

## Criterios de aceptación
- Dos preguntas seguidas en el mismo `thread_id` se resuelven con el contexto; con otro `thread_id` no hay contexto compartido.
- `consultar_datos` devuelve solo filas que existen en los archivos y dice «sin resultados» cuando no hay coincidencias.
- Una pregunta de sede o teléfono usa `consultar_datos`; una pregunta de trámites o tarifas usa `buscar_en_base`.
- Las pruebas automáticas no llaman a Gemini ni a Ollama (modelo simulado) y son gratis.
- Las llamadas reales a Gemini se hacen en un ensayo aparte, con confirmación previa de la usuaria.
- La pestaña «Agente» de la app muestra la conversación y qué herramienta usó cada respuesta.
- El Taller 1 no cambia: sus tres tareas siguen con `gemini-3.5-flash`.

## Fuera de alcance
- API con FastAPI, persistencia en disco y canales (WhatsApp/Telegram): es la Fase 3.
- Consultas SQL abiertas: la herramienta solo filtra campos definidos.
- Reevaluar las 59 preguntas con el modelo nuevo.
