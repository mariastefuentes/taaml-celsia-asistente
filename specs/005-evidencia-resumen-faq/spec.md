---
estado: cumplida
escrita: 2026-10-29
---
# Spec 005: evidencia guardada de Resumen y FAQ

Nace de una revisión de evidencias: Resumen y FAQ no tienen ninguna salida guardada, solo se probaron a mano. La usuaria autorizó 2 llamadas a `gemini-3.5-flash` («Autorizo 2 llamadas»). Se escribe **antes** de programar.

## Qué se necesita
- `scripts/17_probar_resumen_faq.py`: una llamada de Resumen y una de FAQ sobre una página oficial, por la misma ruta de LangChain que usa la app (`resumir` y `generar_faq`), y un CSV con la salida.
- Revisión sin gastar: cada cifra, correo y enlace de la salida se busca en el texto de la página (`validacion.datos_sin_respaldo`).

## Criterios de aceptación
- Exactamente 2 llamadas al modelo; si falla una no se reintenta sola.
- El CSV dice la tarea, la página, el modelo, la fecha, los segundos y los datos sin respaldo.

## Fuera de alcance
- Medir la calidad de Resumen y FAQ con un conjunto de prueba: sigue siendo una limitación declarada.
