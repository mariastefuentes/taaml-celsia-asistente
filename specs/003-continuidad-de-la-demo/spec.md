---
estado: cumplida
escrita: 2026-10-29
---
# Spec 003: que la demo no se caiga si el modelo no responde

Nace de un error real: la app mostró «Se agotó la cuota del modelo» con un solo proveedor configurado. En la sustentación esa falla no es aceptable. Se escribe **antes** de programar y la aprueba la usuaria («Haz la 2, 3 y 4»).

## Qué se necesita
1. **Respaldo automático de modelo.** Si el modelo elegido falla por cuota, límite, servidor caído o falta de clave, la app prueba el siguiente de la cadena: el elegido, `deepseek-flash` (solo si hay clave) y `ollama:llama3.2` (local, gratis, más lento y menos preciso).
2. **Respuestas guardadas.** Si ningún modelo responde, el Q&A muestra la respuesta ya generada en la evaluación (v3) para esa pregunta, marcada como guardada, con sus fuentes. No hay copia nueva de los datos: se leen el CSV de resultados y `chunks.jsonl`.
3. **Ensayo antes de la sustentación.** Un script que comprueba, sin gastar, que todo lo necesario está listo (claves presentes sin mostrarlas, Ollama, índice, respuestas guardadas) y, solo con `--llamar`, hace una llamada por proveedor para ver cuál responde. Más una lista de verificación en la guía de sustentación.

## Criterios de aceptación
- La app dice siempre qué modelo respondió y por qué se cambió; nunca presenta una respuesta guardada como si fuera nueva.
- El modelo local no se usa salvo que los demás fallen.
- Las pruebas automáticas no llaman a ningún modelo (se simulan los fallos).
- Ninguna clave se lee ni se muestra: solo se comprueba si existe.

## Fuera de alcance
- Reintentos con espera para esperar el reinicio de la cuota.
- Resumen y FAQ con respuestas guardadas (se necesitaría generarlas: gastaría cuota). Sí tienen respaldo de modelo.
- Garantizar la calidad del modelo local: es 3.000 millones de parámetros en CPU.
