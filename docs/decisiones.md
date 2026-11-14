# Registro de decisiones de arquitectura (Taller 2)

Cada decisión dice qué se decidió, por qué, qué se descartó y dónde está la evidencia. Es el registro versionado de las decisiones del agente: vive en el repositorio y cambia con él. Se redactó el 13 de noviembre de 2026 a partir del informe (`docs/3 - Informe/informe_taller2.md`) y de las especificaciones (`specs/011` y `specs/012`). No está en Engram: Engram es una herramienta externa de memoria para agentes de código y no se usó en este proyecto.

| # | Decisión | Estado |
|---|---|---|
| D1 | Agente `create_agent`, sin `StateGraph` propio | vigente |
| D2 | El router es el modelo con herramientas bien descritas, no un clasificador aparte | vigente |
| D3 | Los números los calcula el código, no el modelo | vigente |
| D4 | Memoria: checkpointer y Store con SQLite por defecto y PostgreSQL con `DATABASE_URL` | vigente |
| D5 | Qdrant local con alias, búsqueda exacta | vigente |
| D6 | Contexto recuperado como datos pasivos, con delimitador y validación | vigente |
| D7 | Interfaz: API FastAPI con SSE y frontend React desacoplado | vigente |
| D8 | Gemini de pago como modelo principal y Ollama como respaldo | vigente |
| D9 | Sin gatekeeper externo (System One) mientras no haya clave | abierta |

## D1. Agente `create_agent`, sin `StateGraph` propio
- **Contexto.** El flujo es un solo ciclo de decisión: modelo, herramienta, modelo.
- **Decisión.** Usar `create_agent` de LangChain 1.x, que corre sobre LangGraph y trae el checkpointer, el Store y el middleware (recorte de historial, resumen, tope de llamadas, respaldo de modelo).
- **Descartado.** Un grafo a mano (más control con más código que mantener), Deep Agents, Agno, LlamaIndex y DSPy (tabla de la sección 2.2 del informe).
- **Excepción.** Donde sí hay ramas y una pausa obligatoria (radicar un reclamo solo con aprobación humana) se escribió un `StateGraph` a mano, aparte del agente: `src/taaml/flujo_reclamo.py`. Conectarlo al agente queda como trabajo posterior.
- **Cuándo se revisa.** Si el agente necesita ramas explícitas o una aprobación humana antes de una acción.
- **Evidencia.** `src/taaml/agente.py`; informe, secciones 2 y 2.2.

## D2. El router es el modelo con herramientas bien descritas
- **Contexto.** Cada pregunta debe ir a datos exactos, a texto del corpus, a ambos o a ninguno.
- **Decisión.** Que el modelo elija entre `consultar_datos`, `buscar_en_base` y la respuesta directa a partir de las descripciones de las herramientas y de `prompts/v3_agente.md`.
- **Descartado.** Un clasificador previo (más llamadas y un punto de fallo extra).
- **Consecuencia.** El enrutamiento se mide, no se asume: matriz de 28 preguntas con la herramienta esperada, y las preguntas de conteo y de varias ciudades ya cuentan con su caso.
- **Evidencia.** `docs/2 - Conjunto de prueba/matriz_enrutamiento.csv`, `scripts/22_matriz_enrutamiento.py`, informe 4.2 y 5.1.

## D3. Los números los calcula el código
- **Contexto.** Un modelo que suma o cuenta puede equivocarse, y una cifra mal dicha sobre sedes o tarifas es un error de cara al cliente.
- **Decisión.** `consultar_datos` devuelve el total ya calculado, incluida la suma de varias ciudades. Además, `datos_dudosos` revisa que cada cifra, correo y enlace de la respuesta aparezca en lo que devolvieron las herramientas.
- **Evidencia.** `src/taaml/consulta_datos.py`, `tests/test_consulta_datos.py`.

## D4. Memoria con SQLite por defecto y PostgreSQL por configuración
- **Decisión.** `SqliteSaver` y `SqliteStore` sin servidor para desarrollar y demostrar; con `DATABASE_URL` se usan `PostgresSaver` y `PostgresStore`. La memoria de largo plazo guarda lo que el cliente cuenta de sí mismo bajo el namespace `("perfil", usuario)`, con tope de 20 datos y borrado por el cliente.
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
- **Decisión.** `gemini-3.8-flash` (indicación del profesor: API de pago y modelo reciente), con `llama3.2` en Ollama como respaldo. Ollama también calcula los embeddings.
- **Límite declarado.** Gemini ignora `temperature` y `top_p`; el texto varía y se compensa con las herramientas, la validación y el «No tengo esa información».
- **Evidencia.** `specs/011-agente-memoria-y-router`, informe 7.

## D9. Gatekeeper System One (Jev): abierta
- **Contexto.** El enunciado lo pide solo «si está disponible». Es una API comercial y requiere una clave.
- **Decisión pendiente.** Si hay clave, se añade como compuerta opcional (`Noul` para decidir si hace falta RAG, `Choice` para saludo, consulta o fuera de dominio) y se mide contra la matriz. Si no la hay, se documenta como no usado.
