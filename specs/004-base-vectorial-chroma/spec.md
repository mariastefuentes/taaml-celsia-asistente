---
estado: cumplida
escrita: 2026-10-29
---
# Spec 004: Chroma como base vectorial, hit@1 y hit@3, y orden determinista

Nace de comparar con el repositorio de un compañero (Chroma, métricas por posición, prueba de orden estable) y de una revisión del enunciado, que marcó la matriz NumPy como riesgo frente a «base de datos vectorial». La usuaria aprobó las tres cosas y la instalación de `chromadb` («Hagamos las 3»). Se escribe **antes** de programar.

## Qué se necesita
1. **Chroma como base vectorial.** La búsqueda por significado consulta una colección de Chroma (persistente, coseno, sin telemetría) en vez de multiplicar la matriz a mano. No se recalculan embeddings: `07_construir_indice.py` carga en Chroma los vectores que ya calcula (el `.npz` queda como caché de vectores y respaldo).
2. **Hit@1 y hit@3** en `10_evaluar_recuperacion.py`, además de hit@12, y la columna `posicion` en el CSV.
3. **Prueba de orden determinista**: la misma pregunta devuelve siempre los mismos fragmentos en el mismo orden.

## Criterios de aceptación
- Con Chroma, `10_evaluar_recuperacion.py --k 12` da lo mismo que con la matriz (embeddings 31 de 35); si no, se explica la diferencia antes de adoptarlo.
- Si no hay carpeta de Chroma o no coincide con los fragmentos, la búsqueda sigue funcionando con la matriz (una clonación nueva funciona antes de correr el script 07).
- Pruebas gratis: ranking de Chroma igual al de la matriz, y orden estable.
- Chroma no envía telemetría.

## Fuera de alcance
- Guardar el texto en Chroma (el texto sigue en `chunks.jsonl`, un solo lugar).
- Reordenamiento y búsqueda híbrida dentro de Chroma (el híbrido sigue combinando posiciones en código propio).
