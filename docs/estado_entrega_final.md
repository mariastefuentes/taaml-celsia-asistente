# Estado de la entrega frente a la rúbrica del 28 de noviembre

Revisión del 23 de noviembre de 2026. Cada fila dice **dónde está la evidencia en el repositorio** y **qué falta**. Se actualiza el día de la sustentación.

## Resumen

| Categoría | Peso | Estado |
|---|---|---|
| 1. Arquitectura del agente y orquestación | 25 % | Listo salvo la medición del router con 20 herramientas |
| 2. Datos, RAG y conocimiento | 15 % | Listo |
| 3. OpenClaw, canales y despliegue | 30 % | Configuración y workspace versionados; falta validar en el equipo de la demo y vincular el canal |
| 4. Calidad, seguridad y documentación | 20 % | Listo; falta la salida real de `security audit` |
| 5. Sustentación en vivo | 10 % | Guion listo; falta ensayarlo |

## Ítem por ítem

| Ítem | Peso | Evidencia | Falta |
|---|---|---|---|
| **1.1** 20 tools `@tool` con Pydantic | 10 % | `src/taaml/agente.py` (`HERRAMIENTAS`, 20), `specs/015-herramientas-de-dominio/`, pruebas en `tests/test_agente.py`, traza en LangSmith | Ninguna para el código |
| **1.2** Router y planificación | 8 % | `prompts/v13_agente.md`, `scripts/22_matriz_enrutamiento.py`, `docs/enrutamiento.html` | **Volver a medir la matriz con las 20 herramientas** (el 42/43 es del prompt v9) |
| **1.3** Memoria por capas | 7 % | `PostgresSaver` + `PostgresStore`, `docs/memoria.html`, `tests/test_memoria_postgres.py` | Ensayar el reinicio en vivo |
| **2.1** Pipeline de datos | 5 % | `scripts/01`–`06`, `docs/pipeline.html`, `make datos` | Ninguna |
| **2.2** RAG sobre Qdrant con citas | 6 % | `src/taaml/recuperacion.py`, `src/taaml/vectorstore.py`, nota de dato sin respaldo, `docs/arquitectura_agente.html` | Ninguna |
| **2.3** Evaluación del conocimiento | 4 % | `ranking_k10.csv`, `metricas_logs.csv`, `notebooks/analisis_conversaciones.ipynb` (t-SNE, UMAP, PCA) | Ninguna |
| **3.1** Gateway OpenClaw | 8 % | `openclaw/openclaw.example.json`, `docs/guia_despliegue_openclaw.md`, D47 | **`openclaw config validate` en el equipo de la demo** |
| **3.2** WhatsApp con allowlist E.164 | 10 % | Webhook propio con allowlist (`src/taaml/whatsapp.py`, D49), modo abierto `*` y QR del auditorio (`make qr-whatsapp`, D53) + canal de OpenClaw | **Vincular el canal de OpenClaw con el número dedicado y probarlo desde dos teléfonos externos** |
| **3.3** Workspace operativo | 7 % | `openclaw/workspace/` (`SOUL`, `AGENTS`, `USER`, `MEMORY`, bitácora), D48 | Escribir la bitácora del día |
| **3.4** Skills/MCP | 5 % | `src/taaml/servidor_mcp.py` (10 herramientas), `tests/test_servidor_mcp.py`, `.opencode/skills/` | Ninguna |
| **4.1** Código, pruebas y `uv` | 7 % | 409 pruebas, ruff, pre-commit, CI, `make verificar-clon` | Ninguna |
| **4.2** Seguridad y hardening | 7 % | Sandbox y `tools.deny` versionados, HITL, límite por teléfono, inyección 11/11 | **`openclaw security audit` real** y pegarlo con fecha |
| **4.3** Documentación final | 6 % | README, guía de despliegue, diagramas Archify, informes, `.env` fuera del repo | Regenerar el PDF del informe si cambia |
| **5.1** Pitch de 7 minutos | 6 % | `docs/guion_sustentacion_final.md` | Ensayarlo con cronómetro |
| **5.2** Discusión técnica de 8 minutos | 4 % | Mismo guion, reparto por integrante | Ensayar preguntas del público |
| Bonus | — | Guion en inglés en el mismo documento | Decidir quién sustenta en inglés |

## Antes del sábado (en orden de riesgo)

1. **Medir el router con las 20 herramientas** (`make` no lo hace: `uv run python scripts/22_matriz_enrutamiento.py` gasta cuota). Es lo único que puede bajar una nota ya ganada.
2. **Vincular el canal de WhatsApp de OpenClaw** en el equipo de la demo y correr `openclaw channels status --probe`.
3. **Correr `openclaw security audit`** y guardar la salida real en `docs/auditoria_openclaw.md` con fecha.
4. **Definir `WHATSAPP_ALLOWLIST=*`** para el auditorio, comprobar `/api/salud` y generar el QR con `make qr-whatsapp ARGS="+57<numero-del-bot> --html"`.
5. **Ensayar el guion completo** una vez, con el teléfono de un invitado real.
6. **Mergear la rama `informe-final-unificado`** (trae `informe_final.md` y su PDF) y regenerar el PDF si cambia.
7. Cerrar o rebasar las PR abiertas antiguas (#118, #138, #139) para que el CI no falle el viernes.

## Lo que no se afirma

- Que el router acierte con 20 herramientas: la cifra vigente (42/43) es del prompt v9 y con cinco herramientas.
- Que el canal de OpenClaw esté vinculado: la configuración está versionada y validada, pero no se probó en este equipo.
- Que el bot esté desplegado en un servidor: corre en el equipo de la demo con un túnel https.
