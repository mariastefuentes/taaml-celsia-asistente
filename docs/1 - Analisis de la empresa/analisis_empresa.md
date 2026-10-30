# Análisis de la empresa y estrategia de datos: Celsia

Taller 1, punto 1 (Asignación y análisis inicial). **Versión para entrega.**
Última actualización: 27/10/2026. Las cifras provienen del sitio oficial (celsia.com) y se re-verificaron el 28/10/2026 contra los archivos de datos.

**Empresa asignada al grupo: Celsia** (confirmado).

Documentos relacionados: [inventario de fuentes](inventario_fuentes_celsia.md) (de dónde sale la información) e [inventario de intenciones](inventario_intenciones.md) (qué debe saber responder el asistente).

## 1. Perfil de la empresa

**Celsia** es la empresa de energía del Grupo Argos. Genera, transmite, distribuye y comercializa energía eléctrica, con foco en fuentes renovables (agua, sol y viento) y respaldo térmico. Su sede corporativa está en Medellín. Segmentos de cliente: hogares, pymes, empresas y desarrollos inmobiliarios. También ofrece servicio de internet (Celsia Internet).

| Aspecto | Dato | Fuente |
|---|---|---|
| Qué hace | Cadena completa: generación, transmisión, distribución y comercialización | celsia.com/es/quienes-somos/que-hacemos/ |
| Dónde opera | Colombia (Valle del Cauca vía EPSA y Tolima vía Cetsa), Panamá, Costa Rica, Honduras; también Perú | Sitio y Reporte Integrado 2024 |
| Clientes | ~1,36 millones según «Negocios en cifras»; 1,4 millones según «Qué hacemos» | celsia.com/es/quienes-somos/ |
| Generación | La hídrica es la principal fuente (68 % de la matriz); capacidad instalada de ~2.066 MW según una página y 2.175 MW según otra | Sitio |
| Redes | 16 subestaciones de transmisión y 449 km; 189 subestaciones de distribución y más de 46.000 km de redes en Valle y Tolima | Sitio |
| Hitos | Escisión de Colinversiones de Coltabaco (2001); adquisición de EPSA (2009); cambio de nombre a Celsia (2012); Celsia Solar Yumbo (2017) | celsia.com/es/quienes-somos/la-nueva-era-de-la-energia/ |

**Datos que el propio sitio contradice** (en el informe hay que citar la fuente y la fecha de cada cifra): capacidad instalada (2.066 vs 2.175 MW), número de clientes (1,36 vs 1,4 millones) y la compra de EPSA (50 % en 2009 según Celsia; «mayoría» según Valora Analitik).

## 2. Problema que se aborda

Los clientes de Celsia deben acudir a varios canales (un sitio con cientos de páginas, línea telefónica, WhatsApp, oficinas) para resolver dudas básicas: cómo reportar un daño, pagar la factura, hacer una PQR o conocer los servicios. Eso genera tiempos de espera y carga sobre la atención humana.

**Necesidad:** un canal automatizado, siempre disponible y **preciso**, que responda solo con información oficial y reconozca cuando no sabe.

## 3. Estrategia de datos

### 3.1 Fuentes
El detalle de cada fuente (sitio, PDF, redes, medios, entidades) y por qué entra o no está en el [inventario de fuentes](inventario_fuentes_celsia.md). Lo que entró al proyecto: páginas generales y blog del sitio en español, **52 noticias: las de menos de 12 meses y las atemporales (fraude, tarifa)**, las 58 sedes (de una capa pública de mapas) y dos documentos escritos a mano con datos que el sitio muestra solo como enlaces o en otro sitio (canales de atención; quién presta el servicio, planes de internet y redes oficiales). Las redes sociales y los medios se investigaron y documentaron, pero no entran al corpus (son institucionales, financieros o de comunicación de marca).

### 3.2 Capas de datos (patrón Medallion del docente)

| Capa | Qué contiene | Cantidad |
|---|---|---|
| **Bronze** (crudo) | HTML tal como lo devolvió el sitio, y la lista cruda de sedes | 1.272 páginas HTML (páginas, blog y 823 noticias) |
| **Silver** (limpio) | Solo el texto útil, sin menús ni duplicados exactos | 1.101 documentos (148 páginas con menos de 200 caracteres y 24 duplicados exactos quedaron fuera; se sumó el archivo de sedes) |
| **Gold** (enriquecido) | Los mismos documentos con metadatos: categoría, región, idioma, fechas y relevancia propuesta | 1.101 documentos |

### 3.3 Curaduría
**Criterio (cambió el 27/10/2026).** Al principio la base se armó pensando solo en un cliente nuevo y dejó fuera el 77 % de lo descargado (inversionistas, sostenibilidad, proyectos, regulación, gran parte del blog). Eso hacía que el asistente dijera «no sé» ante preguntas que el sitio sí contesta. El objetivo es que responda **cualquier pregunta que el sitio oficial conteste**, así que ahora entra todo el contenido oficial en español y se descarta solo el ruido y lo vencido. Las reglas son explícitas y ordenadas (`scripts/05_curar_base.py`); cada documento queda con su decisión y su motivo en `data/4_curaduria/registro_curaduria.csv`.

| Regla | Qué hace | Documentos |
|---|---|---|
| R1 | Excluye lo que está en inglés (son copias de las páginas en español) | 44 |
| R6 | Elimina casi-duplicados (más de 65 % de palabras en común), conservando la versión en español | 28 |
| R7 | Noticias: entran las de menos de 12 meses y las atemporales (fraude, explicación de la tarifa); el resto está vencido | 52 incluidas, 638 excluidas |
| R8 | Excluye páginas con casi nada de texto (menos de 150 caracteres) | 0 |
| R0 | Todo lo demás entra | 339 |
| M0 | Incluye los documentos escritos a mano en `data/0_manual/` (canales de atención; prestadores, planes de internet y redes oficiales) | 2 |

**Resultado:** **393 documentos y 1,27 millones de caracteres** (unos 316.800 tokens con el tokenizador o200k de OpenAI) en `data/4_curaduria/base_conocimiento.txt`. Los blogs y las noticias llevan su **fecha de publicación** en el encabezado para que el asistente avise cuando un dato es antiguo.

**Fragmentado (chunking):** los 393 documentos se dividen en **1.690 fragmentos** (`scripts/06_construir_chunks.py`, resultado en `data/4_curaduria/chunks.jsonl`). Se usó `RecursiveCharacterTextSplitter` de LangChain con fragmentos de 1.000 caracteres (unos 250 tokens) y un solape de 150, que corta por párrafo, línea o frase antes de partir una palabra. Cada sede es un fragmento propio (58) porque su dirección y horario forman una unidad de respuesta, y cada fragmento lleva al inicio el título de su documento (y la fecha, en blog y noticias) para que se entienda solo cuando se recupere. Se verificó que todos los documentos tienen fragmentos y que los datos clave (teléfonos, direcciones, requisitos) sobreviven.

**Recuperación de fragmentos (RAG).** La base completa cabe en el contexto de Gemini, pero pegarla en cada pregunta cuesta unas 80 veces más entrada (en una prueba de 5 preguntas respondió igual que RAG; ver el informe, sección 5) y consume la cuota de la API. Cada fragmento tiene un **embedding** (vector con su significado) calculado con `nomic-embed-text-v2-moe` en Ollama (`scripts/07_construir_indice.py`, guarda `data/4_curaduria/indice_embeddings.npz`). Para cada pregunta se buscan los 12 fragmentos más parecidos (`src/taaml/recuperacion.py`) y solo esos van al prompt, junto con su fuente. Los vectores viven en una base vectorial (Chroma). Si Ollama no responde, se usa una búsqueda por palabras de respaldo.

**Calidad de la recuperación (medida, sin gastar cuota del modelo).** `scripts/10_evaluar_recuperacion.py` comprueba, para cada una de las 35 preguntas de respuesta, si entre los fragmentos recuperados hay uno que contiene la respuesta (según el patrón de su intención en el inventario). Con 12 fragmentos y las 35 preguntas de respuesta: búsqueda por palabras **54 %**, híbrido (palabras y significado) **74 %** y **embeddings 89 %** (31 de 35), con el diccionario de sinónimos (`src/taaml/sinonimos.py`); sin él los embeddings daban 80 % (medición anterior, no guardada). Las cifras actuales están en `resultados/recuperacion_k12.csv`. Esa mejora se midió con las mismas preguntas que la motivaron y puede sobrestimar lo que ganaría con preguntas nuevas; siguen sin recuperarse P05, P12, P14 y P30. En una medición anterior (31 preguntas, 1.510 fragmentos) los embeddings daban 71, 74 y 81 % con 5, 8 y 16 fragmentos, por eso se usan 12. Es una medida aproximada: el patrón es estricto y a veces rechaza un fragmento que sí responde (por ejemplo, el de internet para la pregunta de planes), y otras veces acepta uno incompleto. Los fallos reales más claros son «¿Desde cuándo existe Celsia?» (no recupera el fragmento de historia), «¿Qué pasa si me atraso con la factura?» y «¿Cuáles son los valores de Celsia?», porque el sitio no los publica como lista. La calidad de las respuestas se juzga aparte, con el modelo y una revisión manual.

### 3.4 Brechas y limitaciones conocidas
- **PDF de informes** (reporte integrado, ASG, TCFD): el `robots.txt` de celsia.com los bloquea; no se descargan automáticamente. Se citan como contexto (decisión del 27/10/2026).
- **Preguntas que la base no responde:** son 10 y se explican en 4.3.
- **Lista pública de sedes:** tiene 33 ciudades y **no incluye Cali**. No significa que no haya atención allí; la fuente simplemente no la lista.
- **Celsia Internet** tiene sitio propio (`www.celsiainternet.com`) con planes y precios; el enlace `internet.celsia.com` que aparece en el sitio de energía ya no funciona. Los datos clave se resumieron en `data/0_manual/`. Los precios cambian cada pocas semanas.
- **Fechas de cortes y mantenimientos por barrio:** están en la sección excluida de mantenimientos (1.326 páginas, información temporal).
- **Tarifas por estrato:** el sitio las publica en tablas por trimestre que no quedaron como texto en el corpus.
- **Noticias recientes sin tema de cliente:** solo se descargaron 70 de las 823 noticias en español (las de tema de cliente); las demás noticias de los últimos 12 meses, de otros temas, no están. Para incluirlas hay que descargarlas todas para conocer su fecha.
- **Redes sociales:** LinkedIn, Instagram, Facebook, X y YouTube se revisaron sin sesión (27/10/2026): son institucionales, de prensa o de marca, y los videos no están en texto. No se scrapean.
- **Chat «Luz I.A.»** y los enlaces de PQR y pagos son funciones del sitio, no texto; por eso se escribieron a mano en `data/0_manual/`.
- 5 páginas dieron error del servidor (3 errores 500 y 2 errores 404).

## 4. Alcance del asistente

### 4.1 Cómo se definió: desde el recorrido del cliente nuevo, no desde los ejemplos
El enunciado pide definir «qué tipo de preguntas debería poder responder un cliente al interactuar **por primera vez** con la empresa», y da seis **ejemplos**: horarios, sedes, tipos de productos, historia de la empresa, información de contacto y procesos básicos. Son ejemplos («ej.»), no una lista cerrada, así que el alcance no se limita a ellos.

1. **Se recorrió todo el trayecto de un cliente nuevo**: conocer la empresa y confiar en ella, evaluarla (precio, cobertura, calidad), contratar, usar el servicio (pagar, reportar), resolver problemas (PQR, daños) y relacionarse con ella (empleo, comunidad, datos personales). Para cada etapa y para cada tipo de cliente (hogar, pyme, empresa) se preguntó qué querría saber, **sin mirar antes si el sitio lo responde**.
2. **Cada pregunta se contrastó** con la base de conocimiento y con la web (celsia.com, celsiainternet.com, prensa, regulación) para saber si hay respuesta y dónde.
3. Las que tienen respuesta son **intenciones dentro del alcance** (71). Las que no, quedaron aparte como **«Sin respuesta en la base»** (18), con el motivo. El 27/10/2026 el alcance se amplió de «cliente nuevo» a «cualquier pregunta que el sitio oficial conteste»: se sumaron intenciones de sostenibilidad y proyectos, inversionistas y gobierno corporativo y regulación.
4. En «procesos básicos» se añadieron los trámites que Celsia atiende a diario (los accesos directos de su portada y su blog de trámites).

**Cómo fue cambiando el método.** La primera versión (50 intenciones) se armó desde lo que el sitio publica y tenía un sesgo: no veía lo que un cliente pregunta y el sitio no contesta. La segunda partió de los seis ejemplos del enunciado, pero tratarlos como lista cerrada era otro sesgo. Al recorrer el trayecto completo aparecieron **tres tipos de pregunta que los ejemplos ocultaban**: confianza y regulación (quién vigila a Celsia), calidad y evaluación (qué tan confiable es el servicio en mi zona) y derechos y datos (protección de datos, accesibilidad).

**Límite que sigue vigente.** Todo esto es trabajo de escritorio: sale del sitio, de la prensa y de lo que razonablemente preguntaría un cliente. Lo que más mejoraría el alcance son preguntas reales (registros del WhatsApp o de la línea, motivos de PQR) y la experiencia del equipo. Conviene validarlo con él.

### 4.2 Tipos de pregunta, intenciones y cobertura
El detalle completo (cada intención, sus ejemplos, su fuente y cuántos documentos la responden) está en el [inventario de intenciones](inventario_intenciones.md), que se genera desde el CSV; aquí solo el resumen.

- **72 intenciones en alcance** (y 17 preguntas típicas sin respuesta en la base), de 12 tipos de pregunta: los seis ejemplos del enunciado (horarios, sedes, productos y servicios, historia y empresa, contacto, procesos básicos), tres que aparecieron al recorrer todo el trayecto del cliente (confianza y regulación, calidad y evaluación, derechos y datos) y tres que aparecieron al ampliar la base (sostenibilidad y proyectos, inversionistas y gobierno corporativo, regulación y autogeneración).
- **Momento del cliente:** 32 de primer contacto, 19 de «ambos» y 17 de cliente actual. Las de cliente actual se mantienen porque «procesos básicos» las incluye y porque Celsia las destaca en su portada (reportar un daño, pagar la factura, PQR), pero no deben dominar el conjunto de prueba.
- **Cobertura verificada:** las 71 tienen respaldo en la base; 15 dependen de un solo documento y son las más frágiles.
- **Verificación de la verificación.** Al ampliar la base, la regla de cobertura de dos preguntas dio falsos positivos (el precio de los paneles coincidía con cualquier cifra en pesos y la cobertura por municipios con una frase genérica). Se corrigieron las reglas y se comprobó a mano cada pregunta que pasó a «cubierta».

### 4.3 Fuera de alcance y preguntas sin respuesta

**Fuera de alcance** (el asistente debe decir que no tiene esa información y remitir a un canal oficial):
- Valores de la factura de un cliente, y tarifas exactas por estrato (el sitio las publica en tablas por trimestre).
- Datos personales, consumos, estado de cuenta, o estado de una PQR o solicitud (Zona Clientes permite hacerle seguimiento con el número de radicado).
- Cortes en tiempo real y fechas de mantenimiento por barrio.
- Información financiera para inversionistas.
- Asesoría legal o regulatoria.
- Comparaciones con otras empresas de energía.

**Preguntas que la base hoy no responde (10).** Aparecen en el inventario como «Sin respuesta en la base»; si algún día se publican, su estado cambia solo.

| Pregunta | Por qué no se responde |
|---|---|
| Precio de paneles solares y cotizaciones | El sitio no publica precios; se cotiza con un asesor |
| Cuánto demora una conexión | Celsia no publica el plazo. El Contrato de condiciones uniformes está en un PDF bloqueado |
| Cuánto cuesta una conexión nueva | El sitio no publica el costo |
| Cuánto cuesta una reconexión | Solo se advierte que hay costos; no se publican |
| Ser proveedor o contratista | La base incluye la sección de proveedores, pero no explica cómo inscribirse |
| En qué municipios hay cobertura | No hay una lista oficial vigente; las sedes dan solo una parte |
| Horario del WhatsApp | El sitio no lo publica |
| Qué tan confiable es el servicio en mi zona | El sitio no publica indicadores de calidad de la energía por zona |
| Cómo protegen mis datos personales | La base solo menciona la política y su objetivo; el texto está en un PDF que el `robots.txt` bloquea |
| Atención para personas con discapacidad o en otros idiomas | No aparece en el sitio |

Pasaron al alcance al ampliar la base: comprar acciones, quién dirige Celsia y el plazo para responder una PQR (15 días hábiles; cómo apelar sigue sin estar). Para las demás, la salida correcta es que el asistente reconozca que no sabe y remita a un canal oficial.

### 4.4 Criterio de calidad
Una respuesta es correcta si (1) se apoya únicamente en la base de conocimiento, (2) coincide con la fuente oficial y (3) cuando no hay información, el asistente lo dice y remite a un canal oficial. Algunos trámites cambian entre Valle del Cauca y Tolima: el asistente debe indicar la región.

### 4.5 Conjunto de prueba
Es una lista de preguntas, escritas como las escribiría un cliente, **con la respuesta que el asistente debería dar**. Sirve para medir si el asistente funciona y para el informe. El taller exige al menos 20 y que se analice la calidad de las respuestas.

Está en `2 - Conjunto de prueba\conjunto_de_prueba` (el CSV se edita en Excel): **59 preguntas**: 35 de respuesta y 24 negativas (20 sin respuesta en la base o de vigencia y 4 de inyección de instrucciones, que miden que el asistente no obedezca órdenes escondidas en la pregunta). Las negativas son las que la base no responde o que piden datos de un cliente; miden que el asistente **reconozca que no sabe** y remita a un canal oficial en vez de inventar. Al ampliar la base se agregaron 9 preguntas de respuesta de temas que antes no cubría (proyectos, sostenibilidad, inversionistas, subsidios, regulación, pódcast, plazo de una PQR) y una negativa. Luego se amplió el alcance con 11 intenciones nuevas (K1 a K11: dueño, empleados, asistente Luz I.A., misión y visión, NIT, cobertura de internet, cable caído, recurso de reposición, contrato, medidor y mudanza), y con ellas 4 preguntas de respuesta y 8 negativas. Cada una tiene su respuesta esperada comprobada contra el texto oficial. Criterios y su cumplimiento, verificados automáticamente:
- Al menos 20 preguntas: **59**.
- Al menos la mitad de primer contacto o «ambos»: **49 de 59**.
- Están las 7 intenciones de primer contacto con una sola fuente, las más frágiles.
- Hay cinco formas de preguntar: directa, coloquial, incompleta, con contexto e inyección de instrucciones.
- Cada pregunta apunta a una intención del inventario y trae su fuente.

## 5. Conexión con el resto del taller
- Las intenciones (inventario) y las preguntas sin respuesta de 4.3 son la base del conjunto de prueba (4.5).
- Las secciones 3.1 a 3.4 alimentan «Preparación de los datos» del informe.
- Las secciones 1 y 2 alimentan «Descripción del problema».

## 6. Decisiones
- [x] Facebook, X y YouTube de Celsia revisados (27/10/2026); se documentan y no se scrapean.
- [x] Decisión (27/10/2026): los PDF de informes (reporte integrado, ASG, TCFD) se citan como contexto y no se descargan, porque el `robots.txt` los bloquea. Es una limitación conocida; con permiso de Celsia serían la siguiente ampliación.
- [x] Plazo de vigencia de las noticias: 12 meses (decisión en la regla R7, fijada a la fecha del scraping).
- [x] Cifras contradictorias del sitio: se cita la fuente y la fecha de cada una (ver Limitaciones de los datos del informe).
- [x] Noticias: ya se descargaron las 823; entran las de tema de cliente con menos de 12 meses y las atemporales, regla R7).
