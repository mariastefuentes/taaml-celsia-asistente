# Preparación de la sustentación del Taller 2 (sábado 14 de noviembre, 10:00 a 10:15)

Sirve para tres cosas: comprobar que nada de lo que «no se acepta» ocurre, repartir quién explica qué (ítem 5.2) y llegar a las 10:00 con todo encendido y probado (ítem 5.1). El guion de los casos está en `docs/guion_demo_taller2.md`.

## 1. Lo que «no se acepta» y cómo se cumple

| No se acepta | Estado | Cómo y dónde |
|---|---|---|
| Solo diapositivas, un video o un recorrido por el código sin el agente funcionando | Cumple | La demo es en vivo desde el frontend propio; las capturas de `docs/capturas` son solo respaldo si cae la red |
| Streamlit, Gradio, notebook o dashboard de prototipo como interfaz | Cumple | La interfaz del agente es React 19 + Vite (`frontend/`). Streamlit solo queda en `app/` como la aplicación del Taller 1, y un test (`tests/test_agente.py`) vigila que el agente no esté ahí |
| Frontend que llame al modelo directamente | Cumple | El frontend solo habla con `/api/*` (`frontend/src/api.js`); el modelo lo llama el backend (`api/main.py`) |
| «RAG» sin citar fuente o con documentos inventados | Cumple | «Fragmentos consultados» con documento, fragmento y enlace; `datos_dudosos` marca cifras, correos y enlaces que no estén en lo recuperado; sin evidencia responde «No tengo esa información» |
| Memoria en la RAM presentada como persistencia | Cumple | SQLite en disco (o PostgreSQL con `DATABASE_URL`). Se demuestra con F5 o reiniciando la API |
| Router que busca siempre en la base, incluso ante un saludo | Cumple | La matriz de enrutamiento tiene «Hola» (R23) y «Gracias, eso era todo» (R24) con herramienta esperada «ninguna» |
| Menos de 40 PRs fusionados o todo en `main` sin revisión | Parcial | 42 PRs fusionados. Solo 4 commits de los 43 de la línea principal fueron directos a `main`, todos del 29 de octubre al 5 de noviembre. Revisión formal: solo una parte de los PRs la tiene (ver «Radar de pendientes») |
| API keys o `.env` en el repositorio | Cumple | `.env` está ignorado y no se rastrea; una búsqueda de patrones de claves (Google, OpenAI, LangSmith, GitHub) en los archivos y en el historial no encontró ninguna. `.env.example` solo trae nombres |
| Demo que solo funciona en un computador | Parcial | Se instala con `uv sync`, `npm install`, `make indice` y `make api`. El índice de Qdrant no se versiona: hay que construirlo con Ollama (`make indice`), y eso solo se probó en este computador. Antes del sábado conviene clonar en una carpeta limpia y seguir el README una vez |

## 2. Quién explica qué (ítem 5.2)

El historial muestra que el agente del Taller 2 lo escribió casi todo María Stella (154 de 177 commits). Los otros tres integrantes tienen trabajo real y verificable, pero del Taller 1 y de la infraestructura. El docente puede pedir a cualquiera «explica tu parte», así que cada uno debe poder hablar de lo suyo con los archivos abiertos, y conectarlo con el agente. Los commits y PRs de cada uno son la prueba de que es su parte.

### María Stella Fuentes: el agente
Archivos: `src/taaml/agente.py`, `src/taaml/consulta_datos.py`, `prompts/v3_agente.md`, `api/main.py`.
- **Router.** El modelo elige `consultar_datos`, `buscar_en_base` o responder directo, según las descripciones de las herramientas (`agente.py:71` y `:89`). Se mide en la matriz de 28 preguntas.
- **Memoria.** Corto plazo: checkpointer con `thread_id` (`agente.py:176`). Largo plazo: Store con namespace `("perfil", usuario)` (`agente.py:110`).
- **Datos exactos.** `ConsultaDatos` (Pydantic): el total lo calcula el código, no el modelo.
- **Blindaje.** `delimitar_como_datos` y `datos_dudosos`.

Preguntas probables: ¿por qué el modelo y no un clasificador?, ¿qué pasa si dos usuarios usan el mismo hilo?, ¿cómo evitan que un documento mande una orden?

### Juan José Mosquera: respaldo del modelo y base del repositorio
Commits: respaldo local con Ollama cuando falla Gemini (clave inválida, sin clave); menú de atajos y preparación del entorno en el `Makefile`; constitución, plantilla de PR y reglas del repositorio; `make scraping-demo`.
Archivos: `src/taaml/respaldo.py` (`es_falla_del_proveedor`, línea 29), `Makefile`, `.github/PULL_REQUEST_TEMPLATE.md`, `.specify/memory/constitution.md`, `tests/test_respaldo.py`.
- **Qué explicar.** Qué cuenta como falla del proveedor (cuota, conexión, 401/403) y qué no (un error del código); cómo se encadenan Gemini, DeepSeek y Ollama; y cómo el agente usa ese respaldo (`ModelFallbackMiddleware`, `agente.py:239`).
- **Puente al agente.** «Si Gemini se cae en la demo, el agente sigue con `llama3.2`; es más lento y acierta menos (2 de 4 casos con herramientas)».
- **Cómo se levanta todo.** `make setup`, `make api`, `make frontend`: es la parte que más ayuda en el arranque de las 8:00.

Preguntas probables: ¿qué pasa si la clave es inválida?, ¿por qué un error de código no activa el respaldo?, ¿cómo reproduce otra persona el proyecto?

### Nicolás Bolaños: métricas de recuperación
Commit: métricas del RAG y mensajes de error más claros (PR 12: `recuperacion.py`, `reordenar.py`, `tareas.py` y sus pruebas).
Archivos: `src/taaml/recuperacion.py` (`buscar`, línea 237; `_buscar`, línea 208), `src/taaml/reordenar.py`, `scripts/21_metricas_ranking.py` (`ndcg`, línea 31), `tests/test_recuperacion.py`.
- **Qué explicar.** Cómo se busca (por significado, por palabras o híbrido), qué mide hit, precision, recall y nDCG@10, y qué resultados salieron (informe 5.4 y la evaluación de 35 preguntas con respuesta y 24 sin respuesta).
- **Puente al agente.** `buscar_en_base` llama a `recuperacion.buscar`: lo que él explica es lo que hay debajo de la herramienta de RAG.

Preguntas probables: ¿qué es nDCG@10?, ¿por qué el modo «auto» con embeddings superó al híbrido?, ¿cómo se sabe si una pregunta no tiene respuesta en el corpus?

### Jensen Fabián Tamayo: interfaz
Commits: envío con Ctrl+Enter y ayuda de contexto en la app del Taller 1 (`app.py`, hoy `app/asistente.py`).
El frontend del Taller 2 lo escribió María Stella, así que Jensen necesita leerlo antes de explicarlo:
Archivos: `frontend/src/api.js` (lectura del stream SSE, línea 50 en adelante), `frontend/src/App.jsx` (`alEvento`, línea 77; `preguntar`, línea 97; manejo de errores con `catch`), `frontend/src/App.css` (`@media (max-width: 480px)`).
- **Qué explicar.** Cómo el navegador recibe la respuesta por partes (eventos `hilo`, `herramienta`, `fuentes`, `texto`, `aviso`, `fin`, `error`), qué muestra cuando no hay conexión (botón de reintento) y cómo se ve en celular.
- **Puente al agente.** La etiqueta de herramienta y «Fragmentos consultados» son lo que el docente ve del router y de la cita de fuente.

Preguntas probables: ¿por qué el frontend no llama al modelo?, ¿cómo recupera la conversación al recargar?, ¿qué pasa si la API se cae a mitad de una respuesta?

**Para todos.** No hace falta saber todo: cada uno debe poder (1) decir qué hace su parte en una frase, (2) abrir su archivo y señalar la función clave, (3) contestar «¿qué pasa si falla?» y (4) decir cómo se conecta con el agente. Si no sabe algo, lo honesto es decir «eso lo hizo X, pero lo que yo sé es…». Mejor que escudarse es conocer su parte a fondo.

## 3. Guion de 15 minutos (el cronómetro de la rúbrica)

| Minuto | Qué | Quién habla |
|---|---|---|
| 0:00 a 0:45 | Apertura: qué es el agente y qué se verá; la app ya está abierta | María Stella |
| 0:45 a 3:30 | Casos 1 y 2: «¿Qué sedes hay en Ibagué?» y «¿y su teléfono?» | María Stella (router, memoria) |
| 3:30 a 5:00 | Caso 3: política de calidad, abrir «Fragmentos consultados» | Nicolás (cómo se recupera y por qué esa fuente) |
| 5:00 a 6:30 | Caso 4: reporte de daño en Ibagué, con las dos herramientas | María Stella |
| 6:30 a 7:30 | Memoria de largo plazo: «Me llamo Ana…», nueva conversación, «¿Dónde trabajo?» | María Stella |
| 7:30 a 9:00 | Blindaje: `make demo-inyeccion` y la pregunta de política de calidad | María Stella |
| 9:00 a 10:00 | Interfaz: F5 recupera la conversación; qué ve el usuario si la API falla | Jensen |
| 10:00 a 11:00 | Respaldo: qué pasa si Gemini cae y cómo se levanta el proyecto desde cero | Juan José |
| 11:00 a 15:00 | Preguntas del docente | quien tenga la parte |

Si el tiempo aprieta se sacrifica en este orden: la interfaz, el respaldo y el blindaje. Los casos 1 a 4 y la memoria de largo plazo no se recortan.

## 4. Lista de las 8:00 a.m.

Todo abierto antes de las 8:00, como pidió el docente.
1. Ollama encendido (`ollama list` debe mostrar `nomic-embed-text-v2-moe` y `llama3.2:3b`).
2. `.env` con `GOOGLE_API_KEY` con facturación y, si se usa, `LANGSMITH_API_KEY`.
3. Terminal 1: `make api` (puerto 8000). Comprobar `http://localhost:8000/api/salud` → `{"estado":"ok"}`.
4. Terminal 2: `make frontend` (puerto 5173). Abrir `http://localhost:5173`.
5. Pregunta de calentamiento fuera del guion («hola»): la primera carga los modelos.
6. «Nueva conversación» y, en «Lo que recuerdo», borrar lo de ensayos anteriores.
7. IDE con el repositorio abierto en `agente.py`, `consulta_datos.py`, `respaldo.py`, `recuperacion.py` y `App.jsx`.
8. Pestañas de GitHub (PRs fusionados) y de LangSmith (proyecto `taaml-celsia`) ya abiertas y con la sesión iniciada.
9. Ningún PR abierto (el docente lo pidió): fusionarlos o cerrarlos la noche anterior.
10. Ensayar los cuatro casos una vez completos y cronometrar; si algún caso falla, usar la tabla «Si algo falla» del guion.
11. Respaldo: una captura por caso en `docs/capturas`, solo para mostrar si cae la red, nunca como sustituto de la demo.
12. Cargador, red estable y datos del celular listos como segunda red.

## 5. Una prueba que conviene hacer una vez

Clonar el repositorio en una carpeta limpia (`C:\taaml-prueba`, fuera de OneDrive) y seguir el README: `uv sync`, `make indice`, `make api`, `make frontend`. Es la única forma de saber que «se puede reproducir» sin depender de la copia de trabajo actual. Tarda unos minutos y no gasta llamadas a Gemini; `make indice` usa solo Ollama.
