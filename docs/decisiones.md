# Registro de decisiones de arquitectura (Taller 2 y Módulo 3)

Cada decisión dice qué se decidió, por qué, qué se descartó y dónde está la evidencia. Es el registro versionado de las decisiones del agente: vive en el repositorio y cambia con él. Se redactó el 13 de noviembre de 2026 a partir del informe (`docs/3 - Informe/informe_taller2.md`) y de las especificaciones (`specs/011` y `specs/012`). No está en Engram: Engram es una herramienta externa de memoria para agentes de código y no se usó en este proyecto.

| # | Decisión | Estado |
|---|---|---|
| D1 | Agente `create_agent`, sin `StateGraph` propio | vigente |
| D2 | El router es el modelo con herramientas bien descritas, no un clasificador aparte | vigente |
| D3 | Los números los calcula el código, no el modelo | vigente |
| D4 | Memoria: PostgreSQL en la API (`make api`) y SQLite como alternativa (`make api-sqlite`) | vigente |
| D5 | Qdrant local con alias, búsqueda exacta | vigente |
| D6 | Contexto recuperado como datos pasivos, con delimitador y validación | vigente |
| D7 | Interfaz: API FastAPI con SSE y frontend React desacoplado | vigente |
| D8 | DeepSeek de pago como modelo principal y Ollama como respaldo | vigente |
| D9 | Sin gatekeeper externo (System One) mientras no haya clave | abierta |
| D10 | WhatsApp con servidor propio en FastAPI, sin N8N (Módulo 3, vía 2) | vigente |
| D11 | Aprobación humana con `HumanInTheLoopMiddleware` en `radicar_reclamo` | vigente |
| D12 | RAG agéntico por defecto y RAG en cadena como modo opcional | vigente |
| D13 | Límite de mensajes por teléfono en memoria | vigente |
| D14 | Prompt del agente versionado: v7 vigente | vigente |
| D15 | Análisis de conversaciones sobre el checkpointer, con t-SNE y KNN | vigente |
| D16 | Aprobación humana con tres salidas: aprobar, rechazar o responder | vigente |
| D17 | Mejoras de la Clase 9 que no se adoptaron (Jev, formato OKF) | vigente |

## D1. Agente `create_agent`, sin `StateGraph` propio
- **Contexto.** El flujo es un solo ciclo de decisión: modelo, herramienta, modelo.
- **Decisión.** Usar `create_agent` de LangChain 1.x, que corre sobre LangGraph y trae el checkpointer, el Store y el middleware (recorte de historial, resumen, tope de llamadas, respaldo de modelo).
- **Descartado.** Un grafo a mano (más control con más código que mantener), Deep Agents, Agno, LlamaIndex y DSPy (tabla de la sección 2.2 del informe).
- **Excepción.** Para el Taller 2 se escribió un `StateGraph` a mano con una pausa (`src/taaml/flujo_reclamo.py`). En el Módulo 3 la aprobación humana pasó al agente mismo con `HumanInTheLoopMiddleware` (D11); el grafo a mano queda como material del Taller 2.
- **Cuándo se revisa.** Si el agente necesita ramas explícitas que el middleware no pueda expresar.
- **Evidencia.** `src/taaml/agente.py`; informe, secciones 2 y 2.2.

## D2. El router es el modelo con herramientas bien descritas
- **Contexto.** Cada pregunta debe ir a datos exactos, a texto del corpus, a ambos o a ninguno.
- **Decisión.** Que el modelo elija entre `consultar_datos`, `buscar_en_base` y la respuesta directa mediante function calling: recibe las herramientas con su esquema Pydantic y responde con una llamada estructurada (nombre y argumentos validados), guiado por sus descripciones y por el prompt vigente. No se interpreta texto libre. La validación estricta la hace Pydantic de nuestro lado; no se usa el modo `strict` del proveedor. La búsqueda en el texto del sitio admite dos modos (`RAG_MODO`): el agente decide cuándo llamar a `buscar_en_base` (por defecto) o un `dynamic_prompt` inserta los fragmentos recuperados en cada llamada (RAG en cadena).
- **Descartado.** Un clasificador previo (más llamadas y un punto de fallo extra).
- **Consecuencia.** El enrutamiento se mide, no se asume: matriz de 33 preguntas con la herramienta esperada, y las preguntas de conteo y de varias ciudades ya cuentan con su caso.
- **Evidencia.** `docs/2 - Conjunto de prueba/matriz_enrutamiento.csv`, `scripts/22_matriz_enrutamiento.py`, informe 4.2 y 5.1.

## D3. Los números los calcula el código
- **Contexto.** Un modelo que suma o cuenta puede equivocarse, y una cifra mal dicha sobre sedes o tarifas es un error de cara al cliente.
- **Decisión.** `consultar_datos` devuelve el total ya calculado, incluida la suma de varias ciudades. Además, `datos_dudosos` revisa que cada cifra, correo y enlace de la respuesta aparezca en lo que devolvieron las herramientas.
- **Evidencia.** `src/taaml/consulta_datos.py`, `tests/test_consulta_datos.py`.

## D4. Memoria en PostgreSQL en la API y SQLite como alternativa
- **Decisión.** `make api` arranca la API con `PostgresSaver` y `PostgresStore` (levanta un PostgreSQL local sin Docker si no hay `DATABASE_URL`); `make api-sqlite` usa `SqliteSaver` y `SqliteStore`, sin servidor. En el código, sin `DATABASE_URL` se usa SQLite (así los scripts y las pruebas no necesitan servidor). La memoria de largo plazo guarda lo que el cliente cuenta de sí mismo bajo el namespace `("perfil", usuario)`, con tope de 20 datos y borrado por el cliente.
- **Consecuencia.** El mismo código corre en ambos; las pruebas de PostgreSQL usan un servidor real.
- **Evidencia.** `src/taaml/agente.py`, `tests/test_memoria_postgres.py`, informe sección 3.

## D5. Qdrant local con alias, búsqueda exacta
- **Decisión.** Qdrant en modo local (coseno) con el alias `blue`/`green` para cambiar de colección sin parar el servicio. Con 1.690 vectores la búsqueda exacta basta.
- **Medido.** HNSW en un servidor Qdrant 1.20.1 dio recall@10 de 1,000 y no ganó tiempo a este tamaño, así que no se adopta.
- **Evidencia.** `specs/012-base-vectorial-qdrant`, `scripts/29_medir_hnsw_en_servidor.py`, informe 5.6.

## D6. Contexto recuperado como datos pasivos
- **Decisión.** Lo que devuelve una herramienta llega encerrado en `<documentos_recuperados>` con un aviso de que son datos y no instrucciones; un fragmento no puede cerrar ese bloque. Se filtran los caracteres invisibles.
- **Evidencia.** `delimitar_como_datos` en `src/taaml/agente.py`; batería de 11 ataques directos y 8 indirectos resistidos; demo `make demo-inyeccion`; informe 5.3.

## D7. API FastAPI con SSE y frontend React desacoplado
- **Decisión.** El backend (`api/main.py`) transmite eventos SSE y el frontend (`frontend/`) los pinta; el identificador de conversación va en la ruta `/c/<hilo>`. Streamlit queda solo como la aplicación del Taller 1.
- **Evidencia.** `api/main.py`, `frontend/src/App.jsx`, `tests/test_api.py`, informe 6.

## D8. Modelo de pago principal y respaldo local
- **Decisión.** `deepseek-flash` (DeepSeek-V4.1-Flash-1017, API de pago) en el agente y en Q&A, Resumen, FAQ y el flujo de reclamo, con `llama3.2` en Ollama como respaldo. Ollama también calcula los embeddings.
- **Respaldo en cadena (PR 73).** Si DeepSeek falla (cuota, red o más de 60 s sin respuesta), el agente prueba `gemini-3.8-flash` y después `llama3.2` local. `TAAML_MODELO_AGENTE` en `.env` cambia el modelo principal sin tocar código; `/api/salud` informa el principal, no el que respondió.
- **Límite declarado.** DeepSeek respeta `temperature` con el razonamiento apagado, pero deja `top_p` fijo en 1,0; el respaldo Gemini 3.8 ignora ambos. Se compensa con las herramientas, la validación y el «No tengo esa información».
- **Evidencia.** `src/taaml/agente.py`, `tests/test_agente.py`, informe 7.

## D9. Gatekeeper System One (Jev): abierta
- **Contexto.** El enunciado lo pide solo «si está disponible». Es una API comercial y requiere una clave.
- **Decisión pendiente.** Si hay clave, se añade como compuerta opcional (`Noul` para decidir si hace falta RAG, `Choice` para saludo, consulta o fuera de dominio) y se mide contra la matriz. Si no la hay, se documenta como no usado.

## D10. WhatsApp con servidor propio en FastAPI, sin N8N (Módulo 3, vía 2)
- **Contexto.** El Módulo 3 pide conectar el agente a WhatsApp por una de dos vías: N8N (visual) o un servidor de integración propio. Hay que justificar la elección.
- **Alternativas consideradas.** (a) Vía 1, N8N: un flujo visual que recibe el webhook, llama a `POST /chat` y envía la respuesta; (b) Twilio como proveedor en lugar de la API Cloud de Meta; (c) el manejador del webhook dentro de la API FastAPI.
- **Decisión.** (c) con la API Cloud de Meta: `GET/POST /webhook/whatsapp` verifica el webhook, comprueba la firma `X-Hub-Signature-256`, responde 200 enseguida, atiende el mensaje en segundo plano, descarta avisos repetidos por id y envía la respuesta por la Graph API.
- **Por qué.** Un solo servicio que mantener en lugar de dos; la firma, los reintentos, el límite por teléfono y la aprobación se prueban con pruebas automáticas (`tests/test_whatsapp.py`, 15), cosa que un flujo visual no permite igual; el estado vive en nuestra base y no en un sistema externo; la lógica queda versionada en el repositorio y revisada por PR.
- **Qué se pierde.** N8N habría sido más rápido de armar, se modifica sin código y trae el editor visual; hubiéramos escrito menos. Además el servidor propio hay que exponerlo con un túnel https (hoy cambia de dirección en cada arranque).
- **Límite declarado.** El webhook se probó con avisos firmados simulados, no con Meta real: falta confirmar el formato real, la caducidad del token temporal y a cuántos destinatarios puede escribir el número de prueba.
- **Evidencia.** `api/main.py`, `src/taaml/whatsapp.py`, `tests/test_whatsapp.py`, `specs/013-agente-en-produccion-whatsapp`.

## D11. Aprobación humana con `HumanInTheLoopMiddleware` en `radicar_reclamo`
- **Contexto.** Radicar un reclamo cambia algo fuera de la conversación y no debe hacerlo el modelo solo.
- **Alternativas consideradas.** (a) Sin aprobación; (b) aprobar toda herramienta; (c) el `StateGraph` a mano con `interrupt` del Taller 2, separado del agente; (d) `HumanInTheLoopMiddleware` solo en la herramienta que escribe.
- **Decisión.** (d): `radicar_reclamo` pausa con `approve`, `edit` o `reject`; las demás herramientas son de lectura o de memoria del cliente y corren solas. La pausa viaja por el checkpointer (PostgreSQL), así que sobrevive a un reinicio. Una persona decide con `POST /aprobar` (encabezado `X-Aprobador`, deshabilitado sin `APROBADOR_TOKEN`) y el cliente recibe la decisión por WhatsApp.
- **Detalle importante.** El middleware pausa antes de validar los argumentos; por eso `validar_reclamo_antes_de_pausar` (un `after_model` propio, colocado después en la lista) rechaza un reclamo inválido antes de que llegue a la persona, con un máximo de 2 reintentos.
- **Límite declarado.** El registro del reclamo es simulado (`radicar_simulado`): un sistema real llamaría al de Celsia.
- **Evidencia.** `src/taaml/agente.py`, `tests/test_agente.py`, `tests/test_memoria_postgres.py`.

## D12. RAG agéntico por defecto y RAG en cadena como modo opcional
- **Contexto.** El Módulo 3 exige `dynamic_prompt` para alimentar un RAG en cadena; el agente ya buscaba mediante la herramienta `buscar_en_base`.
- **Alternativas consideradas.** (a) Solo RAG agéntico (el modelo decide cuándo buscar); (b) solo RAG en cadena (se busca en cada turno); (c) ambos, elegibles con `RAG_MODO`.
- **Decisión.** (c). Por defecto, agéntico: un saludo no gasta una búsqueda y las preguntas mixtas combinan herramientas. Con `RAG_MODO=cadena`, un `dynamic_prompt` (`con_contexto_recuperado`) inyecta los fragmentos y se quita la herramienta.
- **Evidencia.** `src/taaml/agente.py`, pruebas de RAG en cadena en `tests/test_agente.py`.

## D13. Límite de mensajes por teléfono en memoria
- **Contexto.** El bot será público durante la demo: sin tope, alguien que escriba muchas veces gasta la cuota del modelo.
- **Alternativas consideradas.** (a) Ninguno; (b) por dirección IP; (c) por teléfono en memoria del proceso; (d) por teléfono en Redis.
- **Decisión.** (c): 8 mensajes por minuto por teléfono (`LIMITE_MENSAJES`, `LIMITE_VENTANA_S`). `/chat` responde 429 con `Retry-After`; por WhatsApp se avisa una sola vez por ventana y no se llama al modelo. No guarda el número: usa un hash.
- **Por qué no las otras.** La IP no sirve: todos los avisos de WhatsApp llegan de Meta. Redis añade un servicio para un solo proceso.
- **Límite declarado.** Con varios procesos cada uno cuenta aparte. `POST /api/chat` (el frontend, sin teléfono) no tiene límite.
- **Evidencia.** `src/taaml/limite.py`, `tests/test_limite.py`.

## D14. Prompt del agente versionado: v7 vigente
- **Contexto.** Con el prompt v5 el agente contestaba trivias con su propio conocimiento; con v6 rechazaba preguntas de energía que sí son de Celsia, y con una herramienta caída a veces decía «ya guardé».
- **Alternativas consideradas.** (a) Dejar v6; (b) un clasificador o gatekeeper previo (D9); (c) corregir el prompt.
- **Decisión.** (c), como versión nueva (`prompts/v7_agente.md`; v6 queda marcado como reemplazado): los temas de energía se buscan aunque no nombren a Celsia y, si una herramienta falla, no se dice que algo quedó guardado ni radicado; el aviso de error de la herramienta lo repite.
- **Medido con el agente real.** 7 de 8 preguntas de energía respondidas con búsqueda (la octava dijo con honestidad que no hay información), 10 de 10 preguntas ajenas rechazadas, 6 de 6 respuestas honestas con el Store caído y matriz de enrutamiento 32 de 33 (R31 ya fallaba con v5 y v6).
- **Evidencia.** `prompts/v7_agente.md`, `tests/test_prompts.py`, fila de v7 en `.specify/memory/constitution.md`.

## D15. Análisis de conversaciones sobre el checkpointer, con t-SNE y KNN
- **Contexto.** La ruta transversal A pide guardar cada conversación completa, convertirla en vector y proyectarla con t-SNE para ver clústeres.
- **Alternativas consideradas.** (a) Una tabla de registro aparte escrita por la API; (b) leer lo que ya guarda el checkpointer (`PostgresSaver`); (c) proyectar con t-SNE solo, sin comparar con otro método.
- **Decisión.** (b): una tabla aparte duplicaría datos y obligaría a decidir qué hacer con el teléfono; el checkpointer ya guarda cada conversación completa bajo un hash del teléfono. `taaml.conversaciones` las lee y marca las fallidas; el cuaderno usa los embeddings del propio agente, t-SNE en 2D y 3D, K-means y una comparación con KNN en el espacio original (t-SNE sirve para mirar, KNN para buscar vecinos).
- **Límites declarados.** Los datos son 114 conversaciones simuladas, no clientes reales; la marca de «fallida» es una regla de palabras que mezcla rechazos correctos con fallos reales (de 20 marcadas, 5 lo eran).
- **Evidencia.** `src/taaml/conversaciones.py`, `scripts/35_simular_conversaciones.py`, `scripts/36_construir_notebook_tsne.py`, `notebooks/analisis_conversaciones.ipynb`.

## D16. Aprobación humana con tres salidas: aprobar, rechazar o responder
- **Contexto.** La Clase 9 muestra cuatro decisiones del revisor en `HumanInTheLoopMiddleware`: `approve`, `edit`, `reject` y `respond`. Con solo aprobar o rechazar, una persona que ve un reclamo incompleto no tiene cómo pedirle más datos al cliente.
- **Alternativas consideradas.** (a) Dejar aprobar y rechazar; (b) agregar `edit` en la API; (c) agregar `respond`.
- **Decisión.** (c): `POST /aprobar` acepta `decision: "responder"` con un `mensaje` (obligatorio, hasta 500 caracteres). La herramienta no corre, no se radica nada y el agente recibe lo que dijo la persona para transmitírselo al cliente por WhatsApp. `edit` ya está permitido en el middleware, pero la API no lo expone todavía.
- **Por qué.** Es el único caso en que el humano aporta información en vez de solo un sí o un no, y no cuesta infraestructura nueva: viaja por el mismo checkpointer.
- **Qué no se hizo.** El predicado `when` que muestra la clase (pausar solo algunas llamadas de una herramienta) no existe en la versión instalada de LangChain; `radicar_reclamo` siempre pausa.
- **Evidencia.** `src/taaml/agente.py` (`resolver_aprobacion`), `api/main.py` (`Decision`), pruebas en `tests/test_agente.py` y `tests/test_api.py`.

## D17. Mejoras de la Clase 9 que no se adoptaron
- **Jev (System One) como compuerta del RAG.** Sigue abierta (D9): es una API comercial y no hay clave. El agente ya decide cuándo buscar (D12) y la matriz de enrutamiento mide ese acierto (32 de 33), así que la compuerta sería una optimización de costo y latencia, no una pieza que falte.
- **Campos `verified` y `stale_after` del formato OKF en la capa Gold.** No se agregaron: obligaría a regenerar todos los documentos y a reindexar a un día de la sustentación, sin cambiar lo que responde el agente. Hoy la frescura se cubre con `fecha_extraccion`, `fecha_publicacion` y `hash` en cada documento.
- **Skill propia.** Ya existe y vive en su propio repositorio público (`mariastefuentes/taaml-skills`, skill `corpus-medallion`), con su reporte de SkillSpector en `docs/skillspector-corpus-medallion.md`; no se duplica en este repositorio.
