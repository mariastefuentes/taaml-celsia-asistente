# RAG Chain (Taller 1) frente a RAG Agent (Taller 2)

Medido el 2026-11-09. Las cifras del chain salen de `resultados_gemini-gemini-3.5-flash_rag_v5.csv` (59 preguntas); las del agente, de `scripts/18_ensayo_agente.py` (conversación de 4 turnos con `gemini-3.8-flash`).

| | Chain (Q&A del Taller 1) | Agente (Taller 2) |
|---|---|---|
| Modelo | gemini-3.5-flash | gemini-3.8-flash |
| ¿Quién decide buscar? | Siempre busca (2 pasos fijos) | El modelo decide con herramientas |
| Fragmentos al modelo | 12 por pregunta | 4 por búsqueda |
| Tokens de entrada por pregunta | 4.615 de media (59 preguntas) | 2.238 a 8.554 según el turno |
| Tokens de salida | 101 de media | 133 a 584 (incluye el razonamiento del modelo) |
| Tiempo por pregunta | 7,2 s de media | no medido en esta corrida (el script ya lo registra) |
| Costo por pregunta | sin precio oficial para gemini-3.5-flash | 0,0022 a 0,0075 USD; 0,0209 USD la conversación de 4 turnos |

## Turnos del agente

| Turno | Pregunta | Herramienta | Entrada | Salida | Costo USD |
|---|---|---|---|---|---|
| 1 | ¿Qué sedes hay en Ibagué? | consultar_datos | no capturado | no capturado | 0,00455 (por diferencia) |
| 2 | ¿Y cuál es el teléfono de la sede administrativa? | ninguna (memoria) | 2.238 | 133 | 0,00218 |
| 3 | ¿Cómo cancelo mi servicio? | buscar_en_base | 6.075 | 584 | 0,00675 |
| 4 | ¿Cuánto cuesta un viaje a Cartagena? | buscar_en_base | 8.554 | 277 | 0,00745 |

Resultado: 4 de 4 correctas.

## Cómo leerlo

- El turno 2 muestra la ventaja del agente: respondió desde la memoria sin buscar, con el menor costo. Un chain habría vuelto a buscar.
- La entrada crece con la conversación (el historial se reenvía en cada turno): de 2.238 a 8.554 tokens. Por eso se recorta lo que ve el modelo a unos 3.000 tokens de historial.
- Los modelos son distintos, así que la comparación de tokens es orientativa; no es un experimento controlado.
- El costo del turno 1 se obtuvo restando los otros tres del total, porque la salida de esa corrida mostraba solo los últimos turnos.
