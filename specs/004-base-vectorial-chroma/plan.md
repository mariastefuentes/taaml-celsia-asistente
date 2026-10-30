# Plan 004

1. `uv add chromadb` (verificado en PyPI: 62+ versiones desde 2023, licencia Apache 2.0).
2. `recuperacion.py`: `CHROMA`, `construir_chroma(ids, vectores, metadatos)`, `_coleccion()` (valida que los identificadores coincidan con `chunks.jsonl`), `almacen_vectorial()` y `buscar` consulta Chroma si está vigente; si no, la matriz.
3. `07_construir_indice.py`: al terminar, carga los vectores en Chroma. `.gitignore`: la carpeta de Chroma se regenera.
4. `10_evaluar_recuperacion.py`: hit@1, hit@3 y `posicion`.
5. `tests/test_recuperacion_chroma.py`: paridad con la matriz y orden determinista.
6. Re-medir y actualizar informe, guías y PDF.
