# Informe técnico final: agente de Celsia por WhatsApp

**Curso:** Técnicas avanzadas de IA aplicadas en modelos de lenguaje (Maestría en Inteligencia Artificial y Ciencias de Datos, UAO, 2026-2S)
**Grupo 4:** María Stella Fuentes Díaz, Juan José Mosquera, Nicolás Bolaños y Jensen Tamayo
**Fecha:** 20 de noviembre de 2026 · **Sustentación:** 21 de noviembre de 2026
**Código:** https://github.com/mariastefuentes/taaml-celsia-asistente (público; las decisiones están en `docs/decisiones.md`)

## Resumen

Celsia publica su información en más de mil páginas y un cliente no tiene dónde preguntar y recibir la respuesta con su fuente. El proyecto construyó, en tres módulos, un asistente que responde solo con el contenido oficial de celsia.com y dice «no tengo esa información» cuando la fuente no lo trae. El Módulo 1 armó el corpus (393 documentos, 1.690 fragmentos) y un sistema de preguntas y respuestas con RAG. El Módulo 2 lo convirtió en un agente con memoria, herramientas y enrutamiento. El Módulo 3, que este informe detalla, lo llevó a producción por la **Ruta A**: una API REST con FastAPI, cinco herramientas de LangChain con esquemas Pydantic estrictos, memoria en PostgreSQL, aprobación humana para los reclamos y un **servidor de integración propio** (Vía 2, sin N8N) que atiende a los clientes por WhatsApp con la API Cloud de Meta.

El agente se midió con la matriz de enrutamiento (32 de 33 preguntas con la herramienta esperada), preguntas de energía (7 de 8 respondidas, la octava con «no hay información»), preguntas ajenas (10 de 10 rechazadas) y respuestas honestas con una herramienta caída (6 de 6). Hay 330 pruebas automáticas sin modelos ni red. Como componente opcional, se analizaron 114 conversaciones simuladas con embeddings y t-SNE en 2D y 3D: los vectores recuperan la estructura por tema (índice de Rand ajustado de 0,45) y la lectura de las conversaciones marcadas como fallidas muestra que la tasa de fallo útil es de 4 %, no de 18 %.

Lo que **no** está probado se dice en la sección 11: el canal de WhatsApp se verificó con Meta real solo en parte, el número de prueba de Meta solo conversa con cinco destinatarios autorizados, y las conversaciones reales analizadas son seis, insuficientes para concluir algo sobre ellas.

## 1. Problema y solución

**El problema.** Un cliente de Celsia que escribe por primera vez tiene dudas básicas: cómo pagar la factura, cómo reportar un daño, dónde hay una sede o a qué hora atienden. La respuesta está repartida entre un sitio de cientos de páginas, una línea telefónica, WhatsApp y oficinas. Eso genera esperas y carga a la atención humana. Además, en un servicio público un dato inventado (un plazo, un precio, un teléfono) causa un daño real, por lo que el canal debe ser **preciso** y **reconocer cuando no sabe**.

**La solución.** Un agente conversacional de RAG (generación aumentada por recuperación, Lewis et al., 2020) sobre el contenido oficial. El modelo no responde de memoria: decide qué herramienta usar (datos exactos, búsqueda por significado, memoria del cliente o radicar un reclamo), recibe fragmentos con su fuente y responde con ellos. Se construyó en tres módulos:

| Módulo | Qué entregó | Resultado medido |
|---|---|---|
| 1. Corpus y Q&A | Scraping, limpieza en capas Bronze, Silver y Gold, 1.690 fragmentos, embeddings y un Q&A con resumen y FAQ | La respuesta está entre los 12 fragmentos recuperados en el 89 % de 35 preguntas (con las mismas preguntas que motivaron el diccionario de sinónimos); 4 de 4 ataques de inyección directa y 4 de 4 indirectos rechazados |
| 2. Agente | Agente `create_agent` con memoria, herramientas, enrutador por prompt, blindaje, API FastAPI con streaming y frontend React | 30 de 31 elecciones de herramienta correctas; un turno tarda 8,4 s de mediana; 11 ataques directos y 8 indirectos rechazados |
| 3. Producción | Cinco herramientas con esquemas estrictos, PostgreSQL, aprobación humana, servidor propio de WhatsApp, límite de uso, panel en vivo, análisis t-SNE | Secciones 5 a 10 |

![Pipeline de datos: de celsia.com a los fragmentos indexados](../capturas/pipeline.png)

## 2. Evolución arquitectónica: del Módulo 2 al Módulo 3

El Módulo 2 dejó un agente que funcionaba en una máquina, con una interfaz propia. El Módulo 3 lo convirtió en un servicio al que se llega desde un teléfono. Lo que cambió:

| Aspecto | Módulo 2 | Módulo 3 | Por qué |
|---|---|---|---|
| Canal | Frontend React por HTTP con streaming (SSE) | **WhatsApp** (webhook propio) además del frontend y `POST /chat` | Que un servicio externo pueda hablar con el agente (D7, D10) |
| Modelo | `gemini-3.8-flash` | `deepseek-flash`, con Gemini y `llama3.2` local como respaldo en cadena | Costo y disponibilidad; el respaldo evita dejar al cliente sin respuesta (D8) |
| Memoria | SQLite (`SqliteSaver` y `SqliteStore`) | **PostgreSQL** (`PostgresSaver` y `PostgresStore`) | Varias instancias de la API comparten memoria y una pausa de aprobación sobrevive a un reinicio (D4) |
| Herramientas | 4 | **5**, todas con esquema Pydantic estricto (`radicar_reclamo` es la nueva) | Function calling estricto: los argumentos se validan antes de ejecutar |
| Acciones | Solo lectura y memoria del cliente | Radicar un reclamo, **con aprobación humana** (`HumanInTheLoopMiddleware`) | Una acción que cambia algo fuera de la conversación no la decide el modelo solo (D11, D16) |
| Prompt | v4 | **v7** | Corrige el rechazo de preguntas válidas de energía y el «ya guardé» con una herramienta caída (D14) |
| Protección | Rechazo de inyecciones | + límite de 8 mensajes por minuto por teléfono, firma de Meta, clave para `/chat`, token para aprobar | El bot es público durante la demo (D13) |
| Observación | Trazas en LangSmith | + panel en vivo, chequeo previo, plan B | Se ve qué hace el agente mientras responde (D18, D19) |
| Análisis | Embeddings del corpus | + **t-SNE sobre conversaciones** | Ruta transversal A (D15) |

## 3. Diagrama de extremo a extremo

El camino de un mensaje, del usuario a la respuesta:

![Un mensaje de WhatsApp, paso a paso](../capturas/secuencia_whatsapp.png)

1. **Usuario → Meta.** La persona escribe al número de WhatsApp Business. Meta lo recibe en su API Cloud.
2. **Meta → túnel → API.** Meta firma el aviso (`X-Hub-Signature-256`) y lo envía por POST a `/webhook/whatsapp`. Como la API corre en un computador local, un túnel de Cloudflare la expone por HTTPS.
3. **API.** Comprueba la firma, responde 200 de inmediato (para que Meta no reintente) y atiende el mensaje en segundo plano. Descarta avisos repetidos por identificador y aplica el límite por teléfono. Los saludos y `/nuevo` se resuelven sin llamar al modelo.
4. **Agente.** El teléfono se convierte en un hash que sirve de identificador de la conversación; el agente (`create_agent`) lee su historial en PostgreSQL, arma el prompt v7 y decide si responde o llama a una herramienta.
5. **LLM y herramientas.** DeepSeek elige la herramienta con function calling; Pydantic valida los argumentos. Los datos exactos salen de tablas locales; la búsqueda por significado, de Qdrant con embeddings de Ollama.
6. **Memoria.** El turno se guarda en PostgreSQL bajo el hilo del cliente.
7. **Retorno.** La API envía la respuesta por la Graph API de Meta, que la entrega en el teléfono.

El detalle del agente, con sus componentes intermedios (resumen, validación del reclamo, tope de llamadas y aprobación humana):

![Arquitectura de punta a punta del agente](../capturas/arquitectura_agente.png)

## 4. Ruta A y justificación de las decisiones

El Módulo 3 ofrece dos rutas: la **Ruta A** (LangChain, API REST y WhatsApp) y la **Ruta B** (un sistema operativo de agentes, OpenFang, con memoria en capas, «Hands» y puentes a Telegram o WhatsApp). Son alternativas: se elige una. El grupo eligió la A.

**Por qué la Ruta A.** (1) El agente del Módulo 2 ya estaba hecho con LangChain, con herramientas, memoria y recuperación; la Ruta A lo lleva a producción, mientras que la B exige reconstruirlo en otro sistema. (2) La Ruta B implica instalar un runtime distinto, migrar toda la base de conocimiento a su memoria y escribir los manifiestos de las operaciones autónomas, un trabajo con su propia curva de aprendizaje. (3) Lo medido y probado hasta ahora (esquemas de herramientas, PostgresSaver, aprobación humana, webhook, 330 pruebas, análisis de conversaciones) pertenece a la Ruta A. No se evaluó OpenFang en este proyecto, así que la comparación se argumenta y no se midió.

**Vía 2 (servidor propio) frente a Vía 1 (N8N).** Dentro de la Ruta A, la conexión con WhatsApp tiene dos vías: un flujo visual en N8N o un manejador de webhook escrito en FastAPI. Se eligió el servidor propio (D10):

| | N8N (Vía 1) | Servidor propio en FastAPI (Vía 2, elegida) |
|---|---|---|
| Piezas a mantener | Dos servicios (N8N y la API) | **Uno** |
| Pruebas | Difíciles de automatizar | 15 pruebas del webhook (firma, reintentos, límite, aprobación) |
| Estado | En un sistema externo | En nuestra base de datos |
| Lógica | En un flujo visual | En el repositorio, revisada por pull request |
| Velocidad de armado | **Más rápido, sin código** | Más código |
| Exposición | N8N ya trae su dirección pública | Hay que exponer el servidor con un túnel (la dirección cambia en cada arranque) |

Lo que se pierde: N8N habría sido más rápido de armar y se modifica sin código. El servidor propio exige un túnel y atender detalles de Meta (firma, reintentos, ventana de 24 horas).

## 5. Herramientas y function calling estricto

El agente se construye con `create_agent` de LangChain 1.x, que corre sobre LangGraph. En cada turno el modelo recibe las herramientas con su esquema (JSON Schema generado desde Pydantic) y responde con una **llamada estructurada** (nombre y argumentos). Pydantic valida los argumentos de nuestro lado antes de ejecutar; el prompt solo guía la elección. No se interpreta texto libre.

| Herramienta | Para qué sirve | Tipo |
|---|---|---|
| `consultar_datos` | Dato exacto: sedes, contactos y catálogo, con filtros por ciudad y tipo | Lectura |
| `buscar_en_base` | Búsqueda por significado en 1.690 fragmentos (embeddings `nomic-embed-text-v2-moe`, Qdrant, coseno) | Lectura |
| `guardar_dato_del_cliente` | Memoria de largo plazo: lo que el cliente cuenta de sí mismo (sin cédulas, claves ni tarjetas) | Escritura de memoria |
| `recordar_datos_del_cliente` | Devuelve lo guardado de ese cliente | Lectura de memoria |
| `radicar_reclamo` | Radica un reclamo (el registro es simulado) | **Acción, con aprobación humana** |

**Esquemas estrictos.** Cada herramienta tiene un `args_schema` de Pydantic que prohíbe campos adicionales (`extra="forbid"`) y limita los valores (por ejemplo, `consultar_datos` solo acepta las tres tablas que existen). Los argumentos inválidos no llegan a la herramienta: el modelo recibe qué campo corregir y reintenta.

**Qué es y qué no es Structured Output.** El tool calling valida **después** de que el modelo genera la llamada y reintenta si falla; no restringe la generación. La salida estructurada con `with_structured_output` y un modelo Pydantic se usa en el flujo de reclamos escrito a mano (`src/taaml/flujo_reclamo.py`, un `StateGraph` con `interrupt`) y en las tareas de Resumen y FAQ del Módulo 1; no en el camino que ve el cliente por WhatsApp. Se dice así para no sobreafirmar.

**Errores de herramientas.** Un componente (`errores_amables`) captura cualquier fallo de una herramienta: el detalle completo va al registro del servidor y el modelo recibe un aviso sin datos internos para que le explique al cliente con cortesía que no pudo verificar y que no se guardó ni radicó nada. Se comprobó con el modelo real (script 42): con una lectura y una escritura rotas a propósito, el agente respondió «no pude verificar la información… llama a la línea 01 8000 112 115» y «no pude guardar tu dato… no quedó registrado», sin filtrar el texto de la excepción. Fue una corrida por caso con un solo modelo; la falla se simuló reemplazando la función de la herramienta.

**Aprobación humana.** `radicar_reclamo` pausa el agente con `HumanInTheLoopMiddleware`; una persona de Celsia decide con `POST /aprobar` (aprobar, rechazar o responder con un mensaje) y el cliente recibe la decisión. La pausa viaja por el checkpointer de PostgreSQL, así que sobrevive a un reinicio. Como el middleware pausa antes de validar, un componente propio rechaza un reclamo inválido (por ejemplo, sin ciudad) antes de que llegue a la persona, con un máximo de dos reintentos.

![Enrutamiento: cómo elige el agente la herramienta](../capturas/enrutamiento.png)

## 6. API REST con FastAPI

El agente dejó de vivir en un script de Streamlit y se expone como un servicio web (`api/main.py`):

| Ruta | Para qué |
|---|---|
| `POST /chat` | **Endpoint principal.** Recibe `{"mensaje": "...", "telefono": "573001234567"}` y devuelve `{"respuesta", "herramientas", "ok", "pendiente"}` |
| `POST /api/chat` | Un turno por streaming (SSE), para el frontend React |
| `GET/POST /webhook/whatsapp` | Verificación y mensajes entrantes de Meta |
| `POST /aprobar` | Una persona aprueba, rechaza o responde un reclamo pendiente |
| `GET /api/salud` | Estado, modelo, almacén vectorial y memoria en uso |
| `GET /panel` y `GET /api/actividad` | Panel en vivo de la demostración |
| `GET/DELETE /api/usuarios/{id}/datos` | Ver y borrar lo que el agente recuerda del cliente |

**Memoria por teléfono.** El teléfono identifica la conversación: se convierte en un hash estable (el número no se guarda) y `PostgresSaver` guarda cada turno bajo ese hilo. Se comprobó en vivo el 20 de noviembre: un número dijo «me llamo Camila y mi reclamo es sobre la factura de Cali», y al preguntar después «¿de qué ciudad te dije que era mi factura?» el agente respondió «de Cali»; otro número hizo la misma pregunta y el agente respondió que no tenía nada guardado. La conversación quedó guardada (cuatro mensajes). Que la memoria sobreviva a un reinicio lo cubre una prueba automática contra un PostgreSQL local real; ese día no se reinició la API para comprobarlo.

**Fallos y límites.** Si el modelo o una herramienta fallan, `POST /chat` devuelve un mensaje cortés con `ok: false` y no un error 500, para que quien llama (WhatsApp) siempre tenga algo que reenviar al cliente. La entrada se valida con Pydantic (teléfono de 7 a 15 dígitos, mensaje de 1 a 1.000 caracteres; si no, 422).

**Seguridad.**
- El webhook de WhatsApp exige la **firma HMAC** de Meta; sin `WHATSAPP_APP_SECRET` queda deshabilitado.
- `POST /chat` pide el encabezado `X-Api-Key` cuando el servidor define `CHAT_TOKEN` (en el servidor de la demostración está definida). Sin esa variable queda abierto y solo lo frena el límite por teléfono.
- `POST /aprobar` y el panel piden `X-Aprobador`; sin `APROBADOR_TOKEN` quedan deshabilitados.
- Límite de **8 mensajes por minuto** por teléfono en `/chat` y WhatsApp, y por origen en `/api/chat` (429 con `Retry-After`).
- El contexto recuperado se trata como datos pasivos y se limpia de caracteres invisibles; el modelo recibe la orden de ignorar instrucciones dentro de los datos.

## 7. Integración con WhatsApp (Vía 2)

El servidor de integración está construido directamente en FastAPI (`src/taaml/whatsapp.py` y `api/main.py`), sin N8N ni otro intermediario:

- **Recepción.** `GET /webhook/whatsapp` responde la verificación con el token que se registra en Meta. `POST /webhook/whatsapp` comprueba la firma, lee los mensajes (texto, respuestas a botones, audio) y los atiende en segundo plano. Ignora los avisos de estado, pero registra los que Meta marca como fallidos con su código (por ejemplo, 131031 «cuenta bloqueada»).
- **Envío.** Mensajes de texto y mensajes con hasta tres botones por la Graph API; cada mensaje se marca como leído y se muestra «escribiendo…» mientras el agente piensa.
- **Menú y comandos.** «Hola», «menú» o «ayuda» responden con tres botones (sedes y canales, poner un reclamo, Celsia Solar) sin llamar al modelo. `/nuevo` borra la conversación y conserva lo que el cliente contó de sí mismo.
- **Aprobación por botones.** Si se define `APROBADOR_WHATSAPP`, la persona que aprueba recibe el reclamo con «Aprobar» y «Rechazar»; `POST /aprobar` sigue funcionando.

**Qué se verificó con Meta real.** El 20 de noviembre de 2026, con el número de prueba de Meta, el mensaje «Hola» llegó al servidor por el túnel, el agente lo atendió y **el menú con los tres botones se entregó en el celular**. Se comprobaron la firma, la verificación del webhook y la suscripción de la cuenta a la aplicación. El resto del flujo (respuestas del agente, aprobación y voz) se probó con avisos simulados y pruebas automáticas.

**Lo que Meta impone y hay que saber:**
- El número de prueba solo conversa con **hasta cinco destinatarios autorizados**, que confirman un código. Abrirlo a cualquier persona exige un número real y la verificación del negocio, que no se hicieron.
- El token de acceso temporal vence en pocas horas y hay que renovarlo antes de cada uso.
- Los botones y los mensajes iniciados por la empresa solo llegan dentro de las 24 horas desde el último mensaje de la persona.
- La cuenta de WhatsApp Business figura con envío «bloqueado» en su estado de salud (método de pago pendiente y negocio sin verificar). Una cuenta anterior llegó a bloquearse por completo y se reemplazó; la actual entregó mensajes el 20 de noviembre, pero el riesgo de un bloqueo no está descartado.

## 8. Memoria conversacional

![Memoria: checkpointer frente a Store](../capturas/memoria.png)

- **Corto plazo (checkpointer).** `PostgresSaver` guarda cada conversación completa, incluidas las llamadas a herramientas, bajo un hilo. El modelo ve solo los últimos ~3.000 tokens; si lo guardado pasa de 8.000, un resumen automático reemplaza lo antiguo.
- **Largo plazo (Store).** `PostgresStore` guarda lo que el cliente cuenta de sí mismo en un espacio propio por cliente; un cliente no puede leer lo de otro, y los anónimos no tienen memoria de largo plazo. El cliente puede ver y borrar lo que se recuerda.
- **Alternativa.** Sin `DATABASE_URL`, el mismo código usa SQLite (`make api-sqlite`).
- **Privacidad.** El teléfono nunca se guarda: solo su hash. Los datos personales de clientes caen bajo la Ley 1581 de 2012; en una operación real habría que definir plazos de retención.

## 9. Resultados

| Medición | Resultado |
|---|---|
| Matriz de enrutamiento (herramienta esperada en 33 preguntas) | **32 de 33**; la que falla (R31) ya fallaba con versiones anteriores del prompt |
| Preguntas de energía, con búsqueda | 7 de 8 respondidas; la octava dijo con honestidad que no hay información |
| Preguntas ajenas a Celsia | 10 de 10 rechazadas |
| Con el almacén de memoria caído | 6 de 6 respuestas honestas |
| Herramienta rota a propósito (script 42, modelo real) | 2 de 2 respuestas corteses, sin inventar y sin filtrar el error |
| Recuperación (Módulo 1) | 89 % con embeddings (54 % por palabras, 74 % híbrido) |
| Pruebas automáticas | 330, sin modelos ni red |
| Latencia | Mediana de 8,4 s por turno en el Módulo 2 (2,1 a 23 s); el panel de la demostración registró de 1,5 a 10,9 s en los turnos de WhatsApp del 20 de noviembre, y unas corridas sueltas con herramientas tardaron de 12 a 22 s |
| Costo | Unos 0,02 USD por una conversación de cuatro turnos (Módulo 2) |

**Lo que estas cifras no dicen.** El 89 % de recuperación se midió con las mismas preguntas que motivaron el diccionario de sinónimos; con preguntas nuevas sería menor. Las 33 preguntas de la matriz son pocas. Los 8 casos de energía y los 10 ajenos son listas chicas. Una respuesta de WhatsApp tarda de segundos a unas decenas de segundos, y el indicador «escribiendo…» ayuda pero no la acelera.

## 10. Análisis de conversaciones con t-SNE (ruta transversal A)

**Método.** La API ya guarda cada conversación completa en PostgreSQL. `taaml.conversaciones` las lee, marca cuáles terminaron mal y arma el texto de cada una; el cuaderno `notebooks/analisis_conversaciones.ipynb` convierte cada conversación en un vector con el mismo modelo de embeddings del agente (`nomic-embed-text-v2-moe`, 768 dimensiones), la proyecta con t-SNE (van der Maaten y Hinton, 2008) a 2D y 3D, agrupa con K-means sin ver la categoría y compara con KNN en el espacio original.

**Datos.** 114 conversaciones **simuladas**: las preguntas las escribimos nosotros (producto, facturas, reclamos, temas fuera de alcance, saludos, datos personales, mensajes hostiles o ambiguos y mezcladas) y las pasamos por el agente real. Las respuestas, las herramientas y los fallos son del agente; las preguntas no. Las proporciones **no describen a clientes reales**. Las conversaciones reales de los ensayos por WhatsApp son 6, y con menos de 30 los grupos de t-SNE no son confiables; por eso no se concluye nada con ellas. El cuaderno `--reales` (`scripts/36_construir_notebook_tsne.py`) las analiza cuando haya suficientes.

![t-SNE en 2D de las 114 conversaciones simuladas](tsne_conversaciones_2d.png)

Cada punto es una conversación; cerca significa parecida. El color es la categoría que se quiso probar al escribirla; el círculo negro marca las conversaciones en que el asistente dijo que no sabía o no pudo, o una herramienta falló.

![t-SNE en 3D de las 114 conversaciones simuladas](tsne_conversaciones_3d.png)

**Qué revelan los clústeres.**
- **Los vectores capturan el tema.** K-means, sin ver la categoría, recupera la estructura con un índice de Rand ajustado de 0,45 (1 sería idéntico): los reclamos quedan juntos (un clúster de 17 con 88 % de pureza), los datos personales en otro y las preguntas de producto en tres clústeres con pureza de 71 % a 100 %. Se mezclan sobre todo los saludos con las conversaciones largas y las preguntas de factura con las de producto, lo que es razonable porque hablan de lo mismo.
- **KNN frente a t-SNE.** Clasificando cada conversación por sus 5 vecinas más cercanas, KNN acierta la categoría prevista el 61 % de las veces en el espacio original, el 58 % en el t-SNE 3D y el 70 % en el 2D, contra 18 % del azar. Que el 2D saque más no significa que proyectar agregue información: t-SNE exagera los grupos locales y se calculó con todas las conversaciones a la vez. Sirve para **mirar** los grupos; KNN en el espacio original sirve para **buscar** conversaciones parecidas.
- **Dónde falla el asistente.** El asistente marcó 20 conversaciones como fallidas (18 %), pero al leerlas una por una: 15 son rechazos correctos de temas fuera de alcance, 3 son vacíos de la base de conocimiento (precio del cargador, fecha límite de pago, facturación por estimación) y **2 son fallos reales** (rechazó una pregunta de energía que sí debía contestar). La tasa de fallo útil es de **5 de 114 (4 %)** y se concentra en un clúster concreto: las preguntas generales de energía que no nombran a Celsia.
- **Dónde mirar primero.** El clúster que mezcla rechazos correctos con los dos erróneos es el que se revisaría cada semana, y las conversaciones mezcladas tienen la tasa más alta (33 %) porque un solo turno malo marca toda la conversación.

**Límites.** Los datos son simulados; la marca de «fallida» es una regla de palabras, no un juicio humano, y puede pasar por alto respuestas vagas; t-SNE conserva la vecindad local pero no las distancias entre grupos, así que se interpreta qué conversaciones quedan juntas y no qué tan lejos están dos nubes. Con tráfico real habría que leer una muestra de cada clúster antes de concluir.

![t-SNE del corpus: los 1.690 fragmentos del sitio](tsne_corpus.svg)

## 11. Demostración, operación y limitaciones

**La demostración.** Es práctica y sin diapositivas: se muestra la terminal de la API (los registros de cada turno), el panel en vivo (`/panel`, con la herramienta elegida, el tiempo y el estado de cada turno) y el WhatsApp de quien escribe. El guion, con las preguntas y el plan B, está en `docs/guion_demo_whatsapp.md`. Antes de empezar, `make ensayo-whatsapp` revisa claves, Ollama, el índice, la API, el panel, si el token de Meta sigue vivo y si el túnel llega al webhook. Si Meta falla, el plan B repite una conversación real grabada (avisando que es una repetición) o se usa la misma API por `POST /chat` o por el frontend React.

**Limitaciones y riesgos, sin adornos:**
- **El servidor corre en un computador local.** Si se apaga, se suspende o cambia de red, el bot deja de responder. El túnel de Cloudflare cambia de dirección en cada arranque y esa dirección hay que registrarla de nuevo en Meta.
- **Cinco destinatarios.** El número de prueba solo conversa con cinco celulares autorizados (sección 7).
- **Token de Meta temporal** y cuenta con envío marcado como bloqueado en el estado de salud, con el riesgo de un bloqueo.
- **No se probaron con Meta real** las respuestas largas del agente, la aprobación con botones ni las notas de voz (apagadas por defecto y tentativas).
- **El registro del reclamo es simulado**; un sistema real llamaría al de Celsia.
- **Tres vacíos de la base de conocimiento** (precio del cargador, fecha límite de pago, facturación por estimación) no están publicados por Celsia. El agente dice «no tengo esa información» y da la línea 01 8000 112 115. El texto para llenarlos está preparado y no se aplicó porque cambiaría el corpus e invalidaría las mediciones.
- **Una pregunta de enrutamiento falla (R31)** y la compuerta opcional System One (D9) sigue abierta.
- **Latencia de segundos a decenas de segundos** por respuesta.
- **Evaluaciones pequeñas** (33 y 59 preguntas, 8 y 10 casos): sirven para detectar fallos, no para dar tasas estadísticas.
- **t-SNE** con datos simulados (sección 10).

## 12. Conclusiones

El proyecto cumple el recorrido de la Ruta A: un agente de LangChain con cinco herramientas de esquema estricto, una API REST en FastAPI con memoria por teléfono en PostgreSQL y un servidor de integración propio que conecta el agente con WhatsApp sin intermediarios. Dos decisiones marcan el resultado: tratar lo recuperado como datos y no como órdenes, y exigir aprobación humana para lo único que cambia algo fuera de la conversación.

Lo más valioso fue **medir** en lugar de suponer: la matriz de enrutamiento, las preguntas ajenas y el análisis de las conversaciones fallidas mostraron que un 18 % de «fallos» era en realidad un 4 % de fallos reales, y señalaron dónde mirar primero. Lo más frágil no es el agente sino lo que lo rodea: un token que vence, una cuenta de Meta con restricciones, un túnel que cambia de dirección y un computador local. Por eso el proyecto incluye un chequeo previo y un plan B. El siguiente paso natural sería un número real verificado, un despliegue fijo y una muestra de conversaciones reales de clientes para repetir el análisis.

## Anexo A. Reproducir

```
uv sync
make api              # API con PostgreSQL local (puerto 8000)
make ensayo-whatsapp  # chequeo previo de la demostración
make test             # 330 pruebas, sin modelos ni red
make herramienta-caida  # rompe herramientas a propósito con el modelo real (gasta cuota)
```

Las decisiones (D1 a D20), con su porqué y sus límites, están en `docs/decisiones.md`; las especificaciones, en `specs/`.

## Anexo B. Declaración de uso de IA

| Herramienta | Para qué se usó | Cómo se verificó |
|---|---|---|
| Claude Code (Anthropic) | Escribir y revisar código (agente, herramientas, webhook de WhatsApp, aprobación humana, límite de mensajes, análisis de conversaciones), pruebas y documentos | Cada cambio sale por pull request y una persona del equipo lo revisa y debe poder explicarlo; las pruebas y el linter corren antes de fusionar; las cifras se recalculan con los scripts del repositorio |
| DeepSeek por API | Modelo del agente en producción | Matriz de enrutamiento, preguntas de energía y ajenas, y respuestas con una herramienta caída (sección 9) |
| Gemini (`gemini-3.5-flash`, `gemini-3.8-flash`) por API | Modelo del Q&A (Módulo 1) y del agente (Módulo 2); respaldo en el Módulo 3 | Evaluación con 59 preguntas y matriz de enrutamiento |
| `nomic-embed-text-v2-moe` (Ollama, local) | Embeddings de fragmentos, preguntas y conversaciones | Recuperación (hit@k, precisión, recall y nDCG) y análisis t-SNE con sus límites |
| `llama3.2` (Ollama, local) | Respaldo si falla el modelo principal | Probado con pocos casos; no se midió más |
| LangSmith | Trazas de cada turno (pasos, herramientas, tiempos, tokens) | Se compara la traza con lo que respondió el agente |

Todo código o texto generado por una herramienta lo revisa una persona del equipo.

## Referencias

- Lewis, P. et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. arXiv:2005.11401.
- Yao, S. et al. (2022). *ReAct: Synergizing Reasoning and Acting in Language Models*. arXiv:2210.03629.
- Schick, T. et al. (2023). *Toolformer: Language Models Can Teach Themselves to Use Tools*. arXiv:2302.04761.
- Zaharia, M. et al. (2024). *The Shift from Models to Compound AI Systems*. Berkeley AI Research (BAIR) Blog.
- van der Maaten, L. y Hinton, G. (2008). *Visualizing Data using t-SNE*. Journal of Machine Learning Research, 9.
- Greshake, K. et al. (2023). *Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection*. arXiv:2302.12173.
- Wu, Y. et al. (2025). *From Human Memory to AI Memory: A Survey on Memory Mechanisms in the Era of LLMs*. arXiv:2504.15965.
- LangChain: documentación de `create_agent`, memoria a corto plazo, middleware y `HumanInTheLoopMiddleware` (docs.langchain.com).
- Meta: documentación de la API Cloud de WhatsApp (developers.facebook.com).
- Ley 1581 de 2012 de Colombia (protección de datos personales).
