# Plan 002

- `src/taaml/validacion.py`: extrae cifras (2 o más dígitos), correos y enlaces de la respuesta y los busca en el texto de los fragmentos recuperados. Compara sin puntos, comas ni espacios en los números.
- `app.py`: advertencia bajo la respuesta si hay datos sin respaldo.
- `scripts/14_validar_respuestas.py`: aplica la validación a los CSV de resultados (sin llamar a modelos) y guarda el resumen.
- `src/taaml/agente.py`: herramienta `buscar_en_base` (envuelve `recuperacion.buscar`) y `crear_agente()` con `create_agent`. Dependencias nuevas: `langchain` y `langchain-ollama` (paquetes oficiales, licencia MIT, verificados en PyPI).
- `scripts/15_probar_agente.py`: pregunta de ejemplo al agente local.
- Documentación: ciclo Build, Test, Deploy, Monitor; tabla del sistema compuesto; límites (sin memoria entre turnos; el umbral de similitud ya se probó).
