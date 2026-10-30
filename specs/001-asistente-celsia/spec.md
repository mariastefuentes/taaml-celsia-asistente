---
estado: retroactiva
escrita: 2026-10-28
---
# Spec 001: asistente de atención a clientes de Celsia

> **Aviso de honestidad.** Esta especificación se escribió el 28/10/2026, **después** de construir el asistente, para dejar la especificación versionada como evidencia de diseño. No guió el desarrollo. Desde el próximo cambio, la spec se escribe **antes** (carpeta `specs/00N-nombre/`) y el plan y las tareas se aprueban antes de tocar código.

## Qué se necesita
Un asistente que atienda a personas que escriben por primera vez a Celsia (empresa de energía del Valle del Cauca y el Tolima) y a clientes actuales, con información tomada solo del contenido público y oficial de celsia.com.

## Alcance
- Tres tareas con LangChain: **Resumen** de una página, **FAQ** a partir de una página y **Q&A** con fuentes.
- Aplicación Streamlit para usarlas.
- Conjunto de prueba de al menos 20 preguntas, informe de 5 secciones con declaración de uso de IA y sustentación en vivo (12 min de demostración y 3 de preguntas).

## Fuera de alcance
Datos de clientes (facturas, consumos, estado de solicitudes), PDF bloqueados por `robots.txt`, redes sociales y fuentes de terceros.

## Criterios de aceptación (medibles)
| # | Criterio | Cómo se verifica | Resultado |
|---|---|---|---|
| 1 | Responde con datos concretos y cita las fuentes | Revisión manual de 35 preguntas de respuesta | 29 sí y 6 parciales (revisión manual); 31 correctas del juez |
| 2 | No inventa cuando la base no tiene el dato | 24 preguntas negativas | 19 sí, 4 parciales y 1 no (revisión manual); 21 del juez |
| 3 | Rechaza instrucciones maliciosas | 4 de inyección directa, 3 de jailbreaks adicionales y 4 de indirecta | 4 de 4, 3 de 3 y 4 de 4 |
| 4 | La búsqueda encuentra el fragmento correcto | `scripts/10_evaluar_recuperacion.py` | 31 de 35 con 12 fragmentos (89 %) |
| 5 | `temperature 0.0`, `top_p 0.1`, solo `uv` | Código, `AGENTS.md` y las pruebas de `make test` | Cumplido con Gemini; DeepSeek no admite `top_p` |
| 6 | Nada sale sin revisión | GGA en cada commit | Activo |

La evidencia completa está en `docs/3 - Informe/informe_taller1.md`; esta spec no la repite.
