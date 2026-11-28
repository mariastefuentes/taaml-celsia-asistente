# Estado de la entrega frente a la rúbrica del 28 de noviembre

Revisión del 23 de noviembre de 2026, con cifras al 26. Cada fila dice **dónde está la evidencia en el repositorio** y **qué falta**. Se actualiza el día de la sustentación.

## Resumen

| Categoría | Peso | Estado |
|---|---|---|
| 1. Arquitectura del agente y orquestación | 25 % | Listo |
| 2. Datos, RAG y conocimiento | 15 % | Listo |
| 3. OpenClaw, canales y despliegue | 30 % | Configuración y workspace versionados; falta validar en el equipo de la demo y vincular el canal |
| 4. Calidad, seguridad y documentación | 20 % | Listo; falta la salida real de `security audit` |
| 5. Sustentación en vivo | 10 % | Guion listo; falta ensayarlo |

## Ítem por ítem

| Ítem | Peso | Evidencia | Falta |
|---|---|---|---|
| **1.1** 20 tools `@tool` con Pydantic | 10 % | `src/taaml/agente.py` (`HERRAMIENTAS`, 20), `specs/015-herramientas-de-dominio/`, pruebas en `tests/test_agente.py`, traza en LangSmith | Ninguna para el código |
| **1.2** Router y planificación | 8 % | `prompts/v13_agente.md`, `scripts/22_matriz_enrutamiento.py`, `docs/enrutamiento.html` | Medida con las 20 herramientas el 26/11: 40/43 (D67). Repetir si cambia el prompt |
| **1.3** Memoria por capas | 7 % | `PostgresSaver` + `PostgresStore`, `docs/memoria.html`, `tests/test_memoria_postgres.py` | Ensayar el reinicio en vivo |
| **2.1** Pipeline de datos | 5 % | `scripts/01`–`06`, `docs/pipeline.html`, `make datos` | Ninguna |
| **2.2** RAG sobre Qdrant con citas | 6 % | `src/taaml/recuperacion.py`, `src/taaml/vectorstore.py`, nota de dato sin respaldo, `docs/arquitectura_agente.html` | Ninguna |
| **2.3** Evaluación del conocimiento | 4 % | `ranking_k10.csv`, `metricas_logs.csv`, `notebooks/analisis_conversaciones.ipynb` (t-SNE, UMAP, PCA) | Ninguna |
| **3.1** Gateway OpenClaw | 8 % | `openclaw/openclaw.example.json`, `docs/guia_despliegue_openclaw.md`, D47 | **`openclaw config validate` en el equipo de la demo** |
| **3.2** WhatsApp con allowlist E.164 | 10 % | Canal de OpenClaw con QR público (D54) visible en el chat web y el panel (`/qr-whatsapp.png`), allowlist en el puente (D49, modo abierto `*`) y aprobación en el panel (D56). El webhook de Meta no se usa | **Guardar la prueba desde dos teléfonos externos y probar el aviso de aprobación en el equipo del bot** |
| **3.3** Workspace operativo | 7 % | `openclaw/workspace/` (`SOUL`, `AGENTS`, `USER`, `MEMORY`, bitácora), D48 | Escribir la bitácora del día |
| **3.4** Skills/MCP | 5 % | `src/taaml/servidor_mcp.py` (10 herramientas), `tests/test_servidor_mcp.py`, `.opencode/skills/` | Ninguna |
| **4.1** Código, pruebas y `uv` | 7 % | 591 pruebas aprobadas y 2 omitidas, ruff, pre-commit, CI, `make verificar-clon`, revisión con Playwright (`docs/qa_playwright.md`) | Ninguna |
| **4.2** Seguridad y hardening | 7 % | Sandbox y `tools.deny` versionados, HITL, límite por teléfono, inyección directa 11/11 e indirecta 8/8 (26/11) | **`openclaw security audit` real** y pegarlo con fecha |
| **4.3** Documentación final | 6 % | README, guía de despliegue, diagramas Archify, informes, `.env` fuera del repo | Regenerar el PDF del informe si cambia |
| **5.1** Pitch de 7 minutos | 6 % | `docs/guion_sustentacion_final.md` | Ensayarlo con cronómetro |
| **5.2** Discusión técnica de 8 minutos | 4 % | Mismo guion, reparto por integrante | Ensayar preguntas del público |
| Bonus | — | Guion en inglés en el mismo documento | Decidir quién sustenta en inglés |

## Antes del sábado (en orden de riesgo)

1. **Vincular el canal de WhatsApp de OpenClaw** en el equipo de la demo y correr `openclaw channels status --probe`.
2. **Correr `openclaw security audit`** y guardar la salida real en `docs/auditoria_openclaw.md` con fecha.
3. **Correr `make qa`** (Playwright) y guardar la salida: el Anuncio 008 no acepta presentarse sin esa auditoría.
4. **Definir `WHATSAPP_ALLOWLIST=*`** para el auditorio, comprobar `/api/salud` y generar el QR con `make qr-whatsapp ARGS="+57<numero-del-bot> --html --app"`.
5. **Ensayar el guion completo** una vez, con el teléfono de un invitado real.
6. **Informe final** (`docs/3 - Informe/informe_final.md`): actualizar su sección 11 cuando se cierre un pendiente y regenerar el PDF con `make pdf`.

## Lo que no se afirma

- Que el router acierte siempre: con las 20 herramientas la matriz da 40/43 (26/11, D67), es una sola corrida y las rutas varían entre corridas.
- Que el canal de OpenClaw esté vinculado: la configuración está versionada y validada, pero no se probó en este equipo.
- Que el bot esté desplegado en un servidor: corre en el computador de la demo.
