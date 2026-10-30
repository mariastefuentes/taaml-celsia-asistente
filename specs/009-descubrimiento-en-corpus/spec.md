---
estado: cumplida
escrita: 2026-10-30
---
# Spec 009: la etapa «Descubrir» muestra descubiertas, bloqueadas y con error

Nace de revisar la rúbrica: la pestaña «Corpus y scraping» decía «1.272 URLs descargadas», pero la rúbrica pide ver el proceso. Faltaba separar cuántas URLs se descubrieron en los sitemaps, cuántas bloqueó `robots.txt` y cuántas fallaron. Se escribe **antes** de programar.

## Qué se necesita
1. `scripts/03_construir_silver.py` escribe `data/2_silver/_descubrimiento.json` (versionado; Bronze no se sube a GitHub) con, a partir del índice de Bronze y la última fila de cada URL: URLs descubiertas, descargadas, bloqueadas por `robots.txt`, con error HTTP y el detalle por sección del sitemap.
2. `src/taaml/corpus.py` usa ese archivo en la etapa 1 (entra = descubiertas; sale = descargadas; descartes = bloqueadas y con error). Si el archivo no existe, la etapa muestra solo las descargadas, como antes.
3. La pestaña muestra una métrica más: URLs descubiertas.

## Criterios de aceptación
- Las cifras salen del índice real: 1.273 descubiertas, 1.272 descargadas, 0 bloqueadas, 1 con error (un 500 del propio sitio).
- Volver a correr el script 03 no cambia ningún otro archivo versionado.
- Pruebas: la función de resumen y que cada etapa conserve la cuenta.
