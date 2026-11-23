# Auditoría del proyecto frente al Módulo 3 (23/11/2026)

**Alcance y límite.** Se hizo sin el Anuncio 007 ni la rúbrica oficial (no están en el repositorio ni en las carpetas del curso). Los requisitos usados son los del prompt de auditoría que entregó el equipo; donde dependen del texto oficial se marca **NO VERIFICABLE**. Esto es una simulación, no una nota oficial. Solo se inspeccionó código y configuración; no se probó WhatsApp real ni se repitió el despliegue.

## Dictamen: NO APTO — existen incumplimientos obligatorios (según el prompt)

Hay dos bloqueos: solo hay 5 herramientas (se exigen 20) y OpenClaw no está conectado a WhatsApp ni tiene su espacio de trabajo completo.

## Matriz de los 15 criterios

| # | Criterio (peso) | Estado | Evidencia revisada | Brecha para 5.0 |
|---|---|---|---|---|
| 1.1 | Herramientas, catálogo de 20 (10 %) | **NO CUMPLE** (7 de 20 el 23/11: se añade una por vez, en la rama `herramientas-20`) | `HERRAMIENTAS` en `src/taaml/agente.py:368` tiene 5, con esquema Pydantic (`@tool(args_schema=…)`); `servidor_mcp.py` expone 2 más, que son envoltorios de las mismas búsquedas | Faltan 15 herramientas reales, cada una con esquema, prueba y uso demostrable |
| 1.2 | Router y razonamiento (8 %) | CUMPLE PARCIAL | Matriz de enrutamiento 42/43, banco 49/49 (medido hoy), `errores_amables` | Con 20 herramientas hay que ampliar la matriz; R31 sigue marcada |
| 1.3 | Memoria por capas (7 %) | CUMPLE PARCIAL | PostgresSaver + Store, `thread_id`, aislamiento por usuario en pruebas | Falta demostrar persistencia tras reiniciar en vivo y edición/auditoría de memoria por el usuario |
| 2.1 | Pipeline de datos M1 (5 %) | CUMPLE PARCIAL | `data/1_bronze → 2_silver → 3_gold`, scripts numerados | No se volvió a ejecutar de cero en esta auditoría |
| 2.2 | RAG en Qdrant (6 %) | CUMPLE PARCIAL | Qdrant local, mezcla densa + léxica, fuentes en `buscar_en_base` | Filtros por payload y citas: no se revisó cita por cita; en uso real cae a numpy si otro proceso bloquea Qdrant |
| 2.3 | Evaluación del conocimiento (4 %) | CUMPLE PARCIAL | `scripts/21_metricas_ranking.py`, `36_construir_notebook_tsne.py`, `ranking_k10.csv` | Confirmar recall@10 y nDCG@10 con 20–30 consultas y la interpretación escrita |
| 3.1 | Gateway OpenClaw (8 %) | CUMPLE PARCIAL | `openclaw.json`: `bind: loopback`, token, DeepSeek vía API cloud, `deepseek-flash` | Fallback `deepseek-v4-pro` añadido el 23/11 (falta probarlo apagando el primario); no arranca solo (se enciende a mano) |
| 3.2 | WhatsApp en producción (10 %) | **NO VERIFICABLE / riesgo alto** | Ruta A: webhook FastAPI propio con Meta; `openclaw.json` **no tiene canal WhatsApp ni allowlist** | Prueba real desde un teléfono externo, túnel público estable, hasta 5 destinatarios en Meta |
| 3.3 | Workspace (7 %) | **CUMPLE PARCIAL (flojo)** | Existen `SOUL.md`, `AGENTS.md`, `USER.md`, `IDENTITY.md`, `DREAMS.md` | `MEMORY.md`, bitácora `memory/2026-11-23.md` y sección «Límites» de `SOUL.md` creados el 23/11; falta que la bitácora se actualice a diario |
| 3.4 | Skills / MCP propio (5 %) | CUMPLE PARCIAL | `servidor_mcp.py` conectado en `mcp.servers.celsia`, con prueba de cliente MCP real | Hay que mostrar que el agente de OpenClaw lo invoca de verdad; hoy hay que probarlo |
| 4.1 | Código y pruebas (7 %) | CUMPLE (reportado) | 373 pasan + 2 omitidas (última medición, sin repetirla hoy) | Repetir `uv sync` y `pytest` en un clon limpio (`make verificar-clon`) |
| 4.2 | Seguridad y hardening (7 %) | CUMPLE PARCIAL | `tools.deny` (automation, runtime, fs), `fs.workspaceOnly`, sandbox `all`, `exec: deny`, HITL del reclamo, 11/11 ataques | `openclaw security audit` ejecutado el 23/11: 0 críticos, 1 advertencia aceptada ([salida](openclaw_security_audit.md)); `--deep` también 0 críticos tras reiniciar el gateway; falta la evidencia de pairing |
| 4.3 | Documentación (6 %) | CUMPLE PARCIAL | README, LICENSE MIT, decisiones D1–D40, diagramas, informe | Guía de despliegue y límites conocidos al día; un evaluador externo necesita una sola ruta de arranque |
| 5.1 | Elevator pitch (6 %) | NO VERIFICABLE | `docs/guion_demo_*.md` | Guion de 7 min cronometrado y ensayo real |
| 5.2 | Discusión técnica (4 %) | NO VERIFICABLE | — | Banco de preguntas y reparto por integrante |

## Hallazgos priorizados

| Sev. | Hallazgo | Causa | Corrección | Cierre |
|---|---|---|---|---|
| CRÍTICO | 5 herramientas en vez de 20 | El alcance del Taller 2 se quedó en 5 | Diseñar 15 herramientas útiles para Celsia, con `args_schema`, prueba por herramienta y entradas en la matriz del router | Un inventario de 20 filas; cada una con una prueba que la invoca |
| CRÍTICO | WhatsApp real sin ensayo registrado | Depende de Meta, túnel y número propio | Ensayo completo con un teléfono externo, registrar trazas | Capturas más logs de un hilo con herramienta y memoria |
| ALTO | Workspace sin `MEMORY.md` ni bitácora | Solo se generó lo que crea el asistente de OpenClaw | Crear `MEMORY.md` y la bitácora del día; ampliar `SOUL.md` | Archivos presentes y citados en el guion |
| ALTO | Sin modelos de respaldo en OpenClaw | Solo `primary` configurado | Añadir `fallbacks` (p. ej. `deepseek-v4-pro`) | `openclaw.json` con fallbacks, probado apagando el primario |
| MEDIO | Gateway sin arranque automático | `gateway install` bloqueado (EPERM, probablemente antivirus) | Decisión del equipo: manual | Lista de arranque previa a la demo |
| MEDIO | `openclaw security audit` sin evidencia | No se guardó la salida | Ejecutarlo y archivar el resultado | Informe en `docs/` |
| MEDIO | Respuestas de trámites >1.000 caracteres | Se priorizó la completitud | Acortar o dividir | Medición del largo en el banco |
| BAJO | R31 y R22 marcadas en la matriz | Diferencias de herramienta y de texto | Se documentó; la matriz no se toca (D27) | — |

## Qué no se pudo comprobar
Texto oficial del Anuncio 007 y de la rúbrica (pesos exactos, si OpenClaw debe ser el canal de WhatsApp en Ruta A, qué cuenta como «herramienta»); WhatsApp real; instalación en limpio; `openclaw security audit`; bonificaciones (inglés, LangSmith, Telegram).

## Estimación de nota (sin evidencia completa; no es nota oficial)
Con lo verificado, el ítem 1.1 quedaría en 1.0–2.0 y el 3.3 en 3.0; el resto depende de pruebas pendientes. No se calcula nota ponderada final porque 5 de 15 ítems están sin verificar.
