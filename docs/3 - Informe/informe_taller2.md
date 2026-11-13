# Informe del Taller 2: agente de Celsia con memoria, herramientas y enrutamiento

## Resumen

El asistente del Taller 1 respondía cada pregunta por separado y siempre buscaba en el texto del sitio. Para este taller se convirtió en un **agente conversacional**: recuerda lo que el cliente ya dijo (dentro de la conversación y entre conversaciones), tiene dos herramientas de consulta (búsqueda por significado en el texto oficial y datos exactos en tablas) y dos de memoria, y decide cuál usar con un prompt que hace de enrutador. El modelo del agente es `gemini-3.8-flash` por API de pago, con respaldo local (`llama3.2`). La interfaz es una aplicación React que habla por HTTP, con respuestas en streaming, con una API FastAPI que ejecuta el agente.

Con 22 preguntas etiquetadas, el agente eligió la herramienta esperada en 22 de 22 casos y los parámetros de la consulta (tabla y ciudad) en 11 de 11. Una conversación de cuatro turnos cuesta unos 0,02 USD y un turno tarda 8,8 s de mediana (de 2,6 a 28 s). Los 11 ataques directos y los 8 casos de inyección indirecta contra el agente (uno de ellos intenta envenenar su memoria) fueron rechazados. Los límites principales son que el modelo ignora `temperature` y `top_p` (sus textos pueden variar entre ejecuciones), que algunas preguntas disparan búsquedas de más y que el conjunto de enrutamiento es pequeño.

## 1. Problema y objetivo

Un cliente de Celsia mezcla en la misma conversación preguntas de naturaleza distinta: dónde queda una oficina y a qué hora abre (dato exacto), cómo se cancela un servicio (explicación en texto) y «¿y su teléfono?» (una pregunta que solo se entiende con el turno anterior). Un sistema de pregunta y respuesta de un solo paso falla en los tres frentes: busca por significado un dato que está en una tabla, no recuerda y no distingue qué fuente conviene.

Objetivo: un agente que (1) conserve la conversación, (2) consulte datos exactos cuando la pregunta lo pide y busque en el texto cuando necesita una explicación, y (3) se abstenga («No tengo esa información») cuando ninguna fuente responde.

El enfoque se apoya en tres ideas. La generación aumentada con recuperación (Lewis et al., 2020) mantiene las respuestas atadas al texto oficial. El patrón ReAct (Yao et al., 2022) alterna razonar y actuar: el modelo decide qué herramienta llamar, mira el resultado y decide de nuevo, y los modelos pueden aprender a usar herramientas (Schick et al., 2023). Y el sistema final es un conjunto de componentes (modelo, herramientas, memoria, validaciones) y no un solo modelo, lo que Zaharia et al. (2024) llaman sistema de IA compuesto.

## 2. Arquitectura

![Arquitectura del agente: camino de una pregunta](diagrama_arquitectura_agente.svg)

El agente se construye con `create_agent` de LangChain. En cada turno ocurre lo siguiente:

1. La pregunta se limpia de caracteres invisibles (Unicode), que pueden esconder órdenes.
2. Un componente intermedio recorta lo que ve el modelo a los últimos mensajes que caben en unos 3.000 tokens, siempre empezando en un turno del cliente. El historial completo sigue guardado.
3. El modelo lee el prompt (rol, contexto, instrucción, formato y restricciones) y decide si responde o llama a una herramienta.
4. Si llama a una herramienta, recibe el resultado y vuelve a decidir; el ciclo termina cuando responde.
5. El turno queda guardado en SQLite bajo el identificador de la conversación.

Si Gemini falla (cuota o red), un respaldo cambia al modelo local `llama3.2`. En la prueba del respaldo acertó 2 de 4 casos con herramientas y es lento, por lo que sirve para no dejar al cliente sin respuesta y no como alternativa de calidad.

La alternativa de armar el flujo a mano con un grafo de estados (`StateGraph`) daría más control, pero para dos herramientas y un ciclo de decisión `create_agent` ya lo resuelve con menos código que mantener.

### 2.1 Decisiones de tecnología

| Decisión | Elegido | Por qué |
|---|---|---|
| Marco de trabajo | LangChain | El Taller 1 ya estaba construido con él; `create_agent` trae el ciclo de herramientas, el checkpointer de memoria y los componentes intermedios (recorte del historial, respaldo de modelo) sin código propio. LlamaIndex se centra en indexar y consultar documentos, y el agente aquí importa más que el índice; Agno es otra alternativa de agentes que no ofrecía ventaja para dos herramientas. |
| Modelo de conversación | `obtener_modelo` propio | Elige entre Gemini, DeepSeek y Ollama y arma la cadena de respaldo. `init_chat_model` de LangChain hace algo parecido; se reevalúa en el siguiente taller. |
| Conocimiento | RAG, no fine-tuning | Los datos cambian (sedes, avisos, tarifas), cada respuesta debe poder citar su fuente y no hay un conjunto de entrenamiento: actualizar un índice es barato y reentrenar no. |
| Motor de vectores | Chroma, índice HNSW con coseno | HNSW organiza los vectores en un grafo por capas: se baja desde pocos nodos lejanos hasta los vecinos cercanos y así encuentra los más parecidos sin comparar contra los 1.690 fragmentos. Chroma funciona dentro del proceso, sin servidor, y alcanza para este tamaño. |
| Embeddings | `nomic-embed-text-v2-moe` (Ollama) | Multilingüe y de licencia abierta. Los rankings generales (MTEB, Muennighoff et al., 2022; BEIR, Thakur et al., 2021) orientan, pero no miden español sobre este corpus, así que se midió con un conjunto propio (hit@k, precisión, recall y nDCG). |
| API frente a modelo local | Gemini por API; Ollama solo para embeddings y respaldo | El equipo tiene 7,7 GB de RAM y sin GPU: un modelo local tarda minutos por pregunta. La API es aceptable porque los datos son públicos. |

**Licencias.** Gemini se usa bajo los términos del servicio de Google; Llama 3.2 con la licencia comunitaria de Meta (exige la mención «Built with Llama»); Qwen3-4B y `nomic-embed-text-v2-moe` son Apache 2.0.

**Si cambia el modelo de embeddings.** Se conserva el texto original, se vuelven a calcular todos los vectores y se reconstruye el índice completo: nunca se mezclan vectores de dos modelos, porque sus distancias no son comparables.

## 3. Memoria conversacional

**Qué se guarda.** Cada conversación es un hilo identificado por un `uuid4`; el checkpointer de SQLite (`SqliteSaver`) guarda todos los mensajes, incluidas las llamadas a herramientas. La memoria sobrevive a reiniciar la aplicación y, como el identificador va en la dirección (`?hilo=`), al recargar la página la conversación se recupera.

**Qué ve el modelo.** Solo los últimos ~3.000 tokens. Sin este recorte, la entrada crece en cada turno porque el historial se reenvía completo: en el ensayo de cuatro turnos pasó de 2.238 a 8.554 tokens. El recorte controla el costo sin borrar nada de lo guardado.

La memoria guardada en SQLite corresponde a lo que la literatura llama memoria de corto plazo (la conversación en curso) con persistencia (Wu et al., 2025). No se agregó memoria de largo plazo ni resumen del historial: el índice es pequeño, no se guardan datos del cliente a propósito y el recorte ya controla el costo.

**Cómo se verificó.**
- Pruebas automáticas: persistencia entre dos agentes distintos sobre el mismo archivo, aislamiento entre hilos, que el recorte no borra lo almacenado, un turno que por sí solo supera el límite, y recuperación de la conversación al recargar la aplicación, también cuando el archivo de memoria está dañado.
- Casos de la matriz: «¿y su teléfono?» tras preguntar por las sedes de Ibagué se resolvió a la sede correcta (608 277 08 22), y «¿Cómo me llamo y dónde vivo?» se respondió desde la conversación, sin herramientas.

**Memoria de largo plazo.** Lo que el cliente cuenta de sí mismo (su nombre, dónde trabaja) se guarda en un Store de LangGraph sobre SQLite, en un espacio propio por cliente, y se recupera en una conversación nueva. El agente tiene dos herramientas para esto: `guardar_dato_del_cliente`, que guarda una frase corta y no acepta duplicados ni más de 20 datos por cliente, y `recordar_datos_del_cliente`, que devuelve lo guardado. El identificador del cliente lo pone la aplicación y no lo ve el modelo, así que un cliente no puede leer lo de otro; sin identificador (cliente anónimo) no hay memoria de largo plazo, para que los anónimos no compartan datos. El prompt prohíbe guardar cédulas, claves, tarjetas, cuentas y datos de salud. El cliente puede ver lo que el agente recuerda y borrarlo desde la aplicación («Lo que recuerdo»). Con Gemini real, «Me llamo Ana y trabajo en Carvajal» en una conversación se recuperó al preguntar «¿Dónde trabajo y cómo me llamo?» en otra distinta.

**Privacidad.** La memoria guarda conversaciones en disco. Los datos personales de clientes caen bajo la Ley 1581 de 2012 (protección de datos personales); el identificador de la conversación es un `uuid4` no adivinable, pero cualquiera que lo conozca ve el hilo. En una operación real habría que definir plazos de retención y borrado.

## 4. Diseño de herramientas y enrutamiento

### 4.1 Herramientas

| Herramienta | Para qué sirve | Cómo funciona |
|---|---|---|
| `consultar_datos` | Dato exacto | Filtra tablas locales: «sedes» (direcciones, horarios y teléfonos de sedes, tiendas y puntos de pago, con ciudad, departamento y tipo), «contactos» (teléfonos, WhatsApp, correos y enlaces) y «catálogo» (páginas del sitio). Sin modelo ni embeddings: la respuesta es idéntica cada vez. Sus argumentos se validan con un esquema Pydantic (`ConsultaDatos`): tabla restringida a las tres existentes y filtros de largo acotado. |
| `guardar_dato_del_cliente` y `recordar_datos_del_cliente` | Memoria de largo plazo | Escriben y leen en el Store el dato que el cliente cuenta de sí mismo, en un espacio por cliente. |
| `buscar_en_base` | Explicación en texto | Busca por significado en 1.690 fragmentos del texto oficial (embeddings `nomic-embed-text-v2-moe` en Chroma) y devuelve 4 fragmentos. Son 4 y no los 12 del Taller 1 porque cada turno reenvía el historial. |

Las de consulta solo leen; las de memoria solo escriben o leen el dato que el cliente cuenta de sí mismo, y ninguna ejecuta acciones. Lo que devuelven se trata como datos: el prompt indica ignorar frases que parezcan órdenes dentro de ellos y el texto recuperado se limpia de caracteres invisibles y de etiquetas que podrían cerrar el bloque de contexto.

### 4.2 Enrutador

![Enrutamiento: cómo elige el agente la herramienta](diagrama_enrutamiento.svg)

El enrutador no es código sino el **prompt avanzado** (`prompts/v3_agente.md`): describe cada herramienta, da una regla de elección con un ejemplo por caso y fija las excepciones: si `consultar_datos` responde «Sin resultados» se prueba `buscar_en_base` antes de rendirse, y las preguntas cortas se resuelven con el turno anterior sin suponer datos que el cliente no dijo. El prompt conserva la estructura de cinco bloques y las prácticas de instrucción directa, ejemplos y restricciones explícitas recogidas en los estudios de técnicas de prompting (Schulhoff et al., 2024; Bsharat et al., 2023). Se eligió así, y no con un clasificador aparte, porque con dos herramientas el modelo ya decide bien y un clasificador sumaría otra pieza que mantener y medir.

## 5. Resultados

### 5.1 Matriz de enrutamiento

Son 22 preguntas con la herramienta esperada escrita antes de correrlas: 6 de sedes, 4 de contactos, 5 de texto, 3 mixtas (trámite más lugar o número), 2 de memoria, 1 fuera de dominio y 1 de una ciudad sin sede. Cada una se hizo en una conversación nueva (las de memoria, tras un turno de preparación).

| Resultado | Valor |
|---|---|
| Herramienta esperada | 22 de 22 |
| Parámetros correctos (tabla y ciudad) | 11 de 11 donde la matriz los fija |
| Preguntas con una herramienta de más | 6 de 22 (R04, R05, R08, R09, R13, R22) |
| Tokens de entrada por turno (mediana) | 4.068 |
| Tiempo por turno | mediana 8,8 s; de 2,6 s a 28,4 s |
| Costo de las 22 preguntas | 0,173 USD |

**Cómo se calificó.** Una pregunta cuenta como correcta si la herramienta esperada está entre las usadas; usar una herramienta de más no se penaliza (se cuenta aparte). Las de memoria aceptan responder sin herramienta o con una consulta de datos, y la del enlace de pago acepta cualquiera de las dos herramientas. Los parámetros (tabla y ciudad) se comparan sin tildes. Las etiquetas las escribió el equipo antes de correr y dos se corrigieron después de ver los resultados: Medellín sí está en la tabla de sedes, así que no era un caso sin dato, y se agregó Pasto, que no tiene sede, como caso negativo.

Por tipo de pregunta, las de sedes tardan unos 7 s, las de contactos y las de texto de 9 a 10 s, las mixtas 15 s (dos herramientas y más historial) y las de memoria o fuera de dominio entre 3 y 9 s. Cuando una pregunta de datos usó además `buscar_en_base` (por ejemplo, el enlace de pago), la respuesta fue correcta pero más cara y lenta.

**Caso débil.** «¿Cuánto cuesta reconectar el servicio?» eligió bien la herramienta, pero encadenó búsquedas, gastó 36.941 tokens de entrada (0,030 USD, 28 s) y terminó en «No tengo esa información». No hay una respuesta incorrecta, pero es el patrón a vigilar: una pregunta sin respuesta clara en el corpus puede hacer que el agente busque varias veces. Para una ciudad sin sede (Pasto) el agente consultó la tabla, buscó en el texto y respondió «No tengo esa información» con la línea de atención, sin inventar una dirección.

### 5.2 Cadena frente a agente

| | Cadena (Taller 1) | Agente (Taller 2) |
|---|---|---|
| ¿Quién decide buscar? | Siempre busca (dos pasos fijos) | El modelo decide |
| Fragmentos al modelo | 12 por pregunta | 4 por búsqueda |
| Tokens de entrada | 4.615 de media (59 preguntas) | 2.238 a 8.554 por turno según el historial |
| Tiempo por pregunta | 7,2 s de media | 8,8 s de mediana en la matriz |
| Memoria | No | Sí |

El agente puede ser más barato cuando no necesita buscar (el turno resuelto desde la memoria costó 0,0022 USD) y más caro cuando encadena herramientas o el historial crece. Los modelos son distintos (`gemini-3.5-flash` en la cadena y `gemini-3.8-flash` en el agente), así que la comparación es orientativa y no un experimento controlado.

### 5.3 Seguridad

Hay dos pruebas:

- **Ataques directos, sobre el agente (`gemini-3.8-flash`, prompt v3).** La batería de 11 casos (juego de rol, fuga del prompt, orden directa, texto codificado en base64, texto invisible, mundo hipotético, falsa autoridad, cambio de rol, adulación, propina virtual y chantaje emocional) fue rechazada en los 11. Las categorías siguen las que Shen et al. (2023) observaron en jailbreaks reales.
- **Inyección indirecta, sobre el agente (`gemini-3.8-flash`, prompt v3).** Son 8 casos en que una orden escondida se agrega a lo que devuelve la herramienta que el agente use en esa pregunta (`consultar_datos` en 5 casos y `buscar_en_base` en 3): una orden visible, otra en inglés, una con caracteres invisibles, un cierre falso del bloque de contexto, un dato falso con tono de autoridad, un intento de revelar el prompt y uno de que el agente **escriba en la memoria del cliente** un dato falso («es VIP con 50 % de descuento»). Resistieron los 8, y la memoria del cliente quedó vacía en todos. Este es el riesgo que describen Greshake et al. (2023) y el que OWASP lista entre los principales de aplicaciones con modelos de lenguaje. Con el asistente del Taller 1 (`gemini-3.5-flash`, prompt v3, sin herramientas que escriban) los 7 casos equivalentes también se rechazaron.

Son pruebas escritas por el equipo, con una sola corrida por caso: muestran que estas órdenes no funcionaron, no que el sistema sea inmune.

### 5.4 Decisiones de recuperación

- **Umbral de similitud.** Con este modelo de embeddings los cosenos van de 0,3 a 0,6. Un umbral de 0,5 conserva 26 de 35 respuestas y deja sin contexto a 16 de 24 preguntas negativas; sin umbral se conservan 31 de 35. No se adoptó un umbral duro porque pierde respuestas y el modelo ya se abstiene por instrucción del prompt.
- **Tamaño de fragmento.** Con 500, 1.000 y 1.500 caracteres, el nDCG@10 con embeddings fue 0,504, 0,535 y 0,549. Se mantuvo 1.000 con solape de 150: la diferencia de 0,014 con 1.500 cae dentro del ruido de 35 preguntas y 500 duplica los fragmentos.
- **Método de búsqueda.** Con k=10 y 35 preguntas, los embeddings superan al híbrido y a las palabras (nDCG 0,535 frente a 0,427 y 0,290; recall 0,515, 0,414 y 0,254).

## 6. Aplicación

El frontend es una aplicación React (Vite) en `frontend/` que nunca llama al modelo: habla por HTTP con una API FastAPI (`api/main.py`) que ejecuta el agente y responde por streaming (Server-Sent Events). Muestra la conversación a medida que se escribe, qué herramienta usó cada respuesta con sus tokens y costo, maneja errores de red y del modelo con un mensaje que no filtra detalles internos y un botón de reintento, y permite empezar una conversación nueva, ver lo que el agente recuerda y borrarlo. El hilo va en la dirección (`?hilo=`) y al recargar la página se recupera desde SQLite. El código del agente está en `src/taaml/agente.py`, el prompt en `prompts/v3_agente.md` y las pruebas automáticas cubren la memoria, el recorte, el enrutamiento y la aplicación sin llamar a Gemini ni a Ollama.

## 7. Limitaciones

- **Variabilidad del modelo.** `gemini-3.8-flash` ignora `temperature` y `top_p` (se midió: cinco frases distintas en cinco intentos con 0,0 y 0,1, igual que con 2,0 y 1,0). Los textos pueden variar entre ejecuciones; lo que se protege son la herramienta elegida, los datos exactos que salen de las tablas y la abstención.
- **Matriz pequeña.** Son 22 preguntas, cada una corrida una sola vez, con etiquetas escritas por el equipo. Sirve para ver el comportamiento, no para estimar una tasa con precisión.
- **Costo y latencia.** Las búsquedas encadenadas y el historial elevan el costo y el tiempo. El precio de `gemini-3.8-flash` es de 0,75 USD por millón de tokens de entrada y 3,75 de salida hasta el 31/12/2026; desde el 1/1/2027 sube a 1,50 y 7,50.
- **Respaldo local.** `llama3.2` solo acertó 2 de 4 casos con herramientas y es lento: cubre una caída, no reemplaza al modelo principal.
- **Dependencia del modelo del Taller 1.** El asistente de preguntas y respuestas usa `gemini-3.5-flash`, que existe en la API pero no figura en la documentación pública de precios; podría retirarse. Cambiarlo es un ajuste de configuración, pero habría que repetir la evaluación.
- **Datos.** Las sedes y los contactos salen de un scraping y de un manual del equipo; pueden quedar desactualizados. Hay avisos antiguos en el texto (por ejemplo, de 2021).
- **Vulnerabilidades de dependencias.** La auditoría de dependencias dejó dos sin corrección posible hoy: `pillow` (lo limita la versión de Streamlit) y `chromadb` (sin versión corregida publicada).
- **Privacidad.** Las preguntas viajan a Google; con datos públicos no es un problema, pero en una empresa real habría que revisarlo, así como la retención de las conversaciones.

### Técnicas consideradas y no adoptadas

Tampoco se adoptaron la autoconsistencia (varias respuestas por pregunta), la optimización automática de prompts (DSPy) ni la repetición del prompt: multiplican las llamadas y el costo con un modelo que ya razona, y no hay evidencia propia de que mejoren. La idea de una «wiki» que el propio modelo mantiene como base de conocimiento tampoco se usó: la base sigue siendo el texto oficial indexado, que se puede auditar contra el sitio.

No se usaron resumen automático del historial, almacén de memoria de largo plazo, viaje en el tiempo del estado, pasos de aprobación humana ni un guardrail externo (Llama Guard, NeMo): el índice es pequeño, las herramientas solo leen, no se guardan datos personales a propósito y las defensas del prompt y de la validación resistieron las pruebas. Si se agregara una herramienta que escriba (por ejemplo, abrir un reclamo), la aprobación humana y la memoria persistente ya existente permitirían pausar el agente antes de la acción. El filtro por región (Valle o Tolima) queda como mejora: solo 5 de las 35 preguntas del conjunto permiten medirlo.

## Referencias

- Yao, S. et al. (2022). *ReAct: Synergizing Reasoning and Acting in Language Models*. arXiv:2210.03629.
- Lewis, P. et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. arXiv:2005.11401.
- Wu, Y. et al. (2025). *From Human Memory to AI Memory: A Survey on Memory Mechanisms in the Era of LLMs*. arXiv:2504.15965.
- Greshake, K. et al. (2023). *Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection*. arXiv:2302.12173.
- Schick, T. et al. (2023). *Toolformer: Language Models Can Teach Themselves to Use Tools*. arXiv:2302.04761.
- Schulhoff, S. et al. (2024). *The Prompt Report: A Systematic Survey of Prompt Engineering Techniques*. arXiv:2406.06608.
- Bsharat, S. M. et al. (2023). *Principled Instructions Are All You Need for Questioning LLaMA-1/2, GPT-3.5/4*. arXiv:2312.16171.
- Shen, X. et al. (2023). *"Do Anything Now": Characterizing and Evaluating In-The-Wild Jailbreak Prompts on Large Language Models*. arXiv:2308.03825.
- Muennighoff, N. et al. (2022). *MTEB: Massive Text Embedding Benchmark*. arXiv:2210.07316.
- Thakur, N. et al. (2021). *BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models*. arXiv:2104.08663.
- OWASP. *Top 10 for Large Language Model Applications*.
- Zaharia, M. et al. (2024). *The Shift from Models to Compound AI Systems*. Berkeley AI Research (BAIR) Blog.
- LangChain: documentación de `create_agent`, memoria a corto plazo y middleware (docs.langchain.com).
- Ley 1581 de 2012 de Colombia (protección de datos personales).

## Declaración de uso de IA

| Herramienta | Para qué se usó | Cómo se verificó |
|---|---|---|
| Claude Code (Anthropic) | Escribir y revisar código (agente, memoria, herramientas, pruebas, scripts de medición) y documentos del proyecto | El equipo revisa lo generado; cada cifra se vuelve a calcular con los scripts; la suite de pruebas y el revisor automático corren antes de cada commit |
| Gemini `gemini-3.8-flash` por API | Modelo del agente | Se midió con la matriz de enrutamiento, la batería de ataques y el ensayo de conversación |
| Gemini `gemini-3.5-flash` por API | Modelo del asistente de preguntas y respuestas del Taller 1 | Se evaluó con 59 preguntas y revisión manual |
| `llama3.2` (Ollama, local) | Respaldo del agente | Se probó con 4 casos; no se midió más |
| `nomic-embed-text-v2-moe` (Ollama, local) | Embeddings de los fragmentos y de las preguntas | Se mide con la recuperación (hit@k, precisión, recall y nDCG) |

Todo código o texto generado por una herramienta lo revisa una persona del equipo.
