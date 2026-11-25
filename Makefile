# Atajos del proyecto. Uso: make          (muestra este menú)
#                                    make <objetivo>
# Todo corre con uv; nada de pip ni requirements.txt (regla del curso).
.PHONY: help ayuda setup modulo1 app app-taller1 api api-cadena api-sqlite db-up db-down frontend chat-web qr-chat-web qr-whatsapp demo-inyeccion demo-limpiar demo-plan-b exportar-chats ensayo-whatsapp preguntas-hostiles informe-borrador herramienta-caida banco-verificable verificar-clon test lint tipos skills-check check format clean datos scraping-demo indice recuperacion ensayo ensayo-agente evaluar pdf mcp openclaw-check openclaw-instalar

# El primer objetivo es el que corre `make` sin argumentos: el menú de ayuda.
help: ayuda

# $(info) imprime desde make, no desde el shell: el menú se ve igual en cmd, PowerShell o sh.
ayuda:
	$(info )
	$(info   Asistente Celsia - Taller 1 y Modulos 2 y 3 (UAO))
	$(info   ===========================================)
	$(info )
	$(info   PREPARAR EL EQUIPO)
	$(info     make setup           uv sync + crea .env (si falta) + descarga el modelo de embeddings)
	$(info )
	$(info   EJECUTAR LA APLICACION)
	$(info     make modulo1         App del Modulo 1: solo el corpus y las etapas del scraping)
	$(info     make api             MODULOS 2 Y 3: API FastAPI del agente con memoria en PostgreSQL, en http://127.0.0.1:8000)
	$(info     make api-cadena      la misma API con RAG en cadena (dynamic_prompt) en vez del agentico; para mostrarlo en la sustentacion)
	$(info     make api-sqlite      la misma API con la memoria en archivos SQLite)
	$(info     make db-up           levanta solo el PostgreSQL local (make db-down lo apaga))
	$(info     make app             MODULO 2: frontend React, en http://localhost:5173 (igual que make frontend))
	$(info     make frontend        instala las dependencias del frontend si faltan y lo enciende)
	$(info     make app-taller1     Taller 1 (Streamlit): Q&A, Resumen, FAQ y Corpus  [historico])
	$(info     make demo-inyeccion  MODULO 2: API con un corpus de demo que trae un documento envenenado (apaga antes la API normal))
	$(info )
	$(info   DATOS Y SCRAPING)
	$(info     make scraping-demo   borra la carpeta de demo y descarga 5 paginas del blog (no toca data/1_bronze ni gasta cuota))
	$(info     make datos           reconstruye silver, gold, curaduria y fragmentos (necesita el HTML de Bronze))
	$(info     make indice          construye el indice de vectores con embeddings de Gemini (en la nube; sube la busqueda del 51 % al 83 %))
	$(info )
	$(info   VERIFICAR ANTES DE LA DEMO)
	$(info     make demo-limpiar    borra la memoria de largo plazo de los ensayos (antes de la demo))
	$(info     make demo-plan-b     plan B: repite en pantalla una conversacion real grabada (por si Meta falla))
	$(info     make exportar-chats  exporta los chats reales de los ensayos para el analisis t-SNE)
	$(info     make ensayo          revisa que la demo este lista, sin gastar cuota)
	$(info     make ensayo-whatsapp chequeo previo de WhatsApp: claves, token de Meta, API y panel (gratis; con ARGS="--tunel URL" prueba el tunel))
	$(info     make qr-whatsapp   QR de WhatsApp del bot para el auditorio: make qr-whatsapp ARGS="+57... --html")
	$(info     make preguntas-hostiles  12 preguntas incomodas tipo profesor al agente real (GASTA CUOTA: unas 15 a 25 llamadas))
	$(info     make herramienta-caida   rompe herramientas a proposito con el modelo real y mira que el agente avise sin inventar (GASTA CUOTA: unas 4 a 8 llamadas))
	$(info     make informe-borrador    genera docs/3 - Informe/borrador_informe_final.md con los datos del repo (gratis))
	$(info     make ensayo-agente   conversacion de 4 turnos con el agente real (GASTA CUOTA: 8 a 12 llamadas al modelo))
	$(info     make test            pruebas automaticas (gratis, sin Gemini))
	$(info     make lint            errores de codigo con ruff y lock vigente)
	$(info     make skills-check    valida las skills de .opencode/skills (gratis))
	$(info     make check           lint + pruebas + skills: lo que corre el CI; correrlo antes de subir)
	$(info     make recuperacion    mide la recuperacion de fragmentos (necesita GOOGLE_API_KEY para los embeddings))
	$(info )
	$(info   OTROS)
	$(info     make evaluar         corre las 59 preguntas con Gemini (GASTA CUOTA: confirmar antes))
	$(info     make pdf             regenera el PDF del informe)
	$(info     make format          da formato al codigo con ruff (cambia archivos: revisa el diff antes del commit))
	$(info     make clean           borra caches (pytest, ruff, __pycache__))
	$(info )
	@:

setup:
	uv sync --all-groups
	uv run python -c "import pathlib, shutil; p = pathlib.Path('.env'); p.exists() or shutil.copy('.env.example', p); print('Listo: .env disponible (completa GOOGLE_API_KEY si esta vacio)')"
	$(info )
	$(info Siguiente paso: edita .env, pon tu GOOGLE_API_KEY y ejecuta 'make modulo1'.)
	$(info Sin GOOGLE_API_KEY ni DEEPSEEK_API_KEY la app muestra las respuestas guardadas. No se usan modelos locales.)

modulo1:
	uv run streamlit run app/modulo1.py

# La entrega vigente del Modulo 2 es el frontend React; la app Streamlit del Taller 1 queda como historica.
app: frontend

app-taller1:
	uv run streamlit run app/asistente.py

# Variable portátil: en PowerShell y cmd de Windows no se puede asignar variables de entorno con
# `VAR=val cmd`; los recetas de la API asignan las variables dentro del mismo proceso que arranca
# uvicorn (os.environ + uvicorn.run), así funciona igual en Linux/WSL, PowerShell y cmd.
API_DATABASE_URL = $(shell uv run python scripts/34_postgres_local.py)

# La API usa PostgreSQL (PostgresSaver y PostgresStore): si DATABASE_URL ya está definida la respeta; si no, levanta un PostgreSQL local sin Docker.
api:
	uv run python -c "import os; os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL') or '$(API_DATABASE_URL)'.strip(); from uvicorn import run; run('api.main:app', port=8000)"

# La API con RAG EN CADENA: un dynamic_prompt inyecta los fragmentos recuperados en cada turno y se quita la herramienta buscar_en_base (D12).
api-cadena:
	uv run python -c "import os; os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL') or '$(API_DATABASE_URL)'.strip(); os.environ['RAG_MODO'] = 'cadena'; from uvicorn import run; run('api.main:app', port=8000)"

# La misma API con la memoria en archivos SQLite (sin servidor de base de datos).
api-sqlite:
	uv run python -c "import os; os.environ['DATABASE_URL'] = ''; from uvicorn import run; run('api.main:app', port=8000)"

frontend:
	cd frontend && npm install && npm run dev

# Compila el chat web para que la API lo sirva en «/» (respaldo de WhatsApp para el público); luego `make api` y `make qr-chat-web ARGS="https://..."`.
chat-web:
	cd frontend && npm install && npm run build

qr-chat-web:
	uv run python scripts/44_qr_chat_web.py $(ARGS)

# QR de WhatsApp del número vinculado al bot: el auditorio lo escanea y cae en el chat (no es el chat web).
qr-whatsapp:
	uv run python scripts/48_qr_whatsapp.py $(ARGS)

db-up:
	uv run python scripts/34_postgres_local.py

db-down:
	uv run python scripts/34_postgres_local.py --detener

# Limpia la memoria de la misma base que usa `make api` (PostgreSQL local, o el de DATABASE_URL si está definida).
demo-limpiar:
	uv run python -c "import os, sys, subprocess; os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL') or '$(API_DATABASE_URL)'.strip(); subprocess.run([sys.executable, 'scripts/30_limpiar_memoria_demo.py', '--borrar'])"

# Plan B de la demostración: repite en pantalla una conversación real grabada (avisa que es una repetición).
demo-plan-b:
	uv run python scripts/37_demo_plan_b.py

# Exporta los chats reales de los ensayos (de la base que usa `make api`) para el análisis t-SNE.
exportar-chats:
	uv run python -c "import os, sys, subprocess; os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL') or '$(API_DATABASE_URL)'.strip(); subprocess.run([sys.executable, 'scripts/38_exportar_conversaciones_reales.py'] + [x for x in '$(ARGS)'.split() if x])"

# Chequeo previo de la demo por WhatsApp (no llama al modelo). Ejemplo: make ensayo-whatsapp ARGS="--tunel https://algo.trycloudflare.com"
# Con el canal de OpenClaw como vía pública: make ensayo-whatsapp ARGS="--openclaw"
ensayo-whatsapp:
	uv run python scripts/39_chequeo_whatsapp.py $(ARGS)

# Preguntas incomodas tipo profesor (gasta cuota). Ejemplo: make preguntas-hostiles ARGS="cargador"
preguntas-hostiles:
	uv run python scripts/40_preguntas_hostiles.py $(ARGS)

# Banco verificable: respuestas esperadas calculadas desde los datos (datos, trampas, robustez, aislamiento, conversación larga). Gasta cuota.
banco-verificable:
	uv run python scripts/43_banco_verificable.py $(ARGS)

# Clona el repositorio de GitHub en una carpeta vacía y comprueba que instala, pasa lint y pruebas, y que el README cita comandos que existen. No gasta cuota; tarda unos minutos.
verificar-clon:
	uv run python scripts/45_verificar_clon.py $(ARGS)

# Herramientas que fallan de verdad con el modelo real (gasta cuota).
herramienta-caida:
	uv run python scripts/42_herramienta_caida.py

# Borrador del informe final con los datos que ya estan en el repo (sin red ni modelo).
informe-borrador:
	uv run python scripts/41_borrador_informe.py

demo-inyeccion:
	uv run python scripts/23_demo_corpus_envenenado.py --servir

test:
	uv run --group analisis python -m pytest

lint:
	uvx ruff@0.17.3 check --select F,E9 src tests scripts app
	uv lock --check

# Valida frontmatter, nombre, tamaño y seguridad de las skills; no las ejecuta.
skills-check:
	uv run python scripts/verificar_skills.py

# Revisión de tipos con ty (Astral). Informa, no bloquea: hoy da 8 avisos, casi todos de tipos de LangChain.
tipos:
	-uvx ty check --python .venv src

# Servidor MCP propio (solo lectura, por stdio): lo lanza el cliente MCP; a mano sirve para ver que arranca.
mcp:
	uv run python -m taaml.servidor_mcp

# Configuracion versionada de OpenClaw: --simular solo valida; sin argumentos valida y escribe ~/.openclaw.
openclaw-check:
	uv run python scripts/47_openclaw_instalar.py --simular

openclaw-instalar:
	uv run python scripts/47_openclaw_instalar.py $(ARGS)

check: lint test skills-check

format:
	uvx ruff@0.17.3 format src tests scripts app

clean:
	@uv run python -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for pat in ('.pytest_cache', '.ruff_cache', '**/__pycache__') for p in pathlib.Path('.').glob(pat) if '.venv' not in p.parts]"

datos:
	uv run python scripts/03_construir_silver.py
	uv run python scripts/04_construir_gold.py
	uv run python scripts/05_curar_base.py
	uv run python scripts/06_construir_chunks.py
	uv run python scripts/08_inventario_intenciones.py
	uv run python scripts/09_conjunto_de_prueba.py

scraping-demo:
	@uv run python -c "import pathlib, shutil; shutil.rmtree(pathlib.Path('data/_demo_scraping'), ignore_errors=True)"
	uv run python scripts/01_scrape_celsia.py --sections blog-celsia --limit 5 --salida data/_demo_scraping

indice:
	uv run python scripts/07_construir_indice.py

recuperacion:
	uv run python scripts/10_evaluar_recuperacion.py --k 12

ensayo:
	uv run python scripts/16_ensayo_demo.py

# Prueba real del agente: memoria, router y modelo. Gasta cuota (una conversacion de 4 turnos).
ensayo-agente:
	uv run python scripts/18_ensayo_agente.py

evaluar:
	uv run python scripts/11_evaluar_modelo.py --modelo gemini:gemini-3.5-flash

pdf:
	uv run python scripts/utilidades/md_a_pdf.py
