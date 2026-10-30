# Comparación de modelos con el conjunto de prueba

Generado automáticamente por `scripts/11_evaluar_modelo.py --resumen`. Cada fila es una corrida; la calificación la da un modelo juez comparando con la respuesta esperada, así que es una **ayuda para revisar**, no un veredicto: conviene que una persona revise las respuestas.

| Modelo | Base | Prompt | Preguntas | Correctas | Parciales | Incorrectas | Reconoce que no sabe | Inventa | Sin calificar | Tiempo mediano (s) | Tokens de entrada (media) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| deepseek:deepseek-flash | rag | v3 | 59 | 30 | 4 | 1 | 20 | 4 | 0 | 4 | 4,484 |
| gemini:gemini-3.5-flash | completa | v3 | 5 | 3 | 0 | 0 | 2 | 0 | 0 | 8 | 340,990 |
| gemini:gemini-3.5-flash | rag | v1 | 59 | 33 | 1 | 1 | 21 | 3 | 0 | 7 | 4,023 |
| gemini:gemini-3.5-flash | rag | v2 | 59 | 30 | 3 | 2 | 20 | 4 | 0 | 7 | 4,262 |
| gemini:gemini-3.5-flash | rag | v3 | 59 | 31 | 4 | 0 | 21 | 3 | 0 | 8 | 4,368 |
| gemini:gemini-3.5-flash | rag | v4 | 59 | 31 | 4 | 0 | 20 | 4 | 0 | 8 | 4,661 |
| gemini:gemini-3.5-flash | rag | v5 | 59 | 31 | 4 | 0 | 20 | 4 | 0 | 7 | 4,614 |
| gemini:gemini-3.5-flash | rag-repetido | v3 | 59 | 29 | 6 | 0 | 21 | 3 | 0 | 8 | 4,470 |

«Correctas», «parciales» e «incorrectas» se cuentan sobre las preguntas de respuesta; «reconoce que no sabe» e «inventa», sobre las negativas. «Sin calificar» incluye las preguntas que fallaron por errores de conexión o por el límite de uso de la API (se pueden repetir). El tiempo es la **mediana** de las respuestas sin error: en las corridas por API todavía puede incluir esperas por el límite de uso.
