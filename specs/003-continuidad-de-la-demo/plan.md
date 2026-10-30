# Plan 003

1. `src/taaml/respaldo.py`: `cadena_de_modelos(elegido)`, `es_falla_del_proveedor(error)`, `con_respaldo(funcion, modelo, *args)` → `(resultado, modelo_usado, avisos)` y `respuesta_guardada(pregunta)` → `(respuesta, fragmentos)` o `None`.
2. `tareas.py`: `obtener_modelo` acepta `ollama:<nombre>` (`ChatOllama`, `num_ctx` 8192) y las tareas estructuradas lo tratan como DeepSeek (llamada a función).
3. `app.py`: las tres pestañas llaman con respaldo; el Q&A cae a la respuesta guardada y muestra una nota con el modelo usado.
4. `scripts/16_ensayo_demo.py`: comprobaciones gratis y, con `--llamar`, una llamada por proveedor.
5. `tests/test_respaldo.py` (sin modelos) y lista de verificación en la guía de sustentación.
