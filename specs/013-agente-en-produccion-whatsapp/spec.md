---
estado: implementada; falta la prueba con Meta real
escrita: 2026-11-18
---
# Spec 013: el agente en producción (Módulo 3, Ruta A, vía 2)

Nace de la actividad del Módulo 3: llevar el agente del Módulo 2 a una aplicación de grado de producción que atiende a clientes por WhatsApp. Se eligió la **Ruta A** (LangChain, API REST y WhatsApp) con la **vía 2**: servidor de integración propio en FastAPI, sin N8N (justificación en `docs/decisiones.md`).

## Qué se necesita
1. **Function calling con esquemas estrictos.** Cada una de las 5 herramientas tiene un esquema Pydantic (`args_schema`, `extra="forbid"`, largos y valores permitidos). El modelo elige la herramienta por function calling, no por texto libre; el `strict` del proveedor no se usa (DeepSeek lo ofrece solo en un endpoint beta), la validación es nuestra.
2. **Componentes de LangChain exigidos.** `init_chat_model`, `create_agent`, `HumanInTheLoopMiddleware`, `RecursiveCharacterTextSplitter`, vectorstore y embeddings nativos (`QdrantVectorStore`, subclase de `OllamaEmbeddings`), `dynamic_prompt` (modo de RAG en cadena, `RAG_MODO=cadena`) y `PostgresSaver`.
3. **Errores cortés.** Si una herramienta falla, el cliente recibe un mensaje amable que dice que no se pudo verificar, ofrece otra ayuda y no afirma que algo quedó guardado o radicado.
4. **API REST.** `POST /chat` recibe `{mensaje, telefono}`, mantiene la memoria por teléfono (se guarda su hash) y devuelve JSON; si el agente falla, devuelve un mensaje cortés con `ok: false`.
5. **WhatsApp sin intermediarios.** `GET/POST /webhook/whatsapp`: verificación del webhook, firma `X-Hub-Signature-256`, respuesta 200 enseguida, atención en segundo plano, mensajes repetidos descartados por id y envío de la respuesta por la Graph API.
6. **Aprobación humana.** `radicar_reclamo` pausa el flujo hasta que una persona decide con `POST /aprobar` (encabezado `X-Aprobador`); el cliente recibe la decisión por WhatsApp. Los argumentos se validan antes de pausar.
7. **Protección de la cuota.** Límite de mensajes por teléfono (8 por minuto, configurable): `/chat` responde 429 y por WhatsApp se avisa una sola vez por ventana.
8. **Análisis de conversaciones (opcional, Ruta Transversal A).** Las conversaciones completas ya quedan en PostgreSQL; un cuaderno las convierte en vectores, las proyecta con t-SNE en 2D y 3D y analiza dónde falla el asistente.

## Cómo se comprueba
- `tests/test_agente.py`: esquemas estrictos, router por function calling, errores cortés, RAG en cadena, aprobación humana y validación del reclamo antes de pausar (con modelos simulados).
- `tests/test_whatsapp.py`: verificación, firma, reintentos, tipos de mensaje no soportados, envío y aviso de la decisión.
- `tests/test_memoria_postgres.py`: una aprobación pendiente sobrevive al reinicio del proceso con PostgreSQL real (local).
- `tests/test_limite.py` y `tests/test_conversaciones.py`.
- Con el agente real (prompt v7): 7 de 8 preguntas de energía respondidas, 10 de 10 ajenas rechazadas, 6 de 6 respuestas honestas con el Store caído y matriz de enrutamiento 32 de 33 (la que falla, R31, ya fallaba).

## Lo que se aprendió
- Con `args_schema`, el parámetro `runtime` tiene que declararse en el esquema (`Field(exclude=True)`); sin él, LangChain no lo inyecta y la herramienta falla en silencio. El modelo no lo ve: lo comprueba una prueba.
- `HumanInTheLoopMiddleware` pausa antes de validar los argumentos; por eso se agregó un `after_model` propio, colocado después en la lista (corren en orden inverso).
- Un script de análisis con varios hilos debe crear las tablas de la memoria con una primera conversación en solitario; si no, los hilos chocan al crearlas.
- El análisis t-SNE mostró que la marca de «conversación fallida» mezcla rechazos correctos con fallos reales: de 20 marcadas, 5 eran fallos (4 % de 114).

## Fuera de alcance y pendiente
- **Prueba con Meta real.** El webhook se probó con avisos firmados simulados; falta la cuenta de Meta, sus claves y el ensayo con un teléfono. Sin verificar: el límite de destinatarios del número de prueba y la caducidad del token temporal.
- N8N (vía 1): no se implementa; el plan B de la demo es `POST /chat` y el frontend.
- Un sistema real de radicación: el registro de reclamos es simulado (`radicar_simulado`).
- Despliegue en un servidor fijo: hoy se usa un túnel https.
- Datos reales para el t-SNE: el cuaderno usa 114 conversaciones simuladas.
