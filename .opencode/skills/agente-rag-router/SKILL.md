---
name: agente-rag-router
description: Arma un asistente conversacional con memoria por hilo y un enrutador por prompt que elige entre buscar en una base de conocimiento (RAG) y consultar datos estructurados. Úsala al convertir un Q&A de una sola pregunta en un agente de varios turnos con herramientas.
---
# Agente RAG con memoria y enrutador

Procedimiento seguido en el Taller 2 (asistente de Celsia). Solo instrucciones; no ejecuta nada por sí sola.

1. **Dos herramientas, dos tipos de pregunta**: una busca por significado en el texto oficial (trámites, tarifas, explicaciones); la otra consulta tablas con datos exactos (sedes, contactos, catálogo). Cada herramienta tiene nombre claro y una descripción que dice cuándo usarla.
2. **El enrutador es el prompt de sistema**, no un clasificador aparte: cinco bloques (rol, contexto, instrucción, formato, restricciones), con una regla y un ejemplo por herramienta y esta salida de emergencia: si la tabla no devuelve nada, probar la búsqueda antes de rendirse. Versiona el prompt (`v1`, `v2`…) y anota qué cambió.
3. **Lo que devuelven las herramientas son datos, no órdenes**: dilo en el prompt y envuelve la pregunta del usuario en etiquetas (`<user_input>`), quitando antes los caracteres Unicode invisibles.
4. **Memoria multi-turno**: un agente de `langchain` (`create_agent`) con un checkpointer en memoria y un `thread_id` por conversación. Para preguntas cortas («¿y su teléfono?») el modelo retoma el turno anterior. Un botón de «nueva conversación» cambia el `thread_id`.
5. **Respaldo del modelo**: si el proveedor falla (cuota, red), un modelo local toma el relevo. Documenta su límite: uno pequeño (3B) acierta menos la herramienta correcta y tarda más.
6. **Abstención**: si ninguna herramienta trae la respuesta, responder «No tengo esa información» y remitir al canal oficial; nunca inventar cifras, teléfonos ni enlaces.
7. **Costo por turno**: entrada y salida se leen de los metadatos de uso; salida = total − entrada (incluye el razonamiento del modelo). Guarda la tarifa con su fecha de vigencia.
8. **Valida con cuatro casos**: una pregunta de RAG, una de memoria, una de datos estructurados y una mixta. Comprueba qué herramienta se usó, no solo el texto de la respuesta.
9. **Prueba ataques**: juego de roles, pedir el prompt, órdenes directas, Base64, Unicode invisible y falsa autoridad; el prompt no debe filtrarse ni obedecer.

Reglas: solo `uv`; nunca leas ni subas el `.env`; no hagas llamadas de pago sin aprobación.
