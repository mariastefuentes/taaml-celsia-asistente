# Guion de la sustentación final (28 de noviembre de 2026)

Grupo 4 — Celsia. Último bloque del día: **10:45 a 11:00**. Quince minutos sin diapositivas, sin video y sin leer: **7 minutos de pitch**, **8 minutos de discusión técnica** con el público experto. Los invitados escriben desde su teléfono.

> Este guion reemplaza al del 21/11 (`docs/guion_demo_whatsapp.md`). Lo nuevo: **20 herramientas**, **OpenClaw versionado** y una demo por el **WhatsApp de OpenClaw** (QR); Meta no se usa (D56). Lo medido antes del 23/11 se cita con su fecha y su prompt; lo que no se volvió a medir, no se afirma.

## Reparto (confirmar en el grupo antes del sábado)

| Quién | Qué defiende |
|---|---|
| Juan José Mosquera | Apertura y cierre del pitch; arquitectura de punta a punta; demo desde el teléfono |
| María Stella Fuentes | Datos, RAG y evaluación (pipeline, Qdrant, métricas, t-SNE) |
| Nicolás Bolaños | Seguridad e inyección; pruebas; panel y métricas en vivo |
| Jensen Fabián Tamayo | OpenClaw (gateway, workspace, sandbox, acceso, auditoría) y herramientas |

Quien aprueba un reclamo en vivo **no es** quien está presentando: es otra persona del equipo, en el panel del computador del bot.

## Antes de las 8:00 a. m. (nuestro turno es a las 10:45)

Todo queda encendido y probado antes de las 8:00, y se vuelve a comprobar a las 10:30.

- Los invitados deben estar registrados en la pestaña 2 de la hoja de grupos del curso (Nombre, Cédula, Cargo) **antes del evento**: sin registro no se aceptan. Esos datos van solo en esa hoja.
- Computador del bot con cargador, sin suspensión, y los datos del celular como internet de respaldo.
- Terminal 1: `make api` y comprobar `http://127.0.0.1:8000/api/salud` (`almacen: qdrant`, `memoria: postgresql`, `allowlist_whatsapp: abierta`, `avisos_openclaw: true`).
- Terminal 2: `openclaw gateway` y, en otra, `openclaw channels status --probe`.
- Quien aprueba abre `http://127.0.0.1:8000/panel`, escribe su clave y pulsa «Ver». Cuando hay algo por decidir, la pestaña dice «(1) Por aprobar». Arriba, cuatro luces dicen si el asistente, la búsqueda, la memoria y el puente de WhatsApp contestan; rechazar pide confirmar y «Ver respuesta» muestra lo que se le contestó a cada cliente. Si el QR se proyecta desde el panel, tocarlo para agrandarlo.
- Si se va a mostrar el chat web, pulsar abajo «Ver detalles técnicos»: las fuentes (documento y fragmento), las herramientas usadas y el costo quedan a la vista.
- Dos preguntas de calentamiento, de las que no se van a mostrar.
- QR del bot proyectado: en el bot el invitado no tiene que registrarse, solo escanea y escribe.
- Para la parte técnica, dejar abiertos el código en el editor, la ventana de la API, `openclaw logs --follow` y el panel: se muestran código, trazas y registros, no capturas.

## Minuto a minuto

### 0:00 – 7:00 · Elevator pitch

| Minuto | Qué se dice | Qué se ve |
|---|---|---|
| 0:00 – 0:40 | **Problema.** La información de Celsia está en más de mil páginas; quien necesita una sede, un requisito o un reclamo termina llamando o buscando a ciegas. | Nada más que la voz; el teléfono en la mano |
| 0:40 – 1:20 | **Propuesta.** Un asistente que responde por WhatsApp con información oficial, cita la fuente cuando se la piden, recuerda lo que el cliente contó y no inventa: si no está en la base, lo dice. | Diagrama de arquitectura abierto en segundo plano (no se lee) |
| 1:20 – 2:00 | **Qué es distinto.** 20 herramientas tipadas que el modelo elige solo, memoria que sobrevive al reinicio y una persona que aprueba los reclamos. | El diagrama de enrutamiento (los caminos de una pregunta) |
| 2:00 – 4:30 | **Demo real.** «Escriba al bot, por favor»: el invitado pregunta una sede, luego «¿Qué es una granja solar?», escribe «fuente» justo después y pregunta qué sabe de él. | El teléfono del invitado y la terminal con la traza |
| 4:30 – 5:30 | **Un reclamo con aprobación humana.** El invitado pide un reclamo, alguien del equipo lo aprueba en el panel y la respuesta le llega a su WhatsApp. | El teléfono del invitado y el panel |
| 5:30 – 6:20 | **Lo que se midió.** Banco verificable 49 de 49 y matriz de enrutamiento 40 de 43, con las 20 herramientas el 26/11 (D67); ataques directos 11 de 11 y órdenes escondidas 8 de 8 el 26/11. Si una cifra no se volvió a medir, se dice. | El panel en vivo, no una lámina |
| 6:20 – 7:00 | **Cierre.** Para qué le sirve a un cliente de Celsia en el Valle del Cauca o el Tolima, y lo que falta: más tráfico real y conectarse a los sistemas de Celsia (hoy los reclamos son simulados). | — |

**Reglas del pitch:** no decir «nuestro chatbot»; decir qué problema resuelve. No prometer integración con sistemas de Celsia. No citar una cifra que no esté en el repositorio.

### 7:00 – 12:00 · Discusión técnica

| Minuto | Tema | Quién |
|---|---|---|
| 7:00 – 7:40 | **Recorrido de un mensaje**: WhatsApp → OpenClaw → plugin (fija el remitente) → puente → `POST /chat` → agente → herramienta → PostgreSQL → respuesta | Juan José |
| 7:40 – 8:30 | **20 herramientas**: por qué 20 y no 5; esquemas Pydantic, `APROBACION_HUMANA`, qué se retiró (`consultar_datos`) y por qué; el MCP de solo lectura | Jensen |
| 8:30 – 9:15 | **Datos y RAG**: Bronze → Silver → Gold → curaduría → fragmentos; Qdrant con payload; mezcla significado + palabras; recuperación: 91 % en el Q&A (12 fragmentos) y 80 % en el agente (4 fragmentos), sobre 35 preguntas, las mismas con las que se ajustaron los sinónimos | María Stella |
| 9:15 – 10:00 | **Memoria y evaluación**: `PostgresSaver` frente a `Store`; el hilo sobrevive al reinicio; t-SNE/UMAP de 114 conversaciones simuladas, recalculados con Gemini el 26/11 (índice de Rand 0,53; KNN 74 % frente a 18 % del azar), y sus límites | María Stella |
| 10:00 – 10:45 | **OpenClaw**: plantilla versionada (`openclaw/openclaw.example.json`), `bind: loopback`, `tools.deny`, `fs.workspaceOnly`, sandbox Docker, acceso abierto a propósito y `security audit`; workspace con identidad y límites separados | Jensen |
| 10:45 – 11:30 | **Seguridad**: inyección directa (11/11) e indirecta (8/8, leída a mano: una falsa alarma de la regla), ambas el 26/11, límite por teléfono, clave en `/chat`, HITL, sin `.env` en el repo | Nicolás |
| 11:30 – 12:00 | **Calidad**: `uv sync`, 547 pruebas aprobadas (`make test`), ruff, pre-commit, CI y `make verificar-clon`; lo que no está probado (muchas personas a la vez) | Nicolás |

Cada quien responde lo suyo. Si una pregunta cae en terreno ajeno, se contesta con lo que se sabe y se pasa la palabra; no se improvisa una cifra.

### 12:00 – 15:00 · Preguntas del público

Respuestas preparadas, por si aparecen:

- **«¿De dónde sacó eso?»** En el mismo WhatsApp se escribe «fuente» y salen el documento, el fragmento y el enlace de la última respuesta (D61).
- **«¿Y si el modelo alucina?»** Tres capas: solo fragmentos recuperados, nota «dato sin respaldo» cuando una cifra no está en la fuente y banco verificable de 49 casos: 49/49 el 26/11, con las 20 herramientas.
- **«¿Por qué cualquiera le puede escribir? ¿Y la allowlist?»** Está abierto a propósito, para que cualquier invitado lo pruebe. La rúbrica pide allowlist y hoy no hay lista de números: se dice así. Lo que protege: límite de 8 mensajes por minuto por teléfono en nuestro servidor, el bot no tiene herramientas para ejecutar programas ni abrir archivos del computador (`tools.deny`) y los reclamos necesitan aprobación humana.
- **«¿Por qué no un modelo local?»** El anuncio pide no usarlo: el modelo del agente, sus respaldos y los embeddings (Gemini) van por API en la nube, con las claves en variables de entorno (D51).
- **«¿Qué pasa si falla WhatsApp?»** El plan B es el chat web con QR, con el mismo agente. Como último recurso, `make demo-plan-b` repite una conversación real grabada el 27/11 con `deepseek-flash`: la pantalla avisa que es una repetición, y se dice.

## Versión en inglés (décimas de 5.1 y 5.2)

Si se sustenta en inglés, el pitch y la discusión se hacen en inglés; las preguntas pueden ser en los dos idiomas. Guion corto:

1. **Problem** — Celsia's public information is spread over a thousand pages; customers call or search blindly for a branch, a requirement or a complaint.
2. **What we built** — a WhatsApp assistant grounded on official content: it cites its source, remembers what the customer told it, refuses to invent, and routes each question to one of 20 typed tools.
3. **Demo** — a guest types: a branch in Ibagué, a billing question, "what do you know about me?", then a complaint that a team member approves on the live panel.
4. **Technical highlights** — an OpenClaw gateway with a versioned hardened config and Docker sandbox; a plugin that fixes the verified sender and bridges to the FastAPI agent; PostgreSQL checkpointer and Store; Qdrant retrieval that combines meaning and keyword search; LangGraph middleware for summarization, tool limits and human-in-the-loop; a read-only MCP server.
5. **Evidence** — verified bank 49/49 and routing matrix 40/43, measured with the 20 tools on 26 November; direct prompt-injection 11/11 and indirect 8/8 on 26 November. We say which numbers were not re-measured.
6. **Limits and next steps** — real Celsia systems are out of scope; next is measuring real traffic.

## Si algo falla

Se dice en voz alta y se muestra el repositorio: qué falló, qué se intentó y qué se aprendió. El plan B es el chat web con QR. Lo que no se hace es cambiar de computador a último minuto ni mostrar una captura como si fuera una respuesta en vivo.

Si se aprueba un reclamo y el aviso no llega solo al teléfono, el invitado escribe «hola» y el aviso sale con la respuesta.
