---
estado: cumplida
escrita: 2026-10-29
---
# Spec 006: tabla de recuperación por pregunta y pruebas del pipeline de datos

Nace de la comparación con el repositorio de un compañero (tabla por pregunta de vector contra híbrido; más pruebas). La usuaria lo aprobó («Sí, haz la tabla… y las pruebas del pipeline»). Se escribe **antes** de programar.

## Qué se necesita
1. **Tabla por pregunta.** Un documento `docs/2 - Conjunto de prueba/recuperacion_por_pregunta.md` (y su PDF) con una fila por pregunta de respuesta y, por método (palabras, híbrido, embeddings), la posición en que aparece la respuesta entre los 12 fragmentos o «–» si no está. Sale de `resultados/recuperacion_k12.csv`; `10_evaluar_recuperacion.py` la escribe al terminar una corrida completa y `--solo-tabla` la regenera del CSV sin correr nada.
2. **Pruebas del pipeline de datos** (sin Ollama, sin modelos y sin tocar `data/`): la decisión de la curaduría (`decidir`), la extracción de texto del HTML (`extraer` y `fecha_publicacion`) y el fragmentado (`fragmentar` e `identificador`).

## Criterios de aceptación
- La tabla no cambia ninguna cifra: sus totales coinciden con los del informe (hit@12 54 %, 74 % y 89 %).
- Las pruebas usan datos de ejemplo escritos en la propia prueba.

## Fuera de alcance
- Reorganizar el código en paquetes y usar un modelo local como principal (se evaluaron y se descartaron por riesgo y poco aporte).
