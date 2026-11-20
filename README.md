# ⚡ Asistente virtual de Celsia

[![CI](https://github.com/mariastefuentes/taaml-celsia-asistente/actions/workflows/ci.yml/badge.svg)](https://github.com/mariastefuentes/taaml-celsia-asistente/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
![uv](https://img.shields.io/badge/gestor-uv-5C2D91)
![LangChain](https://img.shields.io/badge/LangChain-1.x-1C3C3C)
![Streamlit](https://img.shields.io/badge/Taller%201-Streamlit-FF4B4B)
![React](https://img.shields.io/badge/M%C3%B3dulo%202-React%20%2B%20FastAPI-61DAFB)
![WhatsApp](https://img.shields.io/badge/M%C3%B3dulo%203-WhatsApp%20%2B%20PostgreSQL-25D366)
[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-green.svg)](LICENSE)

Base de conocimiento y agente conversacional sobre **Celsia**, empresa de energía del Valle del Cauca y el Tolima. Responde **solo con información oficial de celsia.com** y dice «no sé» cuando la fuente no lo trae. El Módulo 1 construyó el corpus y el Q&A (resumen y FAQ); el Módulo 2 lo convirtió en un agente con memoria, herramientas, router y blindaje, servido por una API y un frontend propio; el Módulo 3 lo llevó a producción: memoria en PostgreSQL, herramientas con esquemas estrictos, aprobación humana para los reclamos y un servidor propio que atiende a los clientes por WhatsApp. Curso *Técnicas avanzadas de IA aplicadas en modelos de lenguaje* (Maestría en IA y Ciencias de Datos, UAO, 2026-2S).

## Problema y solución

**Problema de información.** La información pública de Celsia está repartida en más de mil páginas de celsia.com, y no hay un lugar donde preguntar y recibir la respuesta con su fuente.

**Solución.** Un sistema de **RAG** (generación aumentada por recuperación): se descarga y limpia el sitio, se divide en fragmentos, y para cada pregunta se buscan los 12 más parecidos por significado (embeddings en una base vectorial Qdrant). Solo esos fragmentos van al prompt, con instrucciones que obligan a responder con ellos y a citar la fuente.

| Resultado medido | Valor |
|---|---|
| Corpus curado | 393 documentos, 1.690 fragmentos, ~316.800 tokens |
| Recuperación (la respuesta está entre los 12 fragmentos) | 89 % con embeddings (54 % por palabras, 74 % híbrido). El 89 % se midió con las mismas preguntas que motivaron el diccionario de sinónimos: con preguntas nuevas sería menor |
| Preguntas de prueba | 59 (35 con respuesta y 24 que no deben responderse), 4 de inyección |
| Respuestas correctas (Taller 1, con `gemini-3.5-flash`) | Según el juez automático: 31 de 35 con respuesta y 21 de 24 negativas bien resueltas. Con la revisión asistida: 29 de 35 y 19 de 24. Los veredictos de la revisión los propuso el asistente de código y los ratificó María Stella Fuentes |
| Costo frente a pegar toda la base en el prompt | unas 80 veces menor por pregunta |

El detalle y las limitaciones están en el [informe del Taller 1](docs/3%20-%20Informe/informe_taller1.md); el agente del Taller 2, en su [informe](docs/3%20-%20Informe/informe_taller2.md); y las decisiones de arquitectura (D1 a D19), con su porqué, en [docs/decisiones.md](docs/decisiones.md).

## Arquitectura

[![Arquitectura de la aplicación](docs/capturas/arquitectura.png)](docs/arquitectura.html)

Esta es la arquitectura del Taller 1 (Streamlit). La del agente actual, de WhatsApp a la respuesta, está más abajo, en [Agente (Módulos 2 y 3)](#agente-módulos-2-y-3).

El diagrama es interactivo: abre [docs/arquitectura.html](docs/arquitectura.html) (fuente en [docs/arquitectura.json](docs/arquitectura.json)). La preparación de los datos, de celsia.com a los fragmentos indexados, tiene su propio diagrama:

[![Pipeline de datos](docs/capturas/pipeline.png)](docs/pipeline.html)

Interactivo en [docs/pipeline.html](docs/pipeline.html) (fuente en [docs/pipeline.json](docs/pipeline.json)). Los HTML se generan con Archify desde el JSON y no se editan a mano.

### Agente (Módulos 2 y 3)

El agente (`create_agent` de LangChain) decide en cada turno qué herramienta usar mediante **function calling**: el modelo recibe las herramientas con su esquema (JSON Schema generado desde Pydantic) y responde con una llamada estructurada (nombre y argumentos), que Pydantic valida antes de ejecutar; el prompt solo lo guía. No hay enrutamiento por texto libre. Habla con el cliente por una API FastAPI con streaming, y un frontend React independiente la consume.

[![Arquitectura de punta a punta, de WhatsApp a la respuesta](docs/capturas/arquitectura_agente.png)](docs/arquitectura_agente.html)

Diagrama interactivo: [docs/arquitectura_agente.html](docs/arquitectura_agente.html) (fuente en [docs/arquitectura_agente.json](docs/arquitectura_agente.json), generado con Archify).

[![Enrutamiento por herramienta](docs/capturas/enrutamiento.png)](docs/enrutamiento.html)

Cómo elige el agente la herramienta. Interactivo en [docs/enrutamiento.html](docs/enrutamiento.html) (fuente en [docs/enrutamiento.json](docs/enrutamiento.json)).

[![Grafo del agente: el ciclo de un turno](docs/capturas/grafo_agente.png)](docs/grafo_agente.html)

El ciclo de un turno, con el resumen, la validación del reclamo, el tope de herramientas y la aprobación humana. Interactivo en [docs/grafo_agente.html](docs/grafo_agente.html) (fuente en [docs/grafo_agente.json](docs/grafo_agente.json)).

[![Memoria: checkpointer frente a Store](docs/capturas/memoria.png)](docs/memoria.html)

Qué guarda cada memoria y para qué. Interactivo en [docs/memoria.html](docs/memoria.html) (fuente en [docs/memoria.json](docs/memoria.json)).

![Traza real de LangSmith](docs/3%20-%20Informe/diagrama_traza_langsmith.svg)

Traza real de una pregunta al agente actual (DeepSeek, prompt v7), generada con `scripts/33_diagrama_traza_langsmith.py`.

[![Un mensaje de WhatsApp, paso a paso](docs/capturas/secuencia_whatsapp.png)](docs/secuencia_whatsapp.html)

El camino de un mensaje, del cliente a la respuesta. Interactivo en [docs/secuencia_whatsapp.html](docs/secuencia_whatsapp.html) (fuente en [docs/secuencia_whatsapp.json](docs/secuencia_whatsapp.json)).

Un reclamo no se radica solo: `radicar_reclamo` pausa el flujo con `HumanInTheLoopMiddleware` hasta que una persona de Celsia lo aprueba con `POST /aprobar`, y entonces el cliente recibe la decisión por WhatsApp. El frontend React sigue usando `POST /api/chat` (streaming) sobre la misma API y la misma memoria.

| Componente | Qué usa |
|---|---|
| Memoria corta | Checkpointer con `thread_id`: `PostgresSaver` en `make api`, SQLite en `make api-sqlite` (persiste entre reinicios) |
| Confianza baja | `buscar_en_base` antepone un aviso del sistema cuando el mejor fragmento tiene coseno < 0,40; el agente responde con cautela y remite a la línea de atención (`scripts/28_confianza_baja.py`) |
| Memoria en PostgreSQL | Con `DATABASE_URL` definida, el checkpointer y el Store son `PostgresSaver` y `PostgresStore` (grupo de conexiones que se reconecta solo; probados con un PostgreSQL local, `tests/test_memoria_postgres.py`, incluida una aprobación pendiente que sobrevive a un reinicio); sin ella, SQLite. `make api` ya arranca la API contra PostgreSQL (un PostgreSQL local persistente sin Docker, `scripts/34_postgres_local.py`, o el de `DATABASE_URL`), `make api-sqlite` usa SQLite, `make db-up` solo levanta el servidor local y `make db-down` lo apaga; `/api/salud` informa cuál memoria está en uso |
| Grafo del agente | `scripts/31_mostrar_grafo.py`: `create_agent` devuelve un StateGraph compilado; el script imprime sus nodos (8 nodos: el modelo, las herramientas y cuatro de middleware: resumen, validación del reclamo, aprobación humana y tope de llamadas), sus aristas condicionales y el estado, sin llamar a ningún modelo; el diagrama está en [docs/grafo_agente.html](docs/grafo_agente.html) |
| Traza de LangSmith | `scripts/33_diagrama_traza_langsmith.py`: lee de LangSmith (solo lectura) la traza más reciente de una pregunta y dibuja sus pasos, tiempos, tokens y argumentos de herramienta en `docs/3 - Informe/diagrama_traza_langsmith.svg`; necesita `LANGSMITH_API_KEY`, no llama a ningún modelo |
| Flujo con aprobación humana | `scripts/32_flujo_reclamo.py`: un StateGraph escrito a mano (`src/taaml/flujo_reclamo.py`) con `interrupt`: el reclamo se radica solo si una persona lo aprueba; salida estructurada con Pydantic; sin modelo ni costo (con `--real` usa DeepSeek) |
| Viaje en el tiempo | `scripts/27_viaje_en_el_tiempo.py`: historial de puntos de control, replay y fork de un hilo, con un modelo simulado (sin costo) |
| Memoria larga | Store con espacio `("perfil", usuario)`, máximo 20 datos por cliente, borrable por el cliente |
| Prompt y resumen | `@dynamic_prompt` (`con_fecha_de_hoy`) arma el prompt en cada turno con la fecha; `trim_messages` recorta lo que ve el modelo; `SummarizationMiddleware` resume la conversación guardada pasados 8.000 tokens |
| Cadena del Q&A (Taller 1) | `cadena_qa` en `src/taaml/tareas.py`: `RunnablePassthrough.assign` → `ChatPromptTemplate` → modelo → `StrOutputParser` |
| Datos estructurados | `consultar_datos`, con esquema Pydantic (`ConsultaDatos`) sobre sedes, contactos y catálogo |
| RAG agéntico o en cadena | Por defecto el agente decide cuándo llamar a `buscar_en_base` (RAG agéntico). Con `RAG_MODO=cadena` funciona como RAG en cadena: un `dynamic_prompt` (`con_contexto_recuperado`) recupera los fragmentos de la última pregunta y los inserta en el prompt de sistema antes de cada respuesta, y el agente deja de tener `buscar_en_base` (conserva `consultar_datos`, la memoria y el reclamo). Misma búsqueda, mismos delimitadores contra inyección y mismo aviso de baja confianza. En la comparación con 6 preguntas ambos respondieron bien; el modo en cadena recupera también para los saludos y, sin llamada a la herramienta, la pantalla no muestra tarjetas de fuentes |
| Herramientas estrictas y errores corteses | Las 5 herramientas tienen un esquema Pydantic (`args_schema`) que rechaza campos inventados y valida largos y valores permitidos; de él sale el JSON Schema que ve el modelo. Las que usan la memoria llevan `runtime` en el esquema, marcado `exclude`, porque LangChain lo necesita para inyectarlo; el modelo no lo ve. Si una herramienta falla (base o Ollama caídos), el middleware `errores_amables` le pasa al modelo un aviso sin detalles internos (que no pudo verificarlo ahora, que reintente o llame a la línea y que puede ayudarle con otra cosa) y el turno sigue; si la herramienta responde pero sin datos, el prompt manda decir «No tengo esa información» y remitir a la línea; las pausas de aprobación humana no se confunden con errores |
| RAG | `buscar_en_base`: 4 fragmentos del texto oficial (Qdrant + embeddings de Ollama) |
| Vectorstore y embeddings nativos de LangChain | `src/taaml/vectorstore.py`: `EmbeddingsCelsia` (subclase de `OllamaEmbeddings` con el prefijo de tarea y vectores normalizados) y `QdrantVectorStore` sobre la colección; la búsqueda por significado pasa por `similarity_search_with_score_by_vector`. Con los mismos 10 casos de prueba devolvió los mismos 12 fragmentos que la versión anterior. Si tu índice local es del formato anterior (sin texto en Qdrant), la búsqueda cae sola a la matriz `.npz`: corre `make indice` para reconstruirlo (usa los vectores en caché, sin recalcular) |
| Base vectorial | Qdrant local con alias `celsia` sobre colecciones versionadas (migración blue/green y `revertir_qdrant`), payload filtrable por `categoria` y `region`; `scripts/26_explorar_ann_y_filtros.py` mide IVF, PQ y pre/post-filtrado frente a la búsqueda exacta; `scripts/29_medir_hnsw_en_servidor.py` mide HNSW (`m`, `ef_construct`, `ef`) contra un servidor Qdrant en Docker |
| Exploración de embeddings | `scripts/25_explorar_embeddings.py`: coseno, producto punto y L2 (mismo orden con vectores de norma 1), recorte Matryoshka (512 dimensiones casi no pierde calidad) y mapa t-SNE en `docs/3 - Informe/tsne_corpus.svg` |
| Validación de la respuesta | `datos_dudosos` revisa que cada cifra, correo o enlace de la respuesta aparezca en lo que devolvieron las herramientas, lo que dijo el cliente o la fecha de hoy; si no, el frontend avisa «Verifica antes de usar» |
| Blindaje | Limpieza de caracteres invisibles, reglas del prompt y delimitadores `<documentos_recuperados>`. Con DeepSeek y el prompt v7 el detector automático dio 10 de 11 ataques directos y 6 de 8 indirectos; en los 3 marcados el agente rechazó el ataque y solo citó su texto (falsos positivos del detector, ver D6 en `docs/decisiones.md`), así que leídos a mano son 11 de 11 y 8 de 8 |
| Respaldo | Si DeepSeek falla: `gemini-3.8-flash` y después `llama3.2` local |
| Límite por teléfono | `src/taaml/limite.py`: 8 mensajes por minuto por teléfono (`LIMITE_MENSAJES`, `LIMITE_VENTANA_S`); `/chat` responde 429 con `Retry-After` y por WhatsApp se avisa una sola vez por ventana, sin llamar al modelo. Protege la cuota cuando el bot es público. `/api/chat` se limita por origen y `/chat` pide `X-Api-Key` si el servidor define `CHAT_TOKEN` |
| Panel en vivo | `GET /panel` (página) y `GET /api/actividad` (datos, con el token del aprobador): cada turno con canal, mensaje, herramientas, tiempo y estado. En memoria (últimos 200), con un identificador corto y nunca el número (`src/taaml/actividad.py`) |
| Aprobar con botones | Con `APROBADOR_WHATSAPP`, el reclamo pendiente le llega a esa persona con «Aprobar» y «Rechazar»; solo decide el botón que toca ese número. `POST /aprobar` sigue igual. **No probado con Meta real** (Meta solo entrega el mensaje si la persona escribió en las últimas 24 h) |
| Notas de voz (tentativo) | Apagado por defecto (`VOZ_ACTIVA=1`); transcribe en el mismo equipo con `faster-whisper`, que se instala a mano (`src/taaml/voz.py`). No probado con audios reales de Meta |
| Menú, `/nuevo` y «escribiendo…» | «Hola», «menú» o «ayuda» responden con 3 botones sin llamar al modelo (o como texto si Meta no los entrega); `/nuevo` reinicia la conversación (conserva la memoria de largo plazo; no con un reclamo pendiente); cada mensaje se marca leído con indicador de escribiendo. **No probado con Meta real** |
| Chequeo y preguntas de la demo | `make ensayo-whatsapp` (claves, Ollama, API, token de Meta vivo, túnel; gratis), `make preguntas-hostiles` (12 preguntas incómodas al agente real; gasta cuota) `make herramienta-caida` (rompe herramientas a propósito con DeepSeek real y comprueba que el agente avisa con cortesía, no inventa y no filtra detalles internos; gasta cuota) y `make informe-borrador` (esqueleto del informe final desde el repo) |
| Plan B de la demostración | `make demo-plan-b` (`scripts/37_demo_plan_b.py`): repite en pantalla una conversación real grabada en `docs/demo_grabada.json`, avisando que es una repetición |
| Análisis de conversaciones | `src/taaml/conversaciones.py` y `notebooks/analisis_conversaciones.ipynb`: t-SNE sobre conversaciones simuladas (ver la sección siguiente) |

La app de Streamlit del Taller 1 tiene cuatro pestañas: **Preguntas y respuestas** (con fuentes), **Resumen**, **Preguntas frecuentes** y **Corpus y scraping** (etapas del pipeline y métricas). El agente (Módulos 2 y 3) no está en ella: se entrega con la API y el frontend de arriba (`make api` y `make app`).

## Capturas

| Preguntas y respuestas con fuentes | Corpus y scraping |
|---|---|
| ![Q&A](docs/capturas/qa.png) | ![Corpus](docs/capturas/corpus.png) |

## Instalación

Requisitos: [uv](https://docs.astral.sh/uv/) (regla del curso: solo `uv`, sin `pip` ni `requirements.txt`), Python 3.12 y [Ollama](https://ollama.com/) con el modelo `nomic-embed-text-v2-moe` para los embeddings de las preguntas. Opcional: `llama3.2:3b`, el respaldo local que responde cuando no hay `DEEPSEEK_API_KEY` ni `GOOGLE_API_KEY` o se agota la cuota.

```bash
git clone https://github.com/mariastefuentes/taaml-celsia-asistente.git
cd taaml-celsia-asistente
make setup               # uv sync + .env + modelos de Ollama (nomic y llama3.2:3b)
# o paso a paso:
# uv sync
# cp .env.example .env   # completa DEEPSEEK_API_KEY (agente y tareas); GOOGLE_API_KEY es opcional (respaldo Gemini); sin ellas responde el modelo local
# ollama pull nomic-embed-text-v2-moe
# ollama pull llama3.2:3b
make indice              # construye el índice de vectores con Ollama (el repositorio no versiona el .npz ni Qdrant)
```

**En Windows:** clona en una ruta corta y fuera de OneDrive (por ejemplo `C:\taaml`) y activa las rutas largas con `git config --global core.longpaths true`; si `uv sync` falla por enlaces duros, ejecuta antes `$env:UV_LINK_MODE="copy"`. Sin esto, Windows corta las rutas de más de 260 caracteres y el clon queda incompleto.

## Ver el scraper en vivo

```bash
make scraping-demo      # borra data/_demo_scraping y descarga 5 páginas del blog en data/_demo_scraping/ (respeta robots.txt, pausa de 1 s; no toca data/1_bronze)
```

Para reconstruir la base **desde cero** (descargar todo el sitio): `scripts/01_scrape_celsia.py` y `scripts/02_obtener_sedes.py`, y luego `make datos` y `make indice` (tabla de pasos más abajo).

## Uso

**Agente conversacional (Módulos 2 y 3): API y frontend separados.** El frontend (React con Vite, carpeta `frontend/`) no llama al modelo: habla por HTTP con una API FastAPI (`api/`) que ejecuta el agente y le responde por streaming (Server-Sent Events). Se corren en dos terminales:

```bash
make api        # API del agente con memoria en PostgreSQL (levanta uno local si no defines DATABASE_URL; necesita la clave del modelo en .env y Ollama encendido)
make api-sqlite # la misma API con la memoria en archivos SQLite
```

```bash
make app        # frontend en http://localhost:5173 (alias de make frontend)
```

La API expone `GET /api/salud` (estado, modelo y la base donde busca: `"almacen":"qdrant"`), `POST /api/chat` (un turno, por streaming) y `GET /api/hilos/{hilo}/mensajes` (recupera la conversación) y `GET /api/usuarios/{usuario}/datos` (lo que el agente recuerda de un cliente, para el panel «Lo que recuerdo»), `GET /panel` y `GET /api/actividad` (el panel en vivo de la demostración, con el token del aprobador). Para servicios externos (WhatsApp, N8N) expone `POST /chat`: recibe `{mensaje, telefono}` y devuelve un JSON `{respuesta, herramientas, ok, pendiente}`; si el agente deja algo pausado (radicar un reclamo), una persona lo decide con `POST /aprobar` (`aprobar`, `rechazar` o `responder` con un `mensaje` para el cliente; encabezado `X-Aprobador` igual a `APROBADOR_TOKEN`, sin esa variable queda deshabilitado; si WhatsApp está configurado, el cliente recibe la decisión por mensaje); el teléfono identifica la conversación y la memoria del cliente (se guarda su hash, no el número) y, si el agente falla, responde con un mensaje cortés y `ok: false`. Para WhatsApp (API Cloud de Meta), `GET/POST /webhook/whatsapp` verifica el webhook y recibe los mensajes: comprueba la firma `X-Hub-Signature-256` con `WHATSAPP_APP_SECRET`, responde 200 enseguida, atiende cada mensaje una sola vez en segundo plano y envía la respuesta del agente al cliente (variables `WHATSAPP_*` en `.env.example`; sin ellas el webhook queda deshabilitado). El identificador de la conversación va en la dirección (`/c/<hilo>`), así que recargar la página recupera el hilo desde la base de memoria.

**WhatsApp paso a paso (Módulo 3, vía 2: servidor propio, sin N8N).** (1) En developers.facebook.com crea una app de tipo Empresa con el producto WhatsApp y toma el número de prueba. (2) Copia a `.env` `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` y `WHATSAPP_APP_SECRET`, e inventa `WHATSAPP_VERIFY_TOKEN`. (3) Enciende la API (`make api`) y expónla con un túnel https (por ejemplo `cloudflared tunnel --url http://localhost:8000`). (4) En Meta registra `https://<túnel>/webhook/whatsapp` con ese token de verificación y suscribe el campo `messages`. (5) Agrega tu teléfono como destinatario de prueba y escribe al número. Las pruebas automáticas (`tests/test_whatsapp.py`) cubren la verificación, la firma, los reintentos y el envío con avisos firmados simulados; la prueba con Meta real está pendiente del ensayo general; el guion de la demostración, con el plan B, está en [docs/guion_demo_whatsapp.md](docs/guion_demo_whatsapp.md).

```bash
make setup                                # uv sync + .env + modelo de embeddings (una sola vez por equipo)
make modulo1                              # la app del Módulo 1: solo el corpus y las etapas del scraping
make app-taller1                          # la app del Taller 1 (Streamlit); el agente va por API + frontend
make test                                 # pruebas de componentes, sin Gemini ni Ollama (el CI las corre en cada PR)
make lint                                 # ruff y lock vigente
make ensayo                               # revisa que la demo esté lista, sin gastar cuota
make ensayo-agente                        # conversación real con el agente (GASTA CUOTA: 8 a 12 llamadas)
```

`make` muestra el menú de atajos (`setup`, `modulo1`, `api`, `api-sqlite`, `db-up`, `db-down`, `app`, `app-taller1`, `demo-inyeccion`, `demo-limpiar`, `datos`, `indice`, `scraping-demo`, `recuperacion`, `ensayo`, `ensayo-agente`, `test`, `lint`, `check`, `evaluar`, `pdf`).

**Demo del Módulo 1 (histórica).** `app/modulo1.py` fue la versión que se sustentó en la sesión 8: muestra solo las métricas del corpus y las etapas del scraping (descubrir → extraer → limpiar → deduplicar → enriquecer → curar → fragmentar), sin Q&A, Resumen ni FAQ. La app completa queda en `app/asistente.py` (`make app-taller1`). El scraping en vivo se ejecuta con `make scraping-demo`.

<details>
<summary><b>Referencia detallada: cómo se construye la base, pruebas y opciones</b></summary>

### Cómo se construye la base de conocimiento
Los datos pasan por tres capas (patrón Medallion): cada script hace una sola etapa, en este orden.

| Paso | Comando | Resultado |
|---|---|---|
| 1. Descargar (Bronze) | `uv run python scripts/01_scrape_celsia.py --sections page,blog-celsia,noticias` y `uv run python scripts/02_obtener_sedes.py` | HTML crudo y sedes en `data/1_bronze/` |
| 2. Limpiar (Silver) | `uv run python scripts/03_construir_silver.py` | texto útil, sin duplicados, en `data/2_silver/` |
| 3. Enriquecer (Gold) | `uv run python scripts/04_construir_gold.py` | texto con metadatos en `data/3_gold/` |
| 4. Curar | `uv run python scripts/05_curar_base.py` | `data/4_curaduria/base_conocimiento.txt` y el registro de decisiones |
| 4b. Fragmentar (chunking) | `uv run python scripts/06_construir_chunks.py` | `data/4_curaduria/chunks.jsonl`: 1.690 fragmentos con sus metadatos |
| 4c. Indexar (embeddings) | `uv run python scripts/07_construir_indice.py` (necesita Ollama y `nomic-embed-text-v2-moe`) | `data/4_curaduria/indice_embeddings.npz` (un vector por fragmento, caché) y la base vectorial Qdrant `data/4_curaduria/qdrant` (no se sube a Git; sin ella la app usa el `.npz`) |
| 5. Verificar alcance | `uv run python scripts/08_inventario_intenciones.py` | cobertura de las intenciones del cliente |
| 6. Validar la prueba | `uv run python scripts/09_conjunto_de_prueba.py` | comprueba los criterios del conjunto de prueba (59 preguntas) |
| 7. Evaluar un modelo | `uv run python scripts/11_evaluar_modelo.py --modelo deepseek:deepseek-flash --juez deepseek:deepseek-v4-pro` | respuestas y calificaciones en `docs/2 - Conjunto de prueba/resultados/` |

Archivos binarios: el repositorio no versiona PDF ni la matriz de vectores (`indice_embeddings.npz`). Los PDF se generan con `make pdf` y el índice con `make indice` (necesita Ollama con `nomic-embed-text-v2-moe`); sin índice la búsqueda cae a palabras.

Reglas del scraper: respeta `robots.txt` (los PDF de celsia.com están bloqueados), espera 1 segundo entre peticiones y es reanudable.
**`data/1_bronze/` (HTML crudo, ~250 MB) no se sube a GitHub** (está en `.gitignore`): se regenera con el comando del paso 1. Lo que se entrega como base de conocimiento es Silver, Gold y `data/4_curaduria/`.
Los datos que el sitio muestra solo como enlaces (WhatsApp, PQR, pagos) están escritos a mano, con su fuente, en `data/0_manual/`.

### Pruebas y atajos
`make test` corre las pruebas automáticas de componentes (sin Gemini ni Ollama) y `make` muestra los demás atajos (`datos`, `app`, `evaluar`, `pdf`). `uv run python scripts/12_probar_inyeccion_indirecta.py` prueba órdenes escondidas en los documentos (una llamada al modelo por caso: 7 indirectos y 3 directos; con `--agente`, contra el agente).

### Opciones que se activan a propósito
- **Post-validación.** La app avisa si una cifra, un correo o un enlace de la respuesta no aparece en las fuentes consultadas (`src/taaml/validacion.py`); `scripts/14_validar_respuestas.py` lo mide sobre las respuestas guardadas, sin modelo.
- **Continuidad de la demo.** Si el modelo elegido falla por cuota o conexión, la app prueba `deepseek-flash` (si hay clave) y luego `ollama:llama3.2` (local), y si ninguno responde muestra la respuesta ya evaluada (v3) de esa pregunta, marcada como guardada (`src/taaml/respaldo.py`). `uv run python scripts/16_ensayo_demo.py` revisa que todo esté listo sin gastar; con `--llamar` hace una llamada corta por proveedor.
- **Agente con memoria y router (specs 011 y 013).** `src/taaml/agente.py` arma un agente `create_agent` con `deepseek-flash` (DeepSeek-V4.1-Flash-1017, respaldo `gemini-3.8-flash` y `ollama:llama3.2`), memoria por conversación (`thread_id`) en PostgreSQL (o SQLite en `data/memoria/`, que no se versiona; el hilo viaja en la dirección `/c/<hilo>` y la conversación vuelve al recargar), un recorte del historial que ve el modelo (3.000 tokens aproximados; lo guardado y lo que se ve en pantalla siguen completos) y cinco herramientas: `buscar_en_base`, `consultar_datos`, `guardar_dato_del_cliente`, `recordar_datos_del_cliente` y `radicar_reclamo` (con aprobación humana). El prompt vigente es `prompts/v7_agente.md`. Se usa por la API y el frontend (no por Streamlit); `uv run python scripts/18_ensayo_agente.py` hace una conversación de cuatro preguntas (gasta unas 8 a 12 llamadas al modelo de pago) y `scripts/15_probar_agente.py` hace preguntas sueltas.
- **Extracción a JSONL.** `uv run python scripts/13_extraer_contactos.py` (3 llamadas al modelo por defecto, DeepSeek) escribe `data/5_extraccion/contactos.jsonl`.
- **Trazabilidad (LangSmith).** Si el `.env` tiene `LANGSMITH_API_KEY`, la app y las tareas registran cada ejecución (pregunta, fragmentos, prompt, respuesta, tokens y tiempo) en el proyecto `taaml-celsia` de smith.langchain.com. Sin la clave no se envía nada. La evaluación (`11_evaluar_modelo.py`) llama a la API directamente y no se traza. En el agente, cada paso (modelo y herramientas) es un nodo de la traza con su latencia, y un error en los argumentos de una herramienta aparece como error de ese nodo. `scripts/24_evaluar_en_langsmith.py` sube la matriz de enrutamiento como dataset (`celsia-matriz-enrutamiento`) y la evalúa con `evaluate`, con dos configuraciones del agente (con y sin tope de herramientas) que se comparan en LangSmith. LangSmith observa; no orquesta.
- **Reordenamiento de fragmentos.** `responder_con_fuentes(..., reordenar=True)` o `--reordenar` en los scripts 10 y 11: recupera 30 candidatos y un modelo barato elige los 12 mejores (`deepseek-flash`; `gemini-3.5-flash-lite` si el que responde es de Gemini). Cuesta una llamada más por pregunta y está apagado por defecto.
- **DeepSeek (modelo por defecto).** Con `DEEPSEEK_API_KEY` en el `.env`, `deepseek-flash` (DeepSeek-V4.1-Flash-1017) es el modelo por defecto del agente y de las tareas; también se puede escribir `deepseek-flash` (o `deepseek-v4-pro`) en el campo «Modelo» de la app, o pasar `modelo="deepseek-flash"` a las tareas, con el razonamiento apagado; el reordenador también cambia a `deepseek-flash`. En la evaluación: `--modelo deepseek:deepseek-flash --juez deepseek:deepseek-v4-pro`. DeepSeek respeta `temperature 0.0`, pero deja `top_p` fijo en 1,0.

</details>

## Análisis de conversaciones con t-SNE (Ruta Transversal A)

La API ya guarda cada conversación completa en PostgreSQL (el checkpointer, bajo un hash del teléfono). `taaml.conversaciones` las lee, marca cuáles terminaron mal y arma el texto de cada una; el cuaderno `notebooks/analisis_conversaciones.ipynb` las convierte en vectores, las proyecta con t-SNE (2D y 3D), las agrupa y analiza dónde falla el asistente. **Los datos del cuaderno son simulados** (114 conversaciones escritas por el equipo y pasadas por el agente real), no clientes de Celsia.

```
uv sync --group analisis
uv run python scripts/35_simular_conversaciones.py   # simula con el agente real (gasta cuota) y exporta a data/analisis/
uv run python scripts/36_construir_notebook_tsne.py  # construye y ejecuta el cuaderno (necesita Ollama la primera vez)
```

## Estructura
Equivalencias de datos: `data/1_bronze/` es el crudo (raw), `data/2_silver/` el procesado (processed) y `data/3_gold/` el corpus con metadatos (gold). Cada documento de Gold lleva `url`, `title`, `categoria` (la sección del sitio), `fecha_extraccion` (captura), `fecha_publicacion`, `section` (el sitemap de origen) y `hash`; Silver conserva `url`, `title`, `section`, `fecha_publicacion` y `hash`.

```
docs/        análisis de la empresa, conjunto de prueba, informes, capturas, diagramas de Archify (el `.json` es la fuente; los `*.delivery.json` los genera Archify para la entrega), decisiones.md (D1 a D19), guion_demo_whatsapp.md, politica_de_privacidad.md (la URL que pide Meta para publicar la app), vacios_de_la_base.md, la declaración de uso de IA del Módulo 3 y skillspector-corpus-medallion.md (reporte de seguridad de la skill)
scripts/     01 a 41: etapas del pipeline y pruebas en el orden en que se usan (34 PostgreSQL local, 35 y 36 análisis de conversaciones, 37 plan B de la demostración, 38 exporta los chats reales, 39 chequeo previo de WhatsApp, 40 preguntas hostiles, 41 borrador del informe); utilidades/: herramientas sueltas
data/        0_manual/ 1_bronze/ 2_silver/ 3_gold/ 4_curaduria/ 5_extraccion/
src/taaml/   código del asistente (base.py, recuperacion.py, vectorstore.py, sinonimos.py, reordenar.py, validacion.py, respaldo.py, agente.py, consulta_datos.py, prompts.py, tareas.py, whatsapp.py, limite.py, conversaciones.py, actividad.py, voz.py)
prompts/     prompts versionados (asistente v3 vigente, v4 y v5 descartados; resumen y FAQ v2; agente v7 vigente, v2 a v6 reemplazados; extracción v1)
tests/       pruebas automáticas de componentes (make test)
specs/       especificaciones (qué, cómo y tareas) de cada cambio; 001 a 013: asistente, validación y agente, continuidad de la demo, base vectorial con Chroma (después reemplazada por Qdrant, spec 012), evidencia de Resumen y FAQ, tabla y pruebas del pipeline, pestaña Corpus, prueba del scraper, etapa Descubrir, organización de la entrega, agente con memoria y router, Qdrant, y el agente en producción con WhatsApp; las decisiones de arquitectura están en `docs/decisiones.md`
.specify/    memoria del proyecto: memory/constitution.md (verdad central)
.github/     plantilla de Pull Request y CI
api/        Módulos 2 y 3: API FastAPI del agente (streaming SSE, POST /chat, webhook de WhatsApp, aprobación humana, memoria del cliente)
notebooks/  Módulo 3: análisis de conversaciones con t-SNE (conversaciones simuladas)
frontend/   Módulo 2: interfaz React + Vite, separada de la API
app/        Taller 1 (material histórico, el agente vigente no lo usa): aplicaciones Streamlit, asistente.py (Q&A, Resumen, FAQ y Corpus) y modulo1.py (solo corpus y scraping)
```

## Skills

Las skills del proyecto (`corpus-medallion` y `agente-rag-router`) viven en su propio repositorio público: [mariastefuentes/taaml-skills](https://github.com/mariastefuentes/taaml-skills). Se instalan con `npx skills add mariastefuentes/taaml-skills --skill corpus-medallion`. La revisión de seguridad de `corpus-medallion` está en [docs/skillspector-corpus-medallion.md](docs/skillspector-corpus-medallion.md).

## Licencia

Licencia MIT ([LICENSE](LICENSE)), © 2026 María Stella Fuentes, Juan José Mosquera, Nicolás Bolaños y Jensen Fabián Tamayo. El contenido de celsia.com pertenece a Celsia y se usa aquí con fines académicos, respetando su `robots.txt`.

## Créditos

**Grupo 4, Celsia.** Maestría en IA y Ciencias de Datos, Universidad Autónoma de Occidente, curso *Técnicas avanzadas de IA aplicadas en modelos de lenguaje*, 2026-2S.

| Integrante | GitHub |
|---|---|
| María Stella Fuentes | [@mariastefuentes](https://github.com/mariastefuentes) |
| Juan José Mosquera | [@juanmosqueraesquivel-hub](https://github.com/juanmosqueraesquivel-hub) |
| Jensen Fabián Tamayo | [@Jensentamayo](https://github.com/Jensentamayo) |
| Nicolás Bolaños | [@nico10102003](https://github.com/nico10102003) |

Para contribuir, lee la [guía de contribución](CONTRIBUTING.md), el [código de conducta](CODE_OF_CONDUCT.md) y la [constitución](CONSTITUTION.md) del proyecto.

Herramientas: LangChain, Streamlit, FastAPI, React, Qdrant, PostgreSQL, Ollama, Gemini, DeepSeek, LangSmith y la API Cloud de WhatsApp. El código se escribió con ayuda de Claude Code; la declaración de uso de IA del Módulo 3 está en [docs/3 - Informe/declaracion_uso_ia_modulo3.md](<docs/3 - Informe/declaracion_uso_ia_modulo3.md>) y la de los talleres anteriores, en sus informes.
