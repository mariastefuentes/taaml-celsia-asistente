# AGENTS.md: directrices para agentes de código

Este archivo lo leen los agentes (OpenCode, Claude Code u otros) y los validadores de commit (GGA). Dice cómo trabajar en este repositorio.

La **verdad central** del proyecto (propósito, alcance, stack, estructura, convenciones y decisiones) está en [`.specify/memory/constitution.md`](.specify/memory/constitution.md). Este archivo es el resumen operativo; si hay contradicción, manda la constitución y se actualiza con el mismo commit.

## Qué es este proyecto
Base de conocimiento y asistente de preguntas y respuestas (Q&A) de **Celsia**, empresa de energía del Valle del Cauca y el Tolima. Es el Taller 1 del curso *Técnicas avanzadas de IA aplicadas en modelos de lenguaje* (UAO). La evaluación es **acumulativa**: el Taller 2 parte de este repositorio, así que debe quedar ordenado y reutilizable.

## Reglas inquebrantables
1. **Solo `uv`.** Nada de `pip`, `requirements.txt` ni `conda`. Las dependencias entran con `uv add` y el entorno se reproduce con `uv sync --locked`.
2. **Nunca leer, imprimir ni copiar el archivo `.env`** ni pegar claves en el código, los logs o los mensajes. Las claves se leen con `python-dotenv` desde el entorno. El `.env` no se sube a Git.
3. **No instalar paquetes sin aprobación humana.** Antes de proponer una dependencia, verificar que el nombre exista en PyPI y tenga historial (riesgo de «slopsquatting»). Trabajar en modo **plan** antes de **build**.
4. **No inventar datos de la empresa.** Toda cifra, teléfono, dirección, plazo o precio debe salir de `data/4_curaduria/` con su fuente. Si no está, se dice que no está.
5. **Respetar el sitio de origen:** `robots.txt`, User-Agent propio, timeout y pausa entre peticiones. No se descargan los PDF de celsia.com (su `robots.txt` los bloquea).
6. **No guardar datos personales** de clientes o terceros (Ley 1581 de Habeas Data). Solo datos públicos de la empresa. Excepción consciente: los correos de contacto de trabajo y la cuenta bancaria de Celsia que la empresa publica en su sitio (por ejemplo en inversionistas) se conservan porque son datos públicos de la organización, no de clientes.

## Estructura y qué se puede tocar
- `scripts/`: etapas del pipeline y utilidades (se pueden editar).
- `data/1_bronze/` y `data/2_silver/`, `data/3_gold/`: **se generan con los scripts; no se editan a mano.** Si algo está mal, se corrige el script y se vuelve a ejecutar.
- `data/0_manual/`: único lugar de datos escritos a mano, siempre con su fuente.
- `data/4_curaduria/`: base de conocimiento final y fragmentos (se regeneran con `05_curar_base.py` y `06_construir_chunks.py`).
- `src/taaml/`: código del asistente (`base.py` lee la base, `recuperacion.py` busca los fragmentos relevantes a cada pregunta, `reordenar.py` (opcional) elige los mejores de 30 candidatos con un modelo, `respaldo.py` prueba otro modelo si el elegido falla por cuota o conexión y, si ninguno responde, muestra la respuesta guardada de la evaluación; `validacion.py` marca las cifras, correos y enlaces de una respuesta que no están en sus fuentes, `agente.py` es el agente con herramienta (Ollama), `sinonimos.py` es el diccionario hecho a mano que acerca el lenguaje del cliente al del sitio (si se edita, ejecutar `07_construir_indice.py`), `prompts.py` arma los prompts, `tareas.py` define Q&A, resumen y FAQ). `app.py`: aplicación Streamlit. `prompts/`: prompts versionados (asistente: `v1` y `v2` reemplazados, `v3_asistente.md` vigente; `v3_recordatorio.md` va después de la pregunta; resumen y FAQ: `v2`). Un cambio de prompt es una versión nueva, no una edición de la anterior; se evalúa con `--prompt vN`.
- Los documentos del taller (`.md`: análisis, conjunto de prueba e informe) están en `docs/`. Solo el informe tiene PDF, que se regenera con `make pdf`.

## Cómo trabajar
- Orden del pipeline: `01_scrape_celsia.py` → `03_construir_silver.py` → `04_construir_gold.py` → `05_curar_base.py` → `06_construir_chunks.py` → `07_construir_indice.py` (embeddings y carga en Chroma; necesita Ollama) → `08_inventario_intenciones.py` → `09_conjunto_de_prueba.py`; `02_obtener_sedes.py` agrega las sedes. Ver `README.md`.
- Después de cambiar la curaduría o el alcance, ejecutar `08_inventario_intenciones.py` y `09_conjunto_de_prueba.py`: comprueban que las preguntas siguen teniendo respaldo.
- Para el modelo: `temperature = 0.0` y `top_p = 0.1` en RAG y agentes (regla del proyecto). El prompt tiene cinco bloques (rol, contexto, instrucción, formato, restricciones) y la entrada del usuario va delimitada con etiquetas XML.
- La base completa (~316.600 tokens) no se pega entera en el prompt: Q&A recupera los 12 fragmentos más relevantes (`--base rag`, por defecto). La calidad de la recuperación se mide sin gastar cuota con `scripts/10_evaluar_recuperacion.py`. Si cambia la base o el chunking, hay que volver a ejecutar `07_construir_indice.py`.
- Evaluar con `scripts/11_evaluar_modelo.py` y el conjunto de prueba. La calificación del modelo juez es una ayuda: una persona revisa las respuestas.
- Escribir en **español**, con comentarios breves y útiles. Nombres de variables y funciones claros. Los textos para personas (documentos, mensajes de la app, prompts) y el código de `src/` y `app.py` llevan tildes. En los comentarios y docstrings de `scripts/` las tildes son **opcionales** (hay archivos con y sin ellas; ni una cosa ni la otra es una falta). Los nombres de constantes, variables y archivos nunca llevan tildes.
- Los datos de `DATOS_CLAVE` en `06_construir_chunks.py` son los valores que la verificación espera encontrar en la base (no se usan para responder); si cambian los datos oficiales, se actualizan junto con `data/0_manual/`.

## Antes de cada commit
- No incluir `.env`, `.venv/` ni claves. Revisar `git status`.
- Correr `make test` (pruebas automáticas, gratis) y `make lint`.
- Si se agregó una dependencia, `uv.lock` debe ir en el mismo commit.
- Actualizar el documento afectado (bitácora o análisis) con la decisión tomada, y, si es el informe, regenerar su PDF.
- Mensajes de commit semánticos y en español: `feat:`, `fix:`, `docs:`, `test:`, `refactor:` o `chore:`, seguido de una frase descriptiva. Las decisiones importantes también se registran en Engram (`engram save ... --project taaml-celsia`).
- Los cambios nuevos llevan antes una spec en `specs/00N-nombre/` (spec, plan y tareas) que se aprueba antes de programar. La `001` es retroactiva y lo dice.

## Transparencia sobre el uso de IA
El curso exige declarar qué herramientas de IA se usaron, para qué y cómo se verificó el resultado. Todo código o texto generado por un agente se revisa por una persona del equipo, que debe poder explicarlo en vivo.
