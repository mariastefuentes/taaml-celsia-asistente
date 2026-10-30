# Plan 001: cómo se construyó

Los detalles y las cifras están en `docs/3 - Informe/informe_taller1.md`. Aquí solo van las decisiones y por qué.

## Arquitectura
Scraping respetuoso → capas Bronze, Silver y Gold (Medallion) → curaduría (393 documentos) → fragmentos de 1.000 caracteres con solape de 150 → embeddings locales → búsqueda de 12 fragmentos → Gemini responde con el prompt v3 → app Streamlit.

## Decisiones y alternativas descartadas
| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| RAG con 12 fragmentos | Pegar toda la base (~316.800 tokens) en el prompt | Costo, latencia y el efecto *Lost in the Middle* (Liu 2023); se compara en el informe |
| Embeddings `nomic-embed-text-v2-moe` en Ollama, con diccionario de sinónimos | Búsqueda por palabras (54 %) o híbrida (74 %) | 89 % de aciertos con 12 fragmentos |
| `gemini-3.5-flash` con `temperature 0.0` y `top_p 0.1` | `gemini-3.6-flash` (ignora ambos parámetros) y DeepSeek (deja `top_p` fijo en 1,0) | Cumple la regla del proyecto; DeepSeek quedó casi empatado y se conserva como opción |
| Prompt v3 de cinco bloques con la pregunta entre etiquetas | v1, v2, v4 y v5 (con ejemplos) | v3 es el vigente; v5 no mejoró |
| Reordenar fragmentos y LangSmith como opciones apagadas | Activarlos siempre | El reordenamiento no mejoró (31 de 35) y LangSmith envía datos a un tercero |
| Juez distinto del modelo que responde, más revisión manual | Solo juez automático | Coinciden en 55 de 59, pero no son evidencia independiente |

## Riesgos conocidos
La revisión manual fue propuesta por el asistente de código y ratificada por María Stella Fuentes; el juez de DeepSeek no es el mismo que el de Gemini; sin entrevista del gerente ni PDF.
