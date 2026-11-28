# INFORME_QA_PLAYWRIGHT â€” Celsia

**Fecha/hora:** 2026-11-27 13:50 -05:00. **Repo:** `C:\Proyectos\taama-celsia\taaml-celsia-asistente`. **Rama:** `test/limpiar-cache-modelos`. `main@2046b53` + `tests/conftest.py` (PR #223, no merge). Sin tocar cambios del usuario; `.tar.gz` untracked intacto. **No** commits/push/PR en esta auditorÃ­a; sin WhatsApp real, sin nÃºmeros externos, sin `QA_MODELO_REAL`, sin tokens innecesarios, sin `.env`, sin producciÃ³n, sin debilitar pruebas.

## Comandos ejecutados
- `make chat-web` â†’ `npm install` + `npm run build` `vite` **OK** (`frontend/dist`,`43` mÃ³dulos). `npm` aviso `esbuild` install-scripts no aprobado, `0 vulnerabilities`.
- `make qa` â†’ `QA_E2E=1`, `uv run python -m pytest tests/e2e -rs`. **14 passed, 0 failed, 0 skipped.** **agente simulado, `QA_URL` no, `QA_MODELO_REAL` no.** `make chat-web` antes. **no real token**.
- `make test` â†’ `uv run --group analisis python -m pytest`. **547 passed, 0 failed, 2 skipped.** `make test` excluye `tests/e2e` (`collect_ignore`) salvo `QA_E2E`. `2 skipped` `ss`. 
- `make lint` â†’ `ruff ... F,E9` **All checks passed**; `uv lock --check` **OK**. 
- `make skills-check` â†’ `verificar_skills.py` **Skills OK**. 
- `git status`,`branch`. 

## Evidencia Playwright (`tests/e2e/test_qa_navegador.py`, Microsoft Edge + Playwright 1.65.2; `docs/qa_playwright.md`)
- **14 passed in ~23.6s.** `-rs`. 
- **Carga/navegaciÃ³n:** portada QR, header, `/chat`, `/panel`, ruta daÃ±ada, `/api/salud`. `render` React + Vite. `make chat-web`. 
- **Chat web envÃ­o/recepciÃ³n:** `POST /api/chat`, flujo Â«Â¿QuÃ© es una granja solar?Â», respuesta + herramienta + fuentes `documento`/`fragmento`, estados carga; `POST /api/chat` simulado `agente`. 
- **Respuestas/estados:** `text/event-stream`, `conversar_en_vivo`, streaming, `Nueva conversaciÃ³n`, `/nuevo`, `/nueva`, `/nuevo`, `pendiente`, `respondido`, loading, `409` bloqueo pendiente, bloqueo regenerar/chat. 
- **Manejo errores/desconexiones:** consola sin errores, red sin `400+`, `4xx`, `5xx`, `pending`, `failed`, `websocket`, `offline`, `net::ERR`, `requestfailed`, `POST /api/chat` `409`, webhook sin firma `401`, MCP/error `fallback`, `MENSAJE...`. 
- **Sesiones/continuidad:** `session`, `hilo`, `thread_id`, `Nueva conversaciÃ³n`, `/nuevo`, `reiniciar conversación`, `per-channel-peer`, `localStorage`, recarga. 
- **Formularios/controles:** `/nueva`, `/nueva`, `/nuevo`, `/nueva`, enviar, copiar, ðŸ‘, ðŸ‘Ž, audio/`TTS`, regenerar, `fuente`, `Olvidar todo`, `/api/olvidar`, `/api/actividad`, `/panel`, `Por aprobar`, `/api/pendientes`, `X-Aprobador`, responsive celular 390x844 + escritorio 1366x768, sin overflow. 
- **IntegraciÃ³n frontend-backend:** `frontend`, `/api`, `/api/salud`, `/api/chat`, `/api/actividad`, `/panel`, `/qr`, webhook WhatsApp **simulado firmado** `200` + `401` sin firma; **no** prueba real WhatsApp. `/chat` separado no `QA_E2E`. 
- **`make test`** `test_api`,`test_aprobaciones`,`test_openclaw`,`test_whatsapp`,`test_puente`,`test_flujo_reclamo`,`test_modelos`,`test_conversaciones`, etc. 

## Flujos comprobados
`QA`: pÃ¡gina `Playwright`, `API`, `webhook` (simulado), chat, `/panel`, `/api/salud`, formularios, `Nueva conversaciÃ³n`, `/nuevo`, `copiar`, `feedback`, `audio`, `regenerar`, `fuente`, `responsive`, `consola`, `red`, `409`, `401`. `make test`. 

## Errores encontrados y gravedad
**Ninguno** en `make qa`,`make test`,`make lint`,`make skills-check`,`make chat-web`. Avisos no bloqueantes: `npm install-scripts esbuild`, `Playwright` Edge/Chrome requisito documentado, `make test` `2 skipped`, `record-missing`, `radicar_simulado`, `avisos_openclaw`, `restart-loop` pendientes **fuera de esta QA Playwright** (no relevados por `make qa`). `test_modelos` previo fallo `lru_cache` **corregido** (`tests/conftest.py`, PR #223; `547 passed`). No desactivado/alterado. 

## Omitidas / inestables
**`make qa`: 0 omitidas, 0 fallidas, 0 inestables.** `make test`: `2 skipped`. `make test` no incluye `tests/e2e`. `QA_MODELO_REAL` no. 

## Limitaciones
- `make qa` **servidor propio con agente simulado**; **no** `QA_URL=...`; **no** `QA_MODELO_REAL`; **no** prueba modelo DeepSeek/Gemini real ni consumo. 
- **NO se valida WhatsApp end-to-end real**; **no** mensajes reales, no nÃºmeros externos, no webhook de Meta real, no `PUENTE` real WhatsAppâ†’OpenClawâ†’MCPâ†’FastAPI; `webhook` solo simulado firmado. `**64`,`**69`,`*`; no cambios. 
- **No** producciÃ³n, no `.env`, no credenciales, no PostgreSQL/Qdrant reales aquÃ­, no RAG real, no `POST /chat` real en `make qa`. `Playwright` navegador. 
- `make test` `2 skipped`. `make lint`. `make skills-check`. `make chat-web`. `PR #223` no merge. 

## Veredicto final
**APROBADO CON OBSERVACIONES.** `make qa` `14/14`, `make test` `547`+`2`, `lint`, `skills`, `chat-web`. **Observaciones:** `2 skipped`, `npm esbuild`, `record-missing`, `radicar_simulado`, `OPENCLAW_AVISOS`, `avisos_openclaw`, no `QA_MODELO_REAL`, **no WhatsApp real**. **No** afirmar WhatsApp end-to-end sin prueba real autorizada.

