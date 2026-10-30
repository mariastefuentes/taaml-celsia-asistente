---
estado: cumplida
escrita: 2026-10-28
---
# Spec 002: post-validación de respuestas y agente con herramienta

Nace de revisar el material del curso sobre post-validación de respuestas y agentes con herramientas. Se escribe **antes** de programar.

## Qué se necesita
1. **Post-validación.** Que cada cifra, teléfono, correo y enlace de una respuesta pueda rastrearse hasta un fragmento recuperado. Lo que no aparezca se marca como «sin respaldo».
2. **Agente con herramienta.** Un agente `create_agent` de LangChain 1.x con una herramienta que consulta la base de Celsia, para probar el patrón que usará el Taller 2.

## Criterios de aceptación
- La validación no llama a ningún modelo y no cambia el texto de la respuesta: solo avisa.
- Se mide sobre las respuestas ya guardadas del conjunto de prueba, sin gastar cuota.
- La app muestra un aviso cuando hay datos sin respaldo.
- El agente corre con un modelo local (Ollama) y reutiliza la misma recuperación que el Q&A.
- Pruebas automáticas gratis para la validación y la herramienta.

## Fuera de alcance
- Memoria entre turnos (checkpointers) y LangGraph: el Taller 1 responde un turno a la vez.
- Corregir la respuesta automáticamente.
