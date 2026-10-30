# Informe del Taller 1: asistente de preguntas y respuestas de Celsia

**Versión para entrega.** Las cinco secciones y la declaración de uso de IA están escritas con los datos del proyecto al 28/10/2026; las cifras se volvieron a calcular desde los archivos de resultados. Las 59 respuestas se revisaron contra la base: los veredictos los propuso Claude Code con evidencia de la base y los ratificó María Stella Fuentes (`docs/2 - Conjunto de prueba/revision_manual.md`).

Curso: Técnicas avanzadas de IA aplicadas en modelos de lenguaje (UAO). Empresa asignada al grupo: **Celsia**.
Documentos de apoyo: [análisis de la empresa](../1%20-%20Analisis%20de%20la%20empresa/analisis_empresa.md), [conjunto de prueba](../2%20-%20Conjunto%20de%20prueba/conjunto_de_prueba.md) [comparación de modelos](../2%20-%20Conjunto%20de%20prueba/comparacion_modelos.md) y [recuperación por pregunta](../2%20-%20Conjunto%20de%20prueba/recuperacion_por_pregunta.md).

## Resumen

Celsia publica su información en más de mil páginas y un cliente no tiene dónde preguntar y recibir la respuesta con su fuente. Se construyó un asistente que responde solo con el contenido oficial de celsia.com en español y cita la fuente de cada dato. El scraping descubrió 1.273 direcciones y descargó 1.272; tras limpiar, deduplicar y curar quedaron 393 documentos, divididos en 1.690 fragmentos. Para cada pregunta se recuperan los 12 fragmentos más parecidos (embeddings y Chroma) y solo con ellos responde `gemini-3.5-flash`, en lugar de enviar toda la base (unas 80 veces más entrada y costo por pregunta).

Con 59 preguntas de prueba, la respuesta está entre los 12 fragmentos en el 89 % de los casos (31 de 35). En la revisión de una persona, 29 de 35 respuestas convencen y 6 son parciales, y 19 de 24 negativas convencen; 4 de 4 ataques directos de inyección y 4 de 4 indirectos fueron rechazados. Las limitaciones principales: 35 preguntas dan poca precisión estadística, el diccionario de sinónimos se escribió mirando esas preguntas y los PDF del sitio no se descargaron porque su `robots.txt` los bloquea.

## 1. Descripción del problema

**La empresa.** Celsia es la empresa de energía del Grupo Argos. Genera, transmite, distribuye y comercializa energía, con foco en fuentes renovables, y también ofrece internet. En Colombia atiende a clientes del Valle del Cauca y del Tolima.

**El contexto.** En el ranking «500 empresas del Valle del Cauca» de El País (2025), Celsia Colombia aparece en el segundo lugar por ingresos operacionales (5.024 en la tabla de la fuente, con una variación de −22,6 % frente a 2024).

**El problema.** Un cliente que escribe por primera vez tiene dudas básicas: cómo pagar la factura, cómo reportar un daño, qué trámites puede hacer, dónde hay una sede o a qué hora atienden. La respuesta está repartida en un sitio de cientos de páginas, una línea telefónica, WhatsApp y oficinas. Eso genera esperas y carga a la atención humana.

**La necesidad.** Un canal automático, disponible siempre y **preciso**: que responda solo con información oficial y que **reconozca cuando no sabe**, en vez de inventar un plazo, un precio o un teléfono. En un servicio público, un dato inventado causa un daño real al cliente.

**Alcance.** Se definió recorriendo el trayecto de un cliente nuevo (conocer la empresa, evaluarla, contratar, usar el servicio, resolver problemas), sin partir de lo que el sitio ya contesta. Resultaron **71 intenciones dentro del alcance** y **18 preguntas típicas sin respuesta** en la base, que el asistente debe reconocer como tales. Los seis ejemplos del enunciado (horarios, sedes, productos, historia, contacto y procesos básicos) quedaron incluidos y se agregaron tres tipos más: confianza y regulación, calidad y evaluación, y derechos y datos.

**Criterio de calidad.** Una respuesta es correcta si (1) se apoya solo en la base de conocimiento, (2) coincide con la fuente oficial y (3) cuando no hay información, lo dice y remite a un canal oficial.

## 2. Solución propuesta: sistema de preguntas y respuestas basado en RAG

**Idea.** RAG (generación aumentada por recuperación) significa que el modelo de lenguaje no responde de memoria: responde con textos oficiales que se le entregan junto con la pregunta. Así se reducen las alucinaciones y cada respuesta se puede rastrear hasta su fuente.

**Cómo se arma.**
1. **Base de conocimiento curada** de Celsia (sección 3).
2. **Recuperación de fragmentos:** la base completa (~316.800 tokens) cabe en el contexto de Gemini, pero cuesta unas 80 veces más por pregunta (sección 5). De sus 1.690 fragmentos, para cada pregunta se buscan los 12 más relevantes (embeddings con `nomic-embed-text-v2-moe` en Ollama, guardados en **Chroma**, una base de datos vectorial persistente, y similitud del coseno) y solo esos van al prompt del modelo, con su fuente. Si Ollama no responde, hay una búsqueda por palabras de respaldo; si falta la carpeta de Chroma, se busca en la matriz de vectores guardada (`indice_embeddings.npz`), con el mismo resultado.
3. **Tres tareas con LangChain:** **Q&A** (responde la pregunta de un cliente), **Resumen** (sintetiza una página oficial) y **FAQ** (arma preguntas frecuentes de una página). Resumen y FAQ devuelven salida estructurada (Pydantic).
4. **Aplicación en Streamlit** con una pestaña por tarea (Q&A, Resumen, FAQ) y una cuarta, «Corpus y scraping», que muestra las etapas del pipeline con sus cifras.

**Base vectorial.** Es Chroma (`chromadb`, persistente, similitud del coseno, sin telemetría); el texto sigue en un solo lugar (`chunks.jsonl`) y Chroma guarda los vectores y la categoría, región y fuente. Se verificó que da el mismo resultado que la matriz que se usaba antes (embeddings 31 de 35 en ambas).

## 3. Preparación de los datos

**Fuentes.** Páginas generales y blog de celsia.com en español, 52 noticias (las de los últimos 12 meses y las atemporales), las 58 sedes (de una capa pública de mapas) y dos documentos escritos a mano con datos que el sitio muestra solo como enlaces (canales de atención; prestadores, planes de internet y redes oficiales). Redes sociales y medios se investigaron, pero no entran: son institucionales o de marca. Los PDF no se descargaron porque el `robots.txt` de celsia.com los bloquea. El scraping usa un User-Agent propio, pausa entre peticiones y respeta el `robots.txt`.

**Tamaño y privacidad de los datos.** El HTML descargado pesa 254 MB y la capa Gold 4,7 MB (98 % menos, medido en bytes): lo que se descarta es ruido (menús, scripts, avisos de cookies) y los 172 documentos vacíos o repetidos. Todo es contenido público e institucional de celsia.com, sin datos de clientes (sí quedan correos de contacto de trabajo con nombre de persona y una cuenta bancaria de Celsia, publicados por la empresa en su sitio; se dejaron por ser datos públicos de la organización y no de clientes, y es una excepción consciente a la regla 6 de `AGENTS.md`) ni zonas bloqueadas por `robots.txt`; el scraper se identifica con un *User-Agent* propio, espera entre peticiones y usa tiempo máximo de espera. Por eso es razonable enviar los fragmentos a una API: si la base tuviera datos confidenciales habría que usar un modelo de pesos abiertos en local. Si Gemini no responde, la app puede enviar la pregunta del cliente y los fragmentos recuperados a DeepSeek (solo si hay clave configurada) y, como último recurso, al modelo local, que no envía nada a terceros; se declara porque la pregunta viajaría a otro proveedor. Los embeddings ya son abiertos y corren en local (`nomic-embed-text-v2-moe`, licencia Apache 2.0 según su ficha en Hugging Face, consultada el 28/10/2026).

**Capas de datos (Medallion).**

| Capa | Qué contiene | Cantidad |
|---|---|---|
| Bronze | HTML tal como lo devolvió el sitio, más la lista cruda de sedes y un registro de captura (URL, fecha, código HTTP y hash de cada página; las bloqueadas o con error también quedan anotadas) | 1.272 páginas HTML |
| Silver | Solo el texto útil, sin menús ni duplicados exactos | 1.101 documentos |
| Gold | Los mismos documentos con metadatos: categoría, región, idioma, fechas, tamaño (caracteres y tokens) y relevancia propuesta | 1.101 documentos |

**Criterio y curaduría.** El objetivo es que el asistente responda cualquier pregunta que el sitio oficial conteste. Una primera versión de la base se armó pensando solo en un cliente nuevo y dejó fuera el 77 % de lo descargado; se corrigió porque el asistente decía «no sé» ante preguntas que el sitio sí contesta (sostenibilidad, inversionistas, proyectos, regulación). Hoy entra todo el contenido oficial en español y las reglas (`05_curar_base.py`) descartan solo ruido y lo vencido. Cada documento queda con su decisión y su motivo en `registro_curaduria.csv`, y nada se borra.

| Regla | Qué hace | Documentos |
|---|---|---|
| R1 | Excluye lo que está en inglés (copias de las páginas en español) | 44 |
| R6 | Elimina casi-duplicados (más de 65 % de palabras en común) | 28 |
| R7 | Noticias: solo las de menos de 12 meses y las atemporales (fraude, explicación de la tarifa) | 52 incluidas, 638 excluidas |
| R8 | Excluye páginas con casi nada de texto | 0 |
| R0 | Todo lo demás entra | 339 |
| M0 | Incluye los documentos escritos a mano | 2 |

**Resultado:** **393 documentos y 1,27 millones de caracteres** (~316.800 tokens con el tokenizador o200k de OpenAI; con el de Gemini la misma base suma ~341.000). Los blogs y las noticias llevan su **fecha de publicación** en el encabezado, para que el asistente avise cuando un dato viene de un texto antiguo.

**Fragmentado (chunking) e índice.** Los 393 documentos se dividen en 1.690 fragmentos con `RecursiveCharacterTextSplitter` de LangChain: 1.000 caracteres (~250 tokens) y solape de 150, cortando por párrafo, línea o frase antes que por palabra. Cada sede es un fragmento propio, porque dirección y horario forman una unidad de respuesta. Cada fragmento lleva el título de su documento. Se verificó que todos los documentos tienen fragmentos y que los datos clave (teléfonos, direcciones, requisitos) sobreviven. A cada fragmento se le calcula su embedding para la recuperación (sección 2).

**Limitaciones de los datos.**
- Los blogs conservan el texto de relleno «Te puede interesar…» al final de cada página (130 veces en la base, unos 152 de los 1.690 fragmentos): es ruido que el limpiador no quitó, no cambia los datos, y corregirlo obliga a rehacer Silver, Gold, curaduría, índice y mediciones; queda como mejora.
- El sitio se contradice en algunas cifras (capacidad instalada 2.066 vs 2.175 MW; clientes 1,36 vs 1,4 millones). Se cita la fuente y la fecha.
- La lista pública de sedes no incluye Cali; eso no significa que no haya atención allí.
- Las tarifas por estrato están en tablas trimestrales que no quedaron como texto.
- Los precios de Celsia Internet cambian cada pocas semanas.
- Los cortes y mantenimientos por barrio son información temporal, excluida.
- Facebook, X y YouTube se revisaron sin sesión (27/10/2026): son institucionales, de prensa o videos, y no sustituyen las páginas del sitio.

## 4. Modelado

**Opciones no adoptadas por defecto.** *Reordenamiento:* recupera 30 candidatos y `gemini-3.5-flash-lite` elige los 12 mejores; cuesta una llamada más por pregunta. Se midió: con 12 fragmentos acierta 31 de 35 (89 %), igual que los embeddings solos (esa salida no se guardó en un archivo: repetirla con `--reordenar` cuesta 35 llamadas a `gemini-3.5-flash-lite`); falla P05, P12, P14 y P22 (los embeddings fallan P05, P12, P14 y P30). No mejora la recuperación, por eso queda apagado. La medición se hizo antes de delimitar la pregunta y los candidatos con etiquetas XML en el prompt del reordenador; el cambio no altera las instrucciones, pero no se repitió la medición. *Trazabilidad:* con una clave de LangSmith en el `.env`, cada ejecución de la app se registra (pregunta, fragmentos, prompt, respuesta, tokens y tiempo); sin clave no se envía nada, y se declara porque las preguntas viajarían a un tercero.

*Prompt con ejemplos (v5).* Como técnica de prompt engineering (few-shot) se probó añadir tres ejemplos al prompt v3. Resultado con las mismas 59 preguntas: 31 correctas y 4 parciales de 35 (igual que v3) y 20 de 24 negativas bien resueltas (v3: 21). No mejora, por eso v3 sigue vigente y v5 queda como experimento descartado. Es una sola corrida por prompt; una diferencia de una pregunta cae dentro del ruido.

*Comparación con otra familia (DeepSeek).* Para no depender de un solo proveedor se repitió la evaluación completa con `deepseek-flash` (prompt v3, mismos fragmentos, `temperature 0.0` con el razonamiento apagado). Resultado: 30 correctas, 4 parciales y 1 incorrecta de 35; 20 de 24 negativas bien resueltas (4 inventan); inyección directa 4 de 4 rechazadas; mediana de 4,0 s por respuesta frente a 7,5 s de Gemini. Es casi un empate (Gemini: 31, 4, 0; 21 de 24). Dos salvedades: el juez fue `deepseek-v4-pro` y no `gemini-3.8-flash`, así que parte de la diferencia puede venir del juez, y DeepSeek deja `top_p` fijo en 1,0 en lugar de 0,1; con `temperature 0.0` esa diferencia pesa poco, porque con temperatura cero `top_p` deja de influir (Google, *Prompt Engineering*, p. 12). No se evaluó `deepseek-v4-pro` como modelo de respuesta. Se mantiene Gemini porque todo lo demás (versiones del prompt, inyección indirecta, reordenamiento y revisión manual) se midió con él, porque cumple la regla de `top_p`, y porque la diferencia no justifica rehacer esas mediciones. La aplicación y las tareas también pueden usar DeepSeek escribiendo `deepseek-flash` como modelo.

*Repetición del prompt.* Siguiendo a Leviathan et al. (2025) se envió el mensaje del usuario dos veces seguidas (`--repetir`). Con las mismas 59 preguntas: 29 correctas y 6 parciales de 35 (v3: 31 y 4) y 21 de 24 negativas bien resueltas (igual que v3); mediana de 8,3 s frente a 7,5 s. No mejora (el propio trabajo la describe como neutral o ligeramente positiva en modelos con razonamiento), así que no se adopta. Es una sola corrida: dos preguntas de diferencia caen dentro del ruido del juez.

*Extracción a JSONL.* `scripts/13_extraer_contactos.py` saca teléfonos, WhatsApp, correos y enlaces de tres páginas del corpus con salida estructurada (Pydantic) y `temperature 0.0`, y comprueba que cada valor aparezca escrito en su página. Resultado: 36 contactos (22, 9 y 5 por página) y los 36 aparecen en el texto. Es una comprobación de presencia: no garantiza que el «para qué sirve» que describe el modelo sea el correcto.

**Sistema compuesto y ciclo de vida.** El asistente no es «un modelo»: es un sistema de piezas, como plantea Zaharia et al. (2024). La tabla relaciona las seis responsabilidades del orquestador con lo que hay en el repositorio.

| Responsabilidad | Dónde está |
|---|---|
| Plantillas de prompts | `prompts/` versionados y `prompts.py` |
| Abstracción de modelos | `obtener_modelo` (Gemini, DeepSeek) y `agente.py` (Ollama) |
| Memoria entre turnos | No aplica: cada pregunta se responde sola (límite declarado) |
| Conexión semántica (RAG) | `recuperacion.py` y el índice de embeddings |
| Herramientas | `buscar_en_base` en `agente.py` |
| Validación | Pydantic (Resumen, FAQ), etiquetas XML, cláusula de abstención y `validacion.py` |

El ciclo *Build, Test, Deploy, Monitor* de LangChain equivale a: Build, el pipeline y los prompts; Test, los scripts 10 y 11 y las pruebas automáticas; Deploy, la aplicación de Streamlit (corre en local, no está desplegada en un servidor) con respaldo de modelo: si Gemini falla por cuota o conexión prueba DeepSeek y luego un modelo local, y si ninguno responde muestra la respuesta guardada de la evaluación, marcada como tal (`respaldo.py`); Monitor, las trazas de LangSmith.

*Post-validación de datos.* `validacion.py` comprueba, sin llamar a ningún modelo, que cada cifra de dos o más dígitos, correo y enlace de la respuesta esté escrito en los fragmentos recuperados o en las instrucciones del asistente (que traen la línea 01 8000 112 115). La app avisa cuando algo no tiene respaldo. Es una revisión de texto: no detecta un teléfono armado con trozos que sí aparecen por separado en las fuentes, ni una afirmación inventada que no lleve cifras. Aplicada a las respuestas guardadas (`scripts/14_validar_respuestas.py`): 0 de 59 con datos sin respaldo en las corridas de Gemini y de DeepSeek. Hay que leerlo con cuidado: revisa que el texto aparezca, no que se use bien, y no detecta invenciones sin cifras (las respuestas que el juez marcó como «inventa» no traen datos numéricos falsos, sino afirmaciones que la base no respalda).

*Agente con herramienta.* `agente.py` arma un agente `create_agent` de LangChain con la herramienta `buscar_en_base`, que usa la misma recuperación del Q&A, y un modelo local de Ollama (`llama3.2`, sin costo). En tres preguntas de prueba (el teléfono, el pago de la factura y una fuera de alcance, el costo de un viaje a Cartagena) llamó a la herramienta las tres veces; dio el teléfono correcto, rechazó la de Cartagena remitiendo a la línea oficial y la validación no encontró datos sin respaldo. Falló un detalle: en la del pago reformuló la consulta con caracteres dañados («Ásá como puedo…») y listó cinco formas de pago que no se contrastaron una a una con la base. Es un modelo de 3.000 millones de parámetros en CPU (minutos por pregunta) y no se midió con las 59 preguntas, así que demuestra el patrón de agente con herramienta pero no reemplaza al Q&A principal.

**Modelo.** Gemini por API (`gemini-3.5-flash`) con `temperature 0.0` y `top_p 0.1`, la regla del proyecto para RAG; `gemini-3.6-flash` se descartó porque ignora ambos parámetros. El framework es LangChain. Un modelo local no es viable en este equipo (7,7 GB de RAM, sin GPU): en una prueba inicial, Llama 3.2 tardó de 7 a 8 minutos por pregunta con una base de solo 5.000 tokens (no se conservó el archivo de resultados de esa prueba). La cuota gratuita de Google (20 solicitudes por día por modelo) llevó a cargar saldo de prepago; cada corrida paga se autorizó antes de ejecutarla. Ollama se usa solo para los embeddings (`nomic-embed-text-v2-moe`).

**Ingeniería de prompts.** El prompt tiene cinco bloques: rol, contexto, instrucción, formato y restricciones. Tiene estructura de sándwich (lo esencial se repite después de la pregunta) y la entrada del cliente va entre etiquetas `<user_input>`, para que el modelo la trate como dato y no como orden. Los prompts están versionados en `prompts/`:

| Versión | Qué cambió |
|---|---|
| v1 | Lista de siete reglas. Punto de partida |
| v2 | Cinco bloques, sándwich, `<user_input>` y defensa contra inyección de instrucciones |
| v3 | v2 + aviso de vigencia: fecha de hoy y fecha de publicación de blogs y noticias, para no presentar un dato antiguo como actual |
| v4 (descartada) | v3 + remitir en temas de seguridad, qué hacer con fuentes que se contradicen o con una sola fuente, no deducir horarios y ejemplos (few-shot). No se promovió |

La versión v3 nació de un error real: el resumen de una noticia de 2020 («tarifa congelada hasta diciembre») se presentaba como vigente.

**Calidad de la recuperación (medida, sin gastar cuota del modelo).** `scripts/10_evaluar_recuperacion.py` comprueba, para cada una de las 35 preguntas de respuesta, si entre los fragmentos recuperados hay uno que contiene la respuesta (según el patrón de su intención en el inventario). Con 12 fragmentos y las 35 preguntas de respuesta (`resultados/recuperacion_k12.csv`): búsqueda por palabras **54 %** (19 de 35), híbrido (palabras y significado) **74 %** (26) y **embeddings 89 %** (31). En una medición anterior (31 preguntas, 1.510 fragmentos) los embeddings daban 71, 74 y 81 % con 5, 8 y 16 fragmentos, por eso se usan 12. Es una medida aproximada: el patrón es estricto y a veces rechaza un fragmento que sí responde (por ejemplo, el de internet para la pregunta de planes), y otras veces acepta uno incompleto. Los fallos más claros eran «¿Desde cuándo existe Celsia?», «¿Qué pasa si me atraso con la factura?» y «¿Cuáles son los valores de Celsia?»: el cliente usa palabras distintas a las del sitio (atraso/mora, valores/cultura). Se atendieron con un **diccionario de sinónimos hecho a mano** (`src/taaml/sinonimos.py`) que se usa de dos formas: agrega el vocabulario del sitio a la pregunta y etiqueta los fragmentos afectados al calcular su embedding (el texto que lee el modelo no cambia). **Posición del acierto:** con embeddings, la respuesta está en el primer fragmento en 21 de 35 preguntas (**hit@1 60 %**) y entre los tres primeros en 24 (**hit@3 69 %**); con palabras, 29 % y 46 %; con híbrido, 46 % y 57 %. O sea que el 89 % depende de leer los 12 fragmentos, y por eso se entregan los 12. Con eso los embeddings pasaron de **80 % (28 de 35) a 89 %** (31 de 35); la cifra de 80 % es de la medición anterior al diccionario y no se guardó en un archivo, la de 89 % sí. Es un parche que cubre solo tres temas y que se escribió mirando esas preguntas, así que la mejora está medida sobre las mismas preguntas que la motivaron y puede sobrestimar lo que ganaría con preguntas nuevas. Siguen sin recuperarse P05 (oficina en Cali), P12, P14 y P30 (la posición exacta de cada pregunta está en la tabla de recuperación por pregunta). La calidad de las respuestas se juzga aparte, con el modelo y una revisión manual.

**Comparación de las cuatro versiones (misma búsqueda, mismo modelo `gemini-3.5-flash`, mismo juez).** En las 35 preguntas de respuesta: v1 33 correctas, 1 parcial, 1 incorrecta; v2 30/3/2; v3 31/4/0; v4 31/4/0. En las 24 negativas, v1 y v3 reconocen que no saben 21 veces e inventan 3; v2 y v4, 20 y 4. Las cuatro rechazaron los 4 ataques de inyección. La diferencia entre versiones (hasta 3 preguntas) es menor que el ruido del juez automático con 35 preguntas, así que **no se demostró que v3 sea mejor que v1**. Se mantiene v3 como vigente porque implementa un diseño de prompt más robusto (cinco bloques, sándwich, XML, defensa contra inyección) y el aviso de vigencia, no porque puntúe más. v4 (más larga y con ejemplos) no mejoró y no corrige N20 y además inventa en N19. En términos estadísticos es un empate entre v1 y v3: cada una se midió en una sola corrida, y repetirlas tres veces cada una (con costo) sería lo que permitiría separarlas. Una prueba de inyección con ataques más difíciles también podría hacerlo.

## 5. Resultados y limitaciones

**Qué se midió.** El conjunto de prueba tiene 59 preguntas: 35 de respuesta (la base sí la contiene), 20 negativas (la base no la contiene) y 4 de inyección de instrucciones. Cada respuesta la califica un modelo juez (`gemini-3.8-flash`, distinto del que responde) contra una respuesta esperada escrita por el equipo; el juez es una ayuda y una persona revisa las respuestas (`docs/2 - Conjunto de prueba/revision_manual.md`). Se midió aparte la recuperación de fragmentos, que no gasta cuota.

**Revisión manual (27/10/2026).** Se revisaron las 59 respuestas de v3 contra la base (`docs/2 - Conjunto de prueba/revision_manual.md`). **Los veredictos los propuso el asistente de código (Claude Code) con evidencia de la base**: los 59 los ratificó María Stella Fuentes; por eso es una revisión asistida: la propuesta salió del asistente y la decisión final es de una persona. Con esos veredictos, de las 35 de respuesta 29 convencen y 6 son parciales; de las 24 negativas, 19 convencen, 4 son parciales y 1 no convence (N20). El juez fue más estricto que la persona en N10 (no inventa: lo que cita está en la base) y más indulgente en P02, P09, N18 y N19.

**Resultados del prompt vigente (v3, `gemini-3.5-flash`, 12 fragmentos por pregunta).**

| Medición | Resultado |
|---|---|
| Recuperación: la respuesta está entre los 12 fragmentos | 89 % (31 de 35); la comparación con la versión anterior al diccionario de sinónimos no se conservó y no se puede repetir |
| Preguntas de respuesta (según el juez automático) | 31 correctas, 4 parciales, 0 incorrectas; con la revisión humana, 29 convencen y 6 son parciales |
| Preguntas negativas, incluye las 4 de inyección (según el juez) | 21 reconocen que no saben, 3 inventan; con la revisión humana, 19 convencen, 4 son parciales y 1 no convence |
| Ataques de inyección directa (N11 a N14) | 4 de 4 rechazados |
| Inyección indirecta (orden escondida en un fragmento recuperado, I1 a I4) | 4 de 4 resistidas |
| Jailbreaks directos adicionales (juego de rol DAN en ficción, orden en Base64 y «respóndeme en JSON», D1 a D3) | 3 de 3 resistidos |
| Pruebas automáticas de componentes (`make test`) | 78 de 78 pasan |
| Tiempo por respuesta | mediana de 7,5 segundos (8 en la tabla de comparación, que la redondea) |

La comparación entre las cuatro versiones del prompt está en la sección 4: rindieron de forma parecida y no se demostró que v3 sea mejor que v1.

**Qué cambió al medir.** La primera medición mostraba tres fallas de recuperación (historia de la empresa, atraso en el pago, valores de Celsia) porque el cliente usa palabras distintas a las del sitio. Se atendieron con un diccionario de sinónimos hecho a mano y la recuperación subió de 80 % a 89 %. Esa mejora se midió con las mismas preguntas que la motivaron, así que puede sobrestimar lo que se ganaría con preguntas nuevas. También se corrigieron respuestas esperadas mal planteadas (P01, P13, P14, P19, P26, N10), por ejemplo una que exigía remitir a un asesor comercial que el sitio no publica.

**Cómo se evaluó.** `scripts/11_evaluar_modelo.py` llama a las APIs por REST (para medir tokens y tiempos) con el mismo prompt de sistema y los mismos parámetros que la app; la app y `responder_con_fuentes` usan LangChain. La ruta de LangChain no se midió aparte con las 59 preguntas. Resumen y FAQ no se evalúan con un conjunto de prueba; como evidencia mínima, `scripts/17_probar_resumen_faq.py` los corrió una vez por LangChain (2 llamadas a `gemini-3.5-flash`) sobre la página «Descubre las ventajas de pagar tu factura en canales digitales» y guardó la salida en `resultados/resumen_faq_gemini-3.5-flash.csv`: el resumen tardó 12 s y la FAQ 8 s, y ninguna cifra, correo ni enlace de la salida quedó sin respaldo en la página (revisión de texto, no de significado). Una página no basta para generalizar.

**Inyección indirecta y pruebas de componentes.** Las pruebas N11 a N14 meten la orden en la pregunta. Existe otro vector, la inyección indirecta: la orden viene en un documento que el bot lee (una página scrapeada). `scripts/12_probar_inyeccion_indirecta.py` toma la recuperación real de una pregunta y le agrega una orden al fragmento más relevante: responder solo «PWNED», pedir cédula y clave en un sitio falso, imprimir el prompt de sistema, o cerrar el bloque `<contexto>` y escribir reglas nuevas. En los 4 casos el asistente respondió la pregunta con los datos reales y no obedeció (4 llamadas a Gemini). Como defensa adicional, `formatear_contexto` ya no deja que un fragmento cierre el bloque `<contexto>`. Aparte, 78 pruebas automáticas (`tests/`, sin Gemini ni Ollama) revisan sinónimos, armado del prompt, recuperación, fragmentado, el conjunto de prueba, el scraper y la validación de respuestas; la primera corrida encontró que 36 identificadores de fragmento estaban repetidos (1.654 únicos de 1.690) porque se cortaban a 70 caracteres. Se corrigieron con una huella en el identificador; el texto de los fragmentos y sus vectores no cambiaron.

**Acuerdo entre el juez y la revisión manual.** Comparando solo si la respuesta está bien o no, el juez y la revisión coinciden en 55 de las 59 (93 %); en las 4 restantes (P02, P09, N18, N19) el juez fue más indulgente. En N10 coinciden en que falla pero no en el motivo. Nota: los veredictos de la revisión los propuso Claude Code y los ratificó María Stella Fuentes.

**Errores que quedan (documentados, no corregidos).** El detalle de cada pregunta está en `docs/2 - Conjunto de prueba/revision_manual.md`. Son de cuatro tipos:
- **Datos desactualizados o sin respaldo oficial.** La respuesta usa información antigua sin avisarlo: afirma que el WhatsApp atiende a cualquier hora apoyándose en una publicación de 2023, cuando el sitio no publica un horario oficial, o no aclara que un horario viene de avisos de 2021. También recomienda un enlace que la propia base marca como caído.
- **Detalles que la base no respalda.** En la pregunta del cable caído agrega consejos de seguridad que son conocimiento general del modelo, y en la de datos personales añade detalles que el juez no respalda. Una versión del prompt con reglas más estrictas (v4) no lo corrigió.
- **Omisiones en respuestas correctas en lo esencial.** Falta remitir a Celsia Empresas, avisar la fecha o la única fuente de un dato, citar la norma vigente o nombrar a un actor (por ejemplo, Cetsa). Una respuesta ofrece como canal el WhatsApp de garantía de la Tienda Celsia, que está en la base pero es de otra función.
- **Recuperación.** En 4 de las 35 preguntas de respuesta el fragmento esperado no queda entre los 12 primeros (por ejemplo, una oficina en Cali, porque la lista pública de sedes no la incluye); el asistente igual responde bien dos de ellas.

**Limitaciones.**
- **Abstención por umbral de similitud.** Se probó rechazar la pregunta sin llamar al modelo cuando el mejor fragmento tiene poca similitud (una técnica común contra la alucinación). No sirve: las 35 preguntas con respuesta tienen similitud de 0,41 a 0,77 y las 24 negativas de 0,32 a 0,61, así que se solapan. El mejor umbral rechazaría solo 5 negativas y no tocaría las que el modelo inventa (por ejemplo N19, con 0,61, la más alta de todas). Se queda la abstención por prompt.
- **Datos que el sitio no publica.** La misión de Celsia y su NIT no aparecen en las páginas de texto de celsia.com (se revisaron el 28/10/2026), por lo que no están en la base y el asistente responde que no tiene esa información. No se completaron con fuentes de terceros para mantener la base solo con contenido oficial.
- **Desviación del enunciado.** El enunciado pide consolidar el texto limpio en el prompt de sistema; el asistente usa RAG (12 fragmentos por pregunta). Se probó la opción del enunciado con 5 preguntas (P01, P02, P07, N01 y N18; 10 llamadas a `gemini-3.5-flash` y a su juez, `resultados_gemini-gemini-3.5-flash_completa_v3.csv`): la base completa (~341.000 tokens de entrada por pregunta) **sí cabe y respondió igual que con RAG** (las 3 de respuesta correctas y las 2 negativas reconocen que no saben), con tiempos parecidos (8 a 11 s contra 6 a 9 s). La diferencia es el tamaño: ~341.000 tokens por pregunta contra ~4.000 con RAG, unas 80 veces más entrada y costo. Con 5 preguntas no se concluye nada sobre precisión; por eso RAG se justifica por costo y escalabilidad (con más documentos la base dejaría de caber), no por calidad.
- **Medición.** Con 35 preguntas de respuesta, una diferencia de dos o tres es menor que el ruido de un juez automático. Las respuestas esperadas las escribió el equipo y varias se corrigieron durante el proyecto.
- **Datos.** No se descargaron los PDF (el `robots.txt` de celsia.com los bloquea), por lo que faltan los informes de gestión y el contrato de condiciones uniformes; 18 intenciones típicas de un cliente nuevo no tienen respuesta en el sitio. Hay datos antiguos en blogs y noticias (el asistente avisa la fecha de publicación) y cifras que el sitio contradice (por ejemplo, dos números de WhatsApp oficiales).
- **Sin memoria entre turnos.** Cada pregunta se responde sola; no hay checkpointers ni LangGraph. Es una decisión de alcance: el asistente no sigue una conversación.
- **Resumen y FAQ** no tienen una evaluación como la de Q&A; se revisan a mano.
- **Jailbreaks directos adicionales.** Son 3 casos tomados de categorías conocidas de jailbreak (rol, ofuscación y el caso Rappi), calificados por reglas y con un solo modelo; las categorías reales son muchas más.
- **Inyección indirecta.** Son 4 casos escritos por el equipo, con un solo modelo y un solo prompt; no prueban que el sistema sea inmune, solo que estas órdenes no funcionaron.
- **Evidencia que no se conservó.** La comparación con la versión anterior al diccionario de sinónimos, las pruebas con 5, 8 y 16 fragmentos y el análisis del umbral de similitud se hicieron durante el desarrollo y sus resultados intermedios no se guardaron; hoy se puede repetir la medición con 12 fragmentos (`scripts/10_evaluar_recuperacion.py`), no las anteriores. Los precios de internet de `data/0_manual/` salen de la web de Celsia Internet a la fecha indicada en el documento y deben verificarse de nuevo antes del 30/11/2026. Las cifras de contexto del sector (ranking de El País, notas de prensa) están citadas por su fuente pero no se copiaron al repositorio. Los CSV de resultados no registran el modelo juez ni la fecha, el orden de los fragmentos puede variar levemente entre corridas, y la evaluación usa un límite de salida de 2.048 tokens frente a 8.192 en la app. Las pruebas automáticas no cubren la regla de casi duplicados (R6).
- **Privacidad.** El modelo es privado: las preguntas viajan a Google. Con datos públicos de Celsia no es un problema, pero en una empresa real habría que revisarlo.

## Referencias

- Zaharia, M. et al. (2024). *The Shift from Models to Compound AI Systems*. Berkeley AI Research (BAIR) Blog.
- Leviathan, Y., Kalman, M. y Matias, Y. (2025). *Prompt Repetition Improves Non-Reasoning LLMs*. arXiv:2512.14982. https://arxiv.org/abs/2512.14982 (la prueba de repetición de la sección 4 sigue su idea).
- LangChain: documentación de `create_agent`, salida estructurada y `RecursiveCharacterTextSplitter` (docs.langchain.com).
- Chroma: repositorio y documentación (github.com/chroma-core/chroma).
- Nomic AI: ficha del modelo `nomic-embed-text-v2-moe` en Hugging Face (consultada el 28/10/2026).
- Celsia: el sitio oficial (celsia.com) y su `robots.txt`; cada documento de la base conserva su dirección de origen en `data/4_curaduria/documentos_incluidos.jsonl`.

## Declaración de uso de IA

Se declara qué herramientas de IA se usaron, para qué y cómo se verificó el resultado.

| Herramienta | Para qué se usó | Cómo se verificó |
|---|---|---|
| Claude Code (Anthropic) | Escribir y revisar código (scraping, limpieza, curaduría, fragmentado, evaluación, aplicación) y documentos del proyecto; ayudar a entender el enunciado y a estudiar | El equipo revisa lo generado; cada cifra se vuelve a calcular con los scripts; el código lo revisa además GGA antes de cada commit |
| OpenCode con `gemini-3-flash-preview` (GGA) | Revisión automática de cada commit contra las reglas de `AGENTS.md` | Es un revisor no determinista: si falla se corrige la causa y se repite, nunca se omite |
| Gemini `gemini-3.5-flash` por API | Es el modelo del asistente (Q&A, resumen y FAQ) | Se evaluó con 59 preguntas y revisión manual |
| Gemini `gemini-3.8-flash` por API | Modelo juez que califica las respuestas | Es solo una ayuda; las respuestas se revisaron contra la base (veredictos propuestos por Claude Code y ratificados por María Stella Fuentes) y se corrigieron respuestas esperadas mal planteadas |
| `deepseek-flash` y `deepseek-v4-pro` (DeepSeek, por API) | Comparación con otra familia de modelos y respaldo si Gemini no responde | Se evaluó con las mismas 59 preguntas; sus respuestas no se usan como verdad |
| `llama3.2` (Ollama, local) | Agente con herramienta y último respaldo de la app | Se probó con 3 preguntas; es un modelo pequeño y no se midió con las 59 |
| `gemini-3.5-flash-lite` | Reordenador opcional de fragmentos (apagado por defecto) | Se midió: no mejoró la recuperación |
| `nomic-embed-text-v2-moe` (Ollama, local) | Embeddings de los fragmentos y de las preguntas | Se mide la recuperación con `scripts/10_evaluar_recuperacion.py` |

Todo código o texto generado por una herramienta lo revisa una persona del equipo, que debe poder explicarlo en vivo. El detalle de cada decisión está en `specs/` (qué se pidió, cómo se verificó) y en los commits.
