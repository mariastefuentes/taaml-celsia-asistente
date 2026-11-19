# Declaración de uso de IA (Módulo 3)

El curso pide declarar qué herramientas de IA se usaron, para qué y cómo se verificó el resultado. Esta sección se pega en el informe final unificado; la del Taller 2 sigue vigente para lo anterior.

| Herramienta | Para qué se usó en el Módulo 3 | Cómo se verificó |
|---|---|---|
| Claude Code (Anthropic) | Escribir y revisar código (webhook de WhatsApp, aprobación humana, límite de mensajes, análisis de conversaciones), pruebas y documentos del repositorio | Cada cambio sale por pull request y una persona del equipo debe revisarlo y poder explicarlo; las pruebas automáticas y el linter corren antes de fusionar; las cifras se recalculan con los scripts del repositorio |
| DeepSeek por API | Modelo del agente en producción | Matriz de enrutamiento (32 de 33), 7 de 8 preguntas de energía con búsqueda, 10 de 10 preguntas ajenas rechazadas, 6 de 6 respuestas honestas con una herramienta caída |
| `nomic-embed-text-v2-moe` (Ollama, local) | Embeddings de los fragmentos, de las preguntas y de las conversaciones del análisis t-SNE | Medido con hit@k, precisión, recall y nDCG; el análisis de conversaciones se explica con sus límites |
| `llama3.2` (Ollama, local) | Respaldo si falla el modelo principal | Probado con pocos casos; no se midió más |
| LangSmith | Trazas de cada turno (pasos, herramientas, tiempos y tokens) | Se compara la traza con lo que respondió el agente |

**Límites que se declaran.** Las 114 conversaciones del análisis t-SNE son simuladas; las generó un script con preguntas de ejemplo que respondió el agente real, no son clientes reales. El webhook se probó con avisos firmados simulados; la prueba con la API Cloud de Meta real está pendiente hasta el ensayo.

Todo código o texto generado por una herramienta lo revisa una persona del equipo, que debe poder explicarlo en vivo.
