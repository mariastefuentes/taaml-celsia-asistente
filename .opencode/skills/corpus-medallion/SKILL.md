---
name: corpus-medallion
description: Construye el corpus de una empresa a partir de su sitio web en capas Bronze, Silver y Gold, y lo deja listo para RAG. Úsala al capturar, limpiar o fragmentar contenido corporativo público.
---
# Corpus Medallion

Procedimiento seguido en el Taller 1 (empresa: Celsia). Solo instrucciones; no ejecuta nada por sí sola.

1. **Antes de descargar**: lee el archivo robots.txt y el mapa del sitio (sitemap.xml) que publica la empresa. Lo que esté en `Disallow` no se toca, ni tampoco datos personales (Ley 1581).
2. **Bronze (crudo)**: descarga con `requests`, un `User-Agent` que diga quién eres, 1 s entre peticiones y tiempo máximo de espera. Guarda el HTML tal cual y un registro con URL, fecha, código HTTP y hash; anota también las páginas bloqueadas o con error.
3. **Silver (limpio)**: quita menús, scripts, pie de página y avisos de cookies; descarta textos muy cortos y duplicados exactos por hash. Registra cada descarte y su motivo.
4. **Gold (enriquecido)**: un Markdown por documento con encabezado (URL, título, fuente, fechas, categoría, región, idioma, caracteres, tokens, hash) y un único archivo JSONL (una línea por documento) con lo mismo.
5. **Curaduría**: decide qué documentos entran con reglas escritas y deja el registro de cada decisión.
6. **Fragmentos**: 1.000 caracteres con solape de 150, con identificadores únicos y estables; comprueba que los datos clave sobreviven.
7. **Índice**: calcula embeddings con un modelo abierto y local; recalcula solo lo que cambió.
8. **Verifica**: mide la recuperación con preguntas reales antes de gastar en el modelo.

Reglas: solo `uv`; nunca leas ni subas el `.env`; guarda siempre el texto crudo para poder reprocesar.
