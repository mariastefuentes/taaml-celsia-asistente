---
estado: cumplida
escrita: 2026-10-29
---
# Spec 007: pestaña «Corpus y scraping» en la app

Nace de la revisión contra la rúbrica de la sustentación (criterio «UI en acción: scraping visible», 20 %): el nivel máximo pide ver en pantalla el proceso por etapas (descubrir → extraer → limpiar → deduplicar → enriquecer), las métricas del corpus (URLs, páginas, tokens, descartes) y un Q&A que cita la fuente. La app tenía el Q&A con fuentes, pero no el proceso ni las métricas. Se escribe **antes** de programar.

## Qué se necesita
1. `src/taaml/corpus.py` con `metricas()`: lee solo archivos versionados (`data/2_silver/_registro.csv`, `data/3_gold/_catalogo.csv`, `data/4_curaduria/registro_curaduria.csv`, `documentos_incluidos.jsonl`, `chunks.jsonl`) y devuelve las etapas con su entrada, su salida y lo descartado. No llama a ningún modelo ni a la red.
2. Una cuarta pestaña en `app.py`, «Corpus y scraping», con: las cinco etapas (más curar y fragmentar) con sus cifras, los descartes por motivo, la distribución de documentos por categoría y los tokens del corpus.
3. Pruebas que comprueban que las cifras de la pestaña coinciden con los archivos y que cada etapa conserva la cuenta (entrada − descartes = salida).

## Criterios de aceptación
- Las cifras son las mismas del informe (1.272 páginas descargadas, 1.100 en Silver, 393 documentos curados, 1.690 fragmentos).
- La pestaña funciona sin Gemini ni Ollama.

## Fuera de alcance
- Volver a descargar el sitio desde la app.
