---
estado: cumplida
escrita: 2026-11-13
---
# Spec 012: Qdrant como base vectorial del RAG

Nace de la auditoría del caso 1 de la sustentación del Módulo 2: «el agente busca en Qdrant sobre el corpus del M1». Reemplaza a la spec 004 (Chroma) en el motor de vectores; el resto de esa spec (hit@1, hit@3 y orden determinista) sigue vigente.

## Qué se necesita
1. **Qdrant como base vectorial.** La búsqueda por significado consulta una colección de Qdrant en modo local (archivos en `data/4_curaduria/qdrant`, sin servidor, similitud del coseno). No se recalculan embeddings: se cargan los del `.npz`.
2. **Sin Chroma.** Se quita `chromadb` de las dependencias: una sola base vectorial, sin duplicados.
3. **Mismo resultado.** La recuperación no cambia: `10_evaluar_recuperacion.py --k 12` da 31 de 35 con embeddings, igual que antes.
4. **Respaldo intacto.** Si la carpeta de Qdrant no existe, no corresponde a los fragmentos actuales o la tiene abierta otro proceso (el modo local la bloquea), se busca en la matriz del `.npz` con el mismo resultado.

## Cómo se comprueba
- `tests/test_recuperacion_qdrant.py`: el ranking de Qdrant coincide con el de la matriz, las similitudes coinciden (tolerancia 1e-3) y reconstruir reemplaza la colección en vez de duplicarla.
- Auditoría de dependencias: sin avisos de `chromadb` (de 62 avisos en 5 paquetes a 44 en 3).

## Lo que se aprendió
- El modo local de Qdrant devuelve los puntos de antes si se borra y recrea una colección dentro del mismo proceso: `construir_qdrant` vacía la colección recién creada para que reindexar reemplace de verdad.
- Apaga la API antes de correr `07_construir_indice.py`: el modo local bloquea la carpeta.

## Fuera de alcance
- Un servidor Qdrant (Docker) con índice HNSW: para 1.690 fragmentos la búsqueda exacta en modo local alcanza.
