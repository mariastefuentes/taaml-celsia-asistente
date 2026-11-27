## 6. Qué encontramos (sobre 114 conversaciones simuladas)

**Los vectores sí capturan el tema.** K-means, sin ver la categoría prevista, recupera la estructura con un índice de Rand ajustado de 0,53 (1 sería idéntico; con los embeddings anteriores daba 0,45): los reclamos quedan juntos (clúster de 16 con 88 % de pureza), los datos personales en otro (11, 100 %), las preguntas de factura en uno (11, 91 %) y las de producto en dos (17 con 71 % y 8 con 100 %). Se mezclan sobre todo los saludos con las conversaciones largas (`mixta`) y las preguntas ambiguas con las molestas, lo que es razonable.

**KNN frente a t-SNE.** Clasificando cada conversación por sus 5 vecinas más cercanas (dejando una fuera), KNN acierta la categoría prevista el 74 % de las veces en los vectores originales, el 67 % en el t-SNE 3D y el 69 % en el t-SNE 2D, contra 18 % del azar. Proyectar a 2 o 3 dimensiones pierde información: t-SNE es una buena forma de **mirar** los grupos, y KNN en el espacio original es la forma de **buscar** conversaciones parecidas (por ejemplo, las 5 más cercanas a un reclamo por corte de luz son 4 reclamos y una conversación mezclada que también trata de un corte). El 74 % tampoco es un techo malo: varias categorías que escribimos se solapan de verdad.

**El asistente marcó 20 conversaciones como fallidas (18 %), pero no todas son fallos.** La marca es una regla simple: el asistente dijo «no tengo esa información» o «no pude», o una herramienta devolvió error. Al leer las 20 una por una:

| Qué pasó | Conversaciones | Veredicto |
|---|---|---|
| Preguntas fuera de alcance (fútbol, recetas, código, clima) y una petición de «claves del sistema» | 15 | **Comportamiento correcto**: el asistente rechaza y redirige. Es lo que pide el prompt v6. |
| La base de conocimiento no tiene el dato (precio del cargador, fecha límite de pago, facturación por estimación) | 3 | **Vacío de contenido**: el asistente lo dice con honestidad y da la línea 01 8000 112 115. Se arregla ampliando la base, no el agente. |
| El asistente rechazó una pregunta de Celsia que sí debía contestar | 2 | **Fallo real**: «¿Qué es la energía renovable?» se rechazó sin buscar, y «¿Cómo funcionan los paneles?» buscó pero la búsqueda no trajo el fragmento correcto. |

Es decir, la tasa de fallo útil es de **5 de 114 (4 %)**, no de 18 %, y los dos fallos reales son preguntas generales de energía que no mencionan a Celsia por su nombre. El prompt v6 es estricto con lo que queda fuera de alcance y, a veces, trata un tema de energía como ajeno a Celsia.

**Dónde mirar primero.** (1) El clúster 2 mezcla los rechazos correctos con la petición de claves: es el más grande en fallidas (14 de 24). (2) Las conversaciones `mixta` tienen la tasa más alta entre las de temas de Celsia (33 %) porque un solo turno malo marca toda la conversación; allí, en los clústeres 6 y 7, están los dos rechazos erróneos. (3) No hubo ninguna conversación `ambiguo` marcada como fallida, pero eso no significa que estén bien: el asistente puede responder algo vago sin decir «no sé», y esta regla no lo detecta.

**Límites de este análisis.** Los datos son simulados y escritos por nosotros, así que las proporciones (18 %, 4 %) **no** describen a clientes reales; sirven para mostrar el método y para encontrar tipos de fallo. La marca de «fallida» es una heurística de palabras, no un juicio humano. t-SNE conserva la vecindad local pero no las distancias entre grupos, así que se interpreta qué conversaciones quedan juntas, no qué tan lejos están dos nubes. Con tráfico real habría que leer una muestra de cada clúster antes de sacar conclusiones.
