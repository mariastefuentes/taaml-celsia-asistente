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
| **Descripción** | Base de conocimiento y asistente de preguntas y respuestas (Q&A, resumen y FAQ) sobre información pública de Celsia, con RAG. |
| **Repositorio** | https://github.com/mariastefuentes/taaml-celsia-asistente |
| **Autoría** | María Stella Fuentes, Juan José Mosquera, Nicolás Bolaños y Jensen Fabián Tamayo — Grupo 4 |
| **Curso** | Técnicas avanzadas de IA aplicadas en modelos de lenguaje (Maestría en IA y Ciencias de Datos, UAO, 2026-2S) |
| **Licencia** | MIT |
| **Rama principal** | `main` |
| **Estado** | Operativo 🟢 (Taller 1 del Módulo 1) |

## 1. Propósito y no-propósito

### Propósito

Convertir el sitio público de **celsia.com** en un corpus Markdown citable y reproducible
(patrón Medallion: Bronze → Silver → Gold → curaduría → fragmentos) y responder preguntas
de clientes **solo con ese corpus**, citando la fuente y diciendo «no sé» cuando la
respuesta no está en la base.

### No-propósito

No es un asistente general ni un buscador abierto de internet: no inventa datos, no
consulta fuentes distintas de las versionadas y no responde con conocimiento del modelo.
Tampoco es un *crawler* del dominio completo, ni procesa datos personales de clientes
(Ley 1581), ni atraviesa formularios o sesiones autenticadas.

## 2. Alcance

### Dentro del alcance

- Capturar con un `User-Agent` propio, `timeout`, pausa entre peticiones y respeto de
  `robots.txt` y `sitemap.xml` (los PDF de celsia.com están bloqueados: no se descargan).
- Mantener las capas **Bronze** (HTML crudo), **Silver** (texto limpio, sin duplicados) y
  **Gold** (Markdown con *front matter* y catálogo).
- Curar la base con reglas explícitas y registrar cada descarte con su motivo.
- Fragmentar (`chunks.jsonl`), indexar con embeddings locales y recuperar los 12 fragmentos
  más relevantes por pregunta (RAG).
- Responder con **Q&A, resumen y FAQ** con prompts versionados y salida estructurada.
- Ofrecer una app Streamlit y un `Makefile` como interfaz única del proyecto.

### Fuera del alcance (por ahora)

- PDFs, vídeos y transcripciones de celsia.com (bloqueados por `robots.txt`).
- Datos de clientes o cualquier información no pública.
- Despliegue en producción y autenticación de usuarios finales.
- Agentes autónomos más allá del agente de la spec 011 (memoria en RAM, dos herramientas); la persistencia y los canales son la Fase 3.

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
| 13. Agente en producción con WhatsApp (specs 013) | ✅ Código fusionado; falta la prueba con Meta real | `api/main.py`, `src/taaml/whatsapp.py`, `limite.py`, `prompts/v7_agente.md` |

## 3. Stack técnico

| Categoría | Tecnología |
|-----------|------------|
| **Lenguaje** | Python 3.12 |
| **Gestor de paquetes y entorno** | [`uv`](https://docs.astral.sh/uv/) |
| **Build backend** | `uv_build` (src-layout, paquete `taaml`) |
| **HTTP y scraping** | `requests` + `beautifulsoup4` + `lxml` |
| **Orquestación de LLM** | LangChain (`langchain`, `langchain-google-genai`, `langchain-openai`, `langchain-ollama`) |
| **Modelo por defecto** | `deepseek-flash` (Q&A, Resumen y FAQ); respaldo `ollama:llama3.2` |
| **Modelo del agente** | `deepseek-flash` (DeepSeek-V4.1-Flash-1017, API de pago); respaldo `gemini-3.8-flash` y `ollama:llama3.2` |
| **Embeddings** | `nomic-embed-text-v2-moe` en Ollama (local, sin costo) |
| **Base vectorial** | Qdrant en modo local (persistente, sin servidor), similitud del coseno |
| **Interfaz** | API FastAPI + frontend React (`api/`, `frontend/`, Módulo 2); Streamlit solo para el Taller 1 (`app/`) |
| **Testing** | `pytest` (315 pruebas, sin modelos ni red) |
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
│   ├── agente.py             # agente con memoria, cinco herramientas, aprobación humana y router (DeepSeek)
│   ├── whatsapp.py           # webhook de WhatsApp: firma, mensajes y envío
│   ├── limite.py             # límite de mensajes por teléfono
│   ├── conversaciones.py     # lectura de las conversaciones guardadas para el análisis t-SNE
│   ├── vectorstore.py        # QdrantVectorStore y embeddings nativos de LangChain
│   ├── consulta_datos.py     # sedes, contactos y catálogo con filtros exactos
│   ├── prompts.py            # armado del prompt (5 bloques + XML)
│   ├── corpus.py             # métricas del pipeline para la app
│   └── tareas.py             # Q&A, resumen y FAQ
├── scripts/                  # 01–38: etapas del pipeline, pruebas, análisis y plan B de la demo (orden de uso)
│   └── utilidades/           # herramientas sueltas (PDF, claves)
├── data/                     # capas Medallion
│   ├── 0_manual/             # único lugar de datos escritos a mano, con fuente
│   ├── 1_bronze/             # HTML crudo (no versionado) + índice de capturas
│   ├── 2_silver/             # texto limpio y registros de descarte
│   ├── 3_gold/               # Markdown con front matter + catálogo
│   ├── 4_curaduria/          # base final, chunks, registro e índice vectorial
│   └── 5_extraccion/         # JSONL de contactos
├── prompts/                  # prompts versionados (nunca se editan: se versionan)
├── docs/                     # análisis, conjunto de prueba, informe, capturas y diagramas (Archify)
├── specs/                    # especificaciones 001–013 (spec, plan, tareas)
├── tests/                    # pruebas automáticas de componentes
├── .specify/memory/          # este archivo — verdad central
├── .github/                  # plantillas de PR e issues, CI, Dependabot y etiquetas
├── api/                      # API FastAPI del agente (Módulo 2)
├── frontend/                 # interfaz React + Vite (Módulo 2)
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
  - `temperature = 0.0` y `top_p = 0.1` en RAG y agentes. **Excepción:** DeepSeek (`deepseek-flash`, en el agente y en las tareas) respeta `temperature` con el razonamiento apagado, pero deja `top_p` fijo en 1,0; se compensa con las herramientas, la validación de datos sin respaldo y el «No tengo esa información».

## 6. Calidad y automatización

| Herramienta | Rol | Comando |
|-------------|-----|---------|
| `uv` | Entornos y dependencias | `make setup` / `uv sync` |
| Ruff | Errores de código | `make lint` |
| `uv lock --check` | Lock vigente | `make lint` |
| `pytest` | Pruebas de componentes | `make test` |
| `scripts/16_ensayo_demo.py` | Chequeo previo a la demo | `make ensayo` |
| GitHub Actions | CI en cada PR y push a `main` | `.github/workflows/ci.yml` |

- La **CI debe estar en verde** antes de fusionar un Pull Request.
- Las pruebas no llaman a Gemini ni a Ollama: la suite corre sin red y sin cuota.
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
| 2026-11-07 | No adoptar pre-commit, Python 3.13, Ruff completo ni Squash & Merge | GGA es el guardián de commits del curso; 3.12 es válido; la rúbrica evalúa los commits individuales (se fusiona con merge commit) |
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

## 10. Notas y tareas pendientes

- [ ] Desplegar en Hugging Face Spaces (deseable de la rúbrica).
- [ ] Reescribir la consulta con el modelo antes de buscar.
- [ ] Ampliar las pruebas de inyección con ataques más difíciles.
- [ ] Incorporar los PDF de Celsia si la empresa autoriza el acceso.
- [ ] Repetir la evaluación tres veces por prompt para separar v1 y v3 con evidencia.

## 11. Configuración local y secretos

> Configuración específica de la máquina. **NO incluir en commits.**

- Las claves viven en `.env` (ignorado por Git) y se documentan vacías en `.env.example`:
  `GOOGLE_API_KEY`, `DEEPSEEK_API_KEY`, `HF_TOKEN` y `LANGSMITH_API_KEY`.
- `data/1_bronze/` (HTML crudo), `data/4_curaduria/qdrant/`,
  `data/4_curaduria/indice_embeddings.npz`, `data/_demo_scraping/` y los PDF
  **no se versionan**: se regeneran con `make datos`, `make indice` y `make pdf`.
- En Windows conviene clonar en una ruta corta, fuera de OneDrive, con
  `git config --global core.longpaths true` y `UV_LINK_MODE=copy` si `uv sync` falla.
