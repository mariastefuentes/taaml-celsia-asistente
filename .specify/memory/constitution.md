# CONSTITUTION — Asistente Celsia

> **Verdad central del proyecto.** Este documento define el propósito, el stack, la
> estructura, las convenciones y el flujo de trabajo de `taaml-celsia-asistente`. Si algo
> aquí contradice al código, el código manda **y este archivo se actualiza**.

> ⚠️ **Directiva de mantenimiento:** cada cambio significativo (nuevas funcionalidades,
> cambios de arquitectura, módulos nuevos o ajustes de tecnologías) **actualiza este
> archivo en el mismo commit**, para que la verdad central no se separe del repositorio.

---

## 0. Identidad del proyecto

| Campo | Valor |
|-------|-------|
| **Nombre** | Asistente Celsia (`taaml-celsia-asistente`) |
| **Descripción** | Base de conocimiento y agente conversacional sobre información pública de Celsia: corpus y Q&A con RAG (Módulo 1), agente con memoria, herramientas y API + frontend (Módulo 2), y canal de WhatsApp por OpenClaw con PostgreSQL, aprobación humana y panel en vivo (Módulo 3). |
| **Repositorio** | https://github.com/mariastefuentes/taaml-celsia-asistente |
| **Autoría** | María Stella Fuentes, Juan José Mosquera, Nicolás Bolaños y Jensen Fabián Tamayo — Grupo 4 |
| **Curso** | Técnicas avanzadas de IA aplicadas en modelos de lenguaje (Maestría en IA y Ciencias de Datos, UAO, 2026-2S) |
| **Licencia** | MIT |
| **Rama principal** | `main` |
| **Estado** | Operativo para la demostración 🟢 (Módulos 1 a 3). La demo va por el WhatsApp de OpenClaw; el webhook de Meta existe pero no se usa. Pendiente: despliegue en un servidor y prueba con tráfico real. |

## 1. Propósito y no-propósito

### Propósito

Convertir el sitio público de **celsia.com** en un corpus Markdown citable y reproducible
(patrón Medallion: Bronze → Silver → Gold → curaduría → fragmentos) y responder preguntas
de clientes **solo con ese corpus**, citando la fuente y diciendo «no sé» cuando la
respuesta no está en la base. Sobre ese corpus se construyó un agente con herramientas
tipadas, memoria por capas, aprobación humana para los reclamos y un canal de WhatsApp
(OpenClaw), servido por una API FastAPI y un frontend React.

### No-propósito

No es un asistente general ni un buscador abierto de internet: no inventa datos, no
consulta fuentes distintas de las versionadas y no responde con conocimiento del modelo.
Tampoco es un *crawler* del dominio completo, ni un sistema de producción con alta
disponibilidad, ni un canal oficial de Celsia. **No procesa datos reales de clientes de
Celsia**: la demo usa datos inventados; del teléfono se guarda un hash y solo lo que la
persona cuenta de sí misma, con derecho a consultarlo y borrarlo. No se conecta a los
sistemas de Celsia: los reclamos y radicados son simulados.

## 2. Alcance

### Dentro del alcance

- Capturar con un `User-Agent` propio, `timeout`, pausa entre peticiones y respeto de
  `robots.txt` y `sitemap.xml` (los PDF de celsia.com están bloqueados: no se descargan).
- Mantener las capas **Bronze** (HTML crudo), **Silver** (texto limpio, sin duplicados) y
  **Gold** (Markdown con *front matter* y catálogo).
- Curar la base con reglas explícitas y registrar cada descarte con su motivo.
- Fragmentar (`chunks.jsonl`), indexar con embeddings y recuperar los fragmentos más
  relevantes por pregunta (RAG).
- Responder con **Q&A, resumen y FAQ** con prompts versionados y salida estructurada.
- Ejecutar un agente (`create_agent` de LangChain sobre LangGraph) con 20 herramientas
  Pydantic, memoria corta y larga en PostgreSQL, aprobación humana y respaldo de modelo.
- Servir el agente por una API FastAPI (streaming SSE y `POST /chat` para canales) y un
  frontend React; exponer diez herramientas de solo lectura por un servidor MCP.
- Atender WhatsApp por el gateway de OpenClaw (QR, plugin que fija el remitente y puente
  MCP hacia la API), con panel en vivo, límite por teléfono y atajos de intención.
- Ofrecer un `Makefile` como interfaz única del proyecto y una app Streamlit histórica
  para el Taller 1.

### Fuera del alcance (por ahora)

- PDFs, vídeos y transcripciones de celsia.com (bloqueados por `robots.txt`).
- Datos reales de clientes o cualquier información no pública.
- Despliegue en producción con alta disponibilidad, autenticación de usuarios finales y
  pruebas de carga con muchas personas a la vez.
- Integración con los sistemas de Celsia: los reclamos, radicados y aprobaciones son
  simulados y no salen del prototipo.
- Usar el webhook de Meta como canal de la demostración: el código existe, pero la demo
  va por OpenClaw (D56).

### Fases

| Fase | Estado | Entregable |
|------|--------|------------|
| 1. Pipeline de datos (specs 001) | ✅ Hecha | `data/1_bronze` → `4_curaduria` |
| 2. Recuperación y agente (specs 002) | ✅ Hecha | `src/taaml/recuperacion.py`, `08`–`15` |
| 3. Continuidad de la demo (specs 003) | ✅ Hecha | `src/taaml/respaldo.py` |
| 4. Base vectorial Qdrant (specs 004 y 012) | ✅ Hecha | `data/4_curaduria/qdrant` |
| 5. Evidencia de resumen y FAQ (specs 005) | ✅ Hecha | `docs/2 - Conjunto de prueba/` |
| 6. Tabla y pruebas del pipeline (specs 006) | ✅ Hecha | `src/taaml/corpus.py` |
| 7. Pestaña Corpus y scraping (specs 007) | ✅ Hecha | `app/asistente.py`, `app/modulo1.py` |
| 8. Prueba del scraper (specs 008) | ✅ Hecha | `tests/test_scraper.py` |
| 9. Etapa Descubrir (specs 009) | ✅ Hecha | `data/2_silver/_descubrimiento.json` |
| 11. Agente con memoria y router (specs 011) | ✅ Hecha | `src/taaml/agente.py`, `consulta_datos.py`, API `api/` y frontend `frontend/` |
| 13. Agente en producción con WhatsApp (specs 013) | ✅ Código fusionado; Meta solo se probó con su número de prueba (20/11) y la demo va por OpenClaw (D56) | `api/main.py`, `src/taaml/whatsapp.py`, `limite.py`, `prompts/v13_agente.md` |
| 14. Skills del proyecto (specs 014) | ✅ Hecha | `.opencode/skills/` y `make skills-check` |
| 15. Herramientas de dominio (specs 015) | ✅ Hecha | 20 herramientas en `src/taaml/agente.py` |
| 16. OpenClaw versionado (specs 016) | ✅ Hecha | `openclaw/`, workspace y puente MCP |
| 17. WhatsApp público (specs 017) | ✅ Hecha | Canal de OpenClaw con QR, allowlist abierta (D54) y panel |
| 18. Atajos de intención (specs 018) | ✅ Hecha | `src/taaml/atajos.py` en el chat web y el puente |
| 19. Pendientes persistentes (specs 019) | ✅ Hecha | Índice de aprobaciones en el Store (D77) |

## 3. Stack técnico

| Categoría | Tecnología |
|-----------|------------|
| **Lenguaje** | Python 3.12 |
| **Gestor de paquetes y entorno** | [`uv`](https://docs.astral.sh/uv/) |
| **Build backend** | `uv_build` (src-layout, paquete `taaml`) |
| **HTTP y scraping** | `requests` + `beautifulsoup4` + `lxml` |
| **Orquestación de LLM** | LangChain 1.x (`create_agent`) sobre LangGraph; `langchain-google-genai` y `langchain-openai` |
| **Modelo por defecto** | `deepseek-flash` (DeepSeek-V4.1-Flash-1017) en Q&A, Resumen, FAQ y agente; respaldo `deepseek-v4-pro` (nube) y, en la app del Taller 1, la respuesta guardada |
| **Modelo del agente** | `deepseek-flash` (API de pago); respaldo `gemini-3.8-flash` y `deepseek-v4-pro`, ambos en la nube (D51) |
| **Embeddings** | `gemini-embedding-001` (API de Google, 768 dimensiones; D51) |
| **Base vectorial** | Qdrant en modo local (persistente, sin servidor), similitud del coseno |
| **Memoria** | `PostgresSaver` (conversación) y `PostgresStore` (perfil y pendientes) con `DATABASE_URL`; SQLite como alternativa en `make api-sqlite` |
| **Interfaz** | API FastAPI + frontend React (`api/`, `frontend/`, Módulos 2 y 3); Streamlit solo para el Taller 1 (`app/`) |
| **Canal de WhatsApp** | Gateway de OpenClaw con plugin `puente-celsia` y puente MCP (`openclaw/`); webhook de Meta en el código, sin uso en la demo |
| **MCP** | Servidor propio de solo lectura con 10 herramientas (`src/taaml/servidor_mcp.py`) y puente de escritura (`src/taaml/puente_mcp.py`) |
| **Testing** | `pytest` (591 aprobadas y 2 omitidas, 593 en total, sin modelos ni red; 28/11/2026) |
| **Linting** | Ruff (`F`, `E9`) + `uv lock --check` |
| **CI/CD** | GitHub Actions (`.github/workflows/ci.yml`) |

> ⚠️ **Regla dura:** toda gestión de dependencias y entornos pasa por `uv`. Está
> **prohibido** `pip`, `requirements.txt` y `conda`.

> 📝 **Decisión sobre el modelo:** `gemini-3.6-flash` se descartó porque ignora
> `temperature` y `top_p`; la regla del proyecto es `temperature = 0.0` y `top_p = 0.1`.

## 4. Estructura del repositorio

```text
taaml-celsia-asistente/
├── src/taaml/                # código del asistente (src-layout)
│   ├── base.py               # lectura de la base de conocimiento
│   ├── recuperacion.py       # embeddings, Qdrant y búsqueda por palabras
│   ├── sinonimos.py          # diccionario cliente → sitio
│   ├── reordenar.py          # reordenamiento opcional de candidatos
│   ├── validacion.py         # cifras, correos y enlaces sin respaldo
│   ├── respaldo.py           # cadena de modelos y respuestas guardadas
│   ├── agente.py             # agente con memoria, 20 herramientas, aprobación humana y router (DeepSeek)
│   ├── aprobaciones.py       # pendientes de aprobación persistidos en el Store (D77)
│   ├── atajos.py             # saludos, agradecimientos y ayuda sin llamar al modelo
│   ├── actividad.py          # panel en vivo de la demostración
│   ├── avisos_openclaw.py    # envío de la decisión al cliente por OpenClaw
│   ├── citas.py              # respuesta a «fuente» con lo recuperado
│   ├── consulta_datos.py     # sedes, contactos y catálogo con filtros exactos
│   ├── conversaciones.py     # lectura de conversaciones para el análisis t-SNE
│   ├── errores.py            # mensajes corteses sin detalles internos
│   ├── flujo_reclamo.py      # StateGraph de ejemplo con interrupt
│   ├── informacion_manual.py # datos escritos a mano con su fuente
│   ├── openclaw.py           # validación de la plantilla y del workspace
│   ├── puente_mcp.py         # MCP de escritura: atender_cliente_celsia
│   ├── sanitizar.py          # limpieza de caracteres invisibles
│   ├── servicios_celsia.py   # datos estructurados de sedes y canales
│   ├── servidor_mcp.py       # MCP de solo lectura con 10 herramientas
│   ├── skills.py             # validación de skills
│   ├── prompts.py            # armado del prompt (5 bloques + XML)
│   ├── corpus.py             # métricas del pipeline para la app
│   ├── tareas.py             # Q&A, resumen y FAQ
│   ├── limite.py             # límite de mensajes por teléfono
│   ├── voz.py                # notas de voz (tentativo, apagado)
│   ├── whatsapp.py           # webhook de WhatsApp: firma, mensajes y envío
│   └── vectorstore.py        # QdrantVectorStore y embeddings nativos de LangChain
├── scripts/                  # 01–49: pipeline, pruebas, análisis, demo y chequeos (orden de uso)
│   └── utilidades/           # herramientas sueltas (PDF, claves)
├── data/                     # capas Medallion
│   ├── 0_manual/             # único lugar de datos escritos a mano, con fuente
│   ├── 1_bronze/             # HTML crudo (no versionado) + índice de capturas
│   ├── 2_silver/             # texto limpio y registros de descarte
│   ├── 3_gold/               # Markdown con front matter + catálogo
│   ├── 4_curaduria/          # base final, chunks, registro e índice vectorial
│   └── 5_extraccion/         # JSONL de contactos
├── prompts/                  # prompts versionados (nunca se editan: se versionan)
├── docs/                     # análisis, conjunto de prueba, informes, capturas, diagramas (Archify)
├── specs/                    # especificaciones 001–019 (spec, plan, tareas)
├── tests/                    # pruebas automáticas de componentes
│   └── e2e/                  # revisión con Playwright (make qa)
├── .specify/memory/          # este archivo — verdad central
├── .github/                  # plantillas de PR e issues, CI, Dependabot y etiquetas
├── .opencode/skills/         # skills para OpenCode (una carpeta por skill con SKILL.md)
├── api/                      # API FastAPI del agente (Módulos 2 y 3)
├── frontend/                 # interfaz React + Vite (Módulo 2)
├── openclaw/                 # plantilla del gateway, workspace y plugin del puente
├── notebooks/                # análisis de conversaciones con t-SNE (Módulo 3)
├── app/                      # aplicaciones Streamlit del Taller 1 (puntos de entrada, no librería)
│   ├── asistente.py          # app completa: Q&A, Resumen, FAQ y Corpus
│   └── modulo1.py            # app del Módulo 1: solo corpus y scraping
├── CONSTITUTION.md           # puntero a este archivo (el estándar del curso la pide en la raíz)
├── CONTRIBUTING.md           # ramas, commits y proceso de PR
├── CODE_OF_CONDUCT.md        # normas de convivencia
├── AGENTS.md                 # contexto y reglas para agentes LLM
├── Makefile                  # menú de atajos (interfaz única)
├── pyproject.toml            # metadatos y dependencias (uv)
├── uv.lock                   # lockfile determinista (versionado)
├── .mailmap                  # une nombres y correos de cada contribuidor
├── .editorconfig             # estilo común entre editores
└── .python-version           # versión de Python fijada
```

## 5. Convenciones de código

- **Estilo:** PEP 8 y PEP 257, con Ruff (`line-length = 100`).
- **Nomenclatura:** `snake_case` (funciones/variables), `PascalCase` (clases),
  `UPPER_CASE` (constantes). Los nombres de archivos, variables y constantes **nunca**
  llevan tildes; el texto para personas y el código de `src/`, `app/` y `frontend/` sí.
- **Idioma:** UI, documentación, prompts y commits en español; identificadores en inglés
  cuando el dominio lo pide (p. ej. `chunk`, `hash`).
- **Docstrings** en módulos, clases y funciones públicas.
- **Reglas propias:**
  - `data/1_bronze`, `2_silver` y `3_gold` **se generan con los scripts; no se editan a mano.**
  - `data/0_manual/` es el único lugar de datos escritos a mano, siempre con su fuente.
  - Un cambio de prompt es una **versión nueva** (`prompts/vN_*.md`), no una edición.
  - Toda cifra, teléfono o enlace que responda el asistente debe existir en la base.
  - Los saludos, agradecimientos, despedidas y la ayuda se responden con reglas (`atajos.py`) y no se guardan en el historial; si el mensaje trae contenido, sigue al agente.
  - Del teléfono se guarda un hash, nunca el número. El perfil tiene un máximo de 20 datos por cliente y el cliente puede consultarlos y borrarlos.
  - La demo de WhatsApp va por OpenClaw (D56); el webhook de Meta se conserva en el código, pero no es el canal de la sustentación.
  - Los pendientes de aprobación se guardan en el Store (D77); las respuestas sin entregar siguen en memoria.
  - `temperature = 0.0` y `top_p = 0.1` en RAG y agentes. **Excepción:** DeepSeek (`deepseek-flash`, en el agente y en las tareas) respeta `temperature` con el razonamiento apagado, pero deja `top_p` fijo en 1,0; se compensa con las herramientas, la validación de datos sin respaldo y el «No tengo esa información».
  - Las skills viven en `.opencode/skills/<nombre>/SKILL.md` (solo OpenCode); `make skills-check` valida frontmatter, nombre, tamaño y seguridad, y el CI lo exige.

## 6. Calidad y automatización

| Herramienta | Rol | Comando |
|-------------|-----|---------|
| `uv` | Entornos y dependencias | `make setup` / `uv sync` |
| Ruff | Errores de código | `make lint` |
| `uv lock --check` | Lock vigente | `make lint` |
| `pytest` | Pruebas de componentes | `make test` |
| `scripts/16_ensayo_demo.py` | Chequeo previo a la demo | `make ensayo` |
| `scripts/verificar_skills.py` | Frontmatter, tamaño y seguridad de las skills | `make skills-check` |
| Playwright | Revisión del chat web como una persona | `make qa` |
| `scripts/45_verificar_clon.py` | Un clon limpio se instala y arranca | `make verificar-clon` |
| GitHub Actions | CI en cada PR y push a `main` | `.github/workflows/ci.yml` |

- La **CI debe estar en verde** antes de fusionar un Pull Request.
- Las pruebas no llaman a ningún modelo: la suite corre sin red y sin cuota.
- Toda dependencia nueva entra con `uv add` / `uv add --dev` (nunca editando `uv.lock`).

## 7. Repositorio y Git

- **Remoto:** `https://github.com/mariastefuentes/taaml-celsia-asistente`
- **Rama principal:** `main`
- **Estrategia de ramas:** `feat/...`, `fix/...`, `docs/...`, `refactor/...`, `test/...`,
  `chore/...`; integración vía Pull Request con la plantilla de `.github/`.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) en español —
  `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, con el **porqué** en el cuerpo.
- **Revisión:** el Code Reviewer del grupo aprueba el PR; en la sustentación del Módulo 1
  (grupo 4) revisa el profesor.

## 8. Flujo diario (commit + push)

```bash
# 1. Ver cambios
git status

# 2. Verificación completa (lint + pruebas)
make lint
make test

# 3. Commit semántico en español
git add -A
git commit -m "tipo: mensaje descriptivo"

# 4. Rama y Pull Request (nunca directo a main)
git push -u origin feat/mi-cambio
```

## 9. Historial de decisiones técnicas

> El registro completo, con alternativa descartada y límites, está en [`docs/decisiones.md`](../../docs/decisiones.md) (D1 a D77). Aquí se conservan los hitos que cambiaron la arquitectura; las filas son históricas y no describen necesariamente el estado vigente (el estado vigente está en las secciones 3 y 4).

| Fecha | Decisión | Motivo |
|-------|----------|--------|
| 2026-10-17 | Adoptar `uv` como gestor único | Reproducibilidad; prohibido `pip`/`requirements.txt` |
| 2026-10-17 | Patrón Medallion con Silver, Gold y curaduría versionados | Reproducir sin volver a la web; Bronze pesa ~250 MB |
| 2026-10-17 | Respetar `robots.txt` y no descargar PDF | Requisito legal y del curso |
| 2026-10-24 | Descartar `trafilatura` y limpiar con BeautifulSoup + reglas | Conserva tarjetas y acordeones institucionales |
| 2026-10-28 | Embeddings locales con `nomic-embed-text-v2-moe` + Qdrant (antes Chroma, ver specs/012) | Sin costo y sin enviar el corpus a terceros |
| 2026-10-29 | RAG (12 fragmentos) en lugar de pegar la base completa | ~80 veces menos costo por pregunta |
| 2026-10-29 | Prompt v3 con cinco bloques y etiquetas XML | Defensa del rol y contra inyección |
| 2026-10-30 | `gemini-3.5-flash` como modelo vigente | Respeta `temperature` y `top_p`; el 3.6 no |
| 2026-10-30 | Cadena de respaldo y respuestas guardadas | La demo no se cae por cuota o conexión |
| 2026-10-30 | El respaldo reconoce 401/403 como falla del proveedor | Una clave inválida o sin permisos no debe impedir DeepSeek ni el modelo local |
| 2026-10-30 | `app_modulo1.py` para la sustentación | Muestra solo lo que evalúa la rúbrica; el resto queda en `app.py` |
| 2026-11-05 | Las apps pasan a `app/asistente.py` y `app/modulo1.py` | La raíz queda para configuración y documentos; `src/taaml` sigue siendo solo la librería |
| 2026-11-07 | Limpiar el historial de `main`: quitar la línea de coautoría de los mensajes y unir un correo duplicado | Pedido del profesor sobre los contribuidores; el código no cambió (mismo árbol), solo los identificadores de commit |
| 2026-11-07 | `.mailmap` con una identidad por persona | `git shortlog` muestra cuatro contribuidores, sin duplicados |
| 2026-11-07 | Diagramas con Archify (`docs/arquitectura.*` y `docs/pipeline.*`) en lugar de Mermaid | Estándar del curso (skill `jan-project-standard`): un diagrama por pregunta, JSON como fuente |
| 2026-11-07 | Adoptar de la skill la gobernanza (plantillas de issues, Dependabot, etiquetas, CONTRIBUTING, código de conducta) y `make check` | Cumple el estándar sin tocar el código |
| 2026-11-07 | No adoptar Python 3.13, Ruff completo ni Squash & Merge | GGA es el guardián de commits del curso; 3.12 es válido; la rúbrica evalúa los commits individuales (se fusiona con merge commit) |
| 2026-11-08 | El agente usa `gemini-3.8-flash` (API de pago) con respaldo `ollama:llama3.2`; las tres tareas del Taller 1 siguen con 3.5 | Indicación del profesor de usar API de pago y un modelo reciente; el 3.5 es el que se evaluó |
| 2026-11-08 | Memoria con `InMemorySaver` y `thread_id` por conversación (en RAM) | Cumple la Fase 2; guardarla en disco es de la Fase 3 |
| 2026-11-08 | Router por prompt (`prompts/v2_agente.md`): el agente elige entre `buscar_en_base` y `consultar_datos` | Más simple que un clasificador aparte y coincide con el RAG Agent de la Clase 9 |
| 2026-11-08 | Tag `taller-1` sobre el `main` sustentado | Conservar el estado exacto de la primera entrega |
| 2026-11-08 | Mantener `gemini-3.8-flash` en el agente aunque ignora `temperature` y `top_p` | El profesor pidió un modelo reciente de pago; el 3.5 sí los respeta pero va de baja. Las defensas contra datos inventados no dependen de la temperatura |
| 2026-11-14 | Prompt del agente v4 (`prompts/v4_agente.md`): respuesta solo en texto plano y rechazo amable de JSON, XML, YAML, HTML, CSV, SQL y tablas | El cliente debe recibir palabras normales, no formatos de programación |
| 2026-11-15 | `deepseek-flash` (DeepSeek-V4.1-Flash-1017, API de pago) en el agente y en las tres tareas del Taller 1 (Q&A, Resumen y FAQ), además del flujo de reclamo; respaldo `ollama:llama3.2` | DeepSeek respeta `temperature` con el razonamiento apagado y su API es OpenAI-compatible; `deepseek-flash` es el ID vigente de la versión V4.1 Flash 1017 |
| 2026-11-18 | Prompt del agente v5 (`prompts/v5_agente.md`) y aprobación humana: `radicar_reclamo` se pausa con `HumanInTheLoopMiddleware` hasta que una persona decide en `POST /aprobar` | Radicar un reclamo cambia algo fuera de la conversación; el agente prepara la acción y un humano la aprueba. Matriz de enrutamiento con el prompt v5: 32 de 33 |
| 2026-11-18 | Prompt del agente v6 (`prompts/v6_agente.md`): las preguntas ajenas a Celsia no se responden, aunque sean sencillas | Con v5 el agente contestaba trivias con su conocimiento propio (3 de 10 preguntas ajenas: una capital, una suma). Con v6 se rechazaron 10 de 10, en los dos modos de RAG, y 8 de 8 preguntas de Celsia, saludos y despedidas siguieron bien. Matriz de enrutamiento con v6: 32 de 33 (igual que con v5) |
| 2026-11-18 | Prompt del agente v7 (`prompts/v7_agente.md`): los temas de energía se buscan aunque no nombren a Celsia, y si una herramienta falla no se dice que algo quedó guardado | El análisis de conversaciones simuladas (PR de t-SNE) mostró 2 de 114 rechazos erróneos de preguntas de energía («¿Qué es la energía renovable?» se rechazó sin buscar) y una prueba anterior con el Store caído en la que el agente dijo «ya guardé». Con v7 y el agente real: 7 de 8 preguntas de energía respondidas con búsqueda (la octava, sobre medidores inteligentes, dijo con honestidad que no hay información), 10 de 10 preguntas ajenas rechazadas, 6 de 6 respuestas honestas con el Store caído y matriz de enrutamiento 32 de 33 (igual que con v6) |
| 2026-11-21 | Las skills (`corpus-medallion` y `agente-rag-router`) se migran a `.opencode/skills/` y se validan con `make skills-check` y el CI; solo OpenCode, y `mariastefuentes/taaml-skills` queda como espejo | Quien clona el proyecto debe tener las skills, el CI debe validarlas y la revisión del curso debe verlas; el equipo usa solo OpenCode (D24) |
| 2026-11-21 | El agente busca con mezcla de significado y palabras; ranking k=10 medido | Rescata el dato que el significado deja lejos; nDCG@10 empata con embeddings (D31) |
| 2026-11-21 | Servidor MCP propio (solo lectura, stdio) con las dos herramientas de consulta | Reutilizar el agente en clientes MCP sin abrir puertos (D32) |
| 2026-11-21 | pre-commit (ruff, lock, `.env`) y `make tipos` con ty informativo | Detectar en local lo que el CI ve tarde; ty aún no bloquea (D33) |
| 2026-11-22 | Métricas de la Parte 1 (D34): hit, MRR y nDCG@4 con Wilson y McNemar; la mezcla no se distingue de embeddings en 35 preguntas | Medir con rigor, no por impresión: 25/35 vs 26/35, p = 1,0 |
| 2026-11-22 | OpenClaw como segundo cliente del MCP, con identidad, permisos endurecidos y sandbox Docker (D35) | El Taller 3 pide un cliente propio del MCP; la configuración vive fuera del repositorio |
| 2026-11-22 | Matriz de enrutamiento ampliada de 33 a 43 preguntas; 42/43 (D36) | Cubre trámites, inglés, datos mezclados, fuga del prompt y fuera de dominio; R31 sigue como límite |
| 2026-11-22 | Asesor humano: sin herramienta nueva; el agente deriva a los canales oficiales (D37) | Una sexta herramienta obligaría a cambiar el prompt v9 y el camino de WhatsApp por poca ganancia |
| 2026-11-22 | Diagrama de arquitectura regenerado con Archify: prompt v9, mezcla, MCP y OpenClaw (D38) | El diagrama de punta a punta estaba desactualizado; se validó y se revisó a ojo |
| 2026-11-18 a 2026-11-26 | De 5 a 20 herramientas tipadas, con `consultar_datos` retirada del agente (D41 a D46) | La rúbrica exige 20 herramientas; el modelo ve solo los campos de la tabla que consulta |
| 2026-11-24 | OpenAI-compatible DeepSeek (`deepseek-flash`), embeddings `gemini-embedding-001` y sin modelos locales (D51) | Cumple el anuncio de usar API en la nube y un modelo reciente |
| 2026-11-24 | El WhatsApp de la demo va por OpenClaw, no por el webhook de Meta (D56) | El gateway aporta canal, sandbox y controles; Meta solo se probó con su número de prueba |
| 2026-11-26 | Medición final con las 20 herramientas: banco 49/49, matriz 40/43, ataques 11/11 y órdenes 8/8 (D67) | Citar cifras fechadas y no mezclar mediciones de prompts anteriores |
| 2026-11-27 | Revisión con Playwright antes de cada push (D74) | El Anuncio 008 pide auditar el flujo del pitch en el navegador |
| 2026-11-27 | Atajos de intención sin llamar al modelo (D76) | Ahorra cuota y latencia en saludos, agradecimientos, despedidas y ayuda |
| 2026-11-28 | Los pendientes de aprobación se guardan en el Store (D77) | El panel no queda vacío al reiniciar la API; la conversación pausada se puede aprobar |

## 10. Notas y tareas pendientes

- [ ] Validar en el computador del bot: canal de WhatsApp vinculado, `openclaw security audit` guardado y aviso de aprobación.
- [ ] Repetir `make qa` (Playwright) en el computador del bot; la corrida general ya se hizo el 27/11.
- [ ] Desplegar en un servidor dedicado (hoy corre en el computador de la demo) y probar carga con muchas personas a la vez.
- [ ] Integrar los reclamos con los sistemas de Celsia; hoy son simulados.
- [ ] Desplegar en Hugging Face Spaces (deseable de la rúbrica del Taller 1).
- [ ] Reescribir la consulta con el modelo antes de buscar.
- [ ] Ampliar las pruebas de inyección con ataques más difíciles.
- [ ] Incorporar los PDF de Celsia si la empresa autoriza el acceso.
- [ ] Repetir la evaluación tres veces por prompt para separar v1 y v3 con evidencia.

## 11. Configuración local y secretos

> Configuración específica de la máquina. **NO incluir en commits.**

- Las claves viven en `.env` (ignorado por Git) y se documentan vacías en `.env.example`:
  `GOOGLE_API_KEY`, `DEEPSEEK_API_KEY`, `LANGSMITH_API_KEY`, `DATABASE_URL`, `CHAT_TOKEN`,
  `APROBADOR_TOKEN`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_APP_SECRET`,
  `WHATSAPP_VERIFY_TOKEN`, `OPENCLAW_GATEWAY_TOKEN` y las variables de OpenClaw que documenta
  `docs/guia_despliegue_openclaw.md`. `HF_TOKEN` solo se usa si se publica en Hugging Face.
- `data/1_bronze/` (HTML crudo), `data/4_curaduria/qdrant/`,
  `data/4_curaduria/indice_embeddings.npz`, `data/_demo_scraping/` y los PDF
  **no se versionan**: se regeneran con `make datos`, `make indice` y `make pdf`.
- En Windows conviene clonar en una ruta corta, fuera de OneDrive, con
  `git config --global core.longpaths true` y `UV_LINK_MODE=copy` si `uv sync` falla.
