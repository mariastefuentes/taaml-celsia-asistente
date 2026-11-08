# Plan 011

- `src/taaml/consulta_datos.py`: carga sedes, contactos y catálogo y ofrece filtros puros (municipio, trámite, sección). Sin LangChain, para probarlo sin modelos.
- `src/taaml/agente.py`: herramienta `consultar_datos` junto a `buscar_en_base`; `crear_agente()` recibe un `InMemorySaver`; `preguntar()` recibe `thread_id`. Modelo por defecto `gemini-3.8-flash`, con respaldo local.
- `prompts/v2_agente.md`: reglas del router (cuándo datos, cuándo texto) y de memoria. El prompt v1 se conserva.
- `scripts/18_ensayo_agente.py`: conversación de cuatro preguntas con Gemini (gasta cuota; se confirma antes). `scripts/15_probar_agente.py` sigue para preguntas sueltas.
- `app/asistente.py`: pestaña «Agente».
- Documentación: README, constitución (decisión del modelo), informe y PDF al día.
