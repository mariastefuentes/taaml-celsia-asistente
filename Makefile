# Atajos del proyecto. Uso: make          (muestra este menú)
#                                    make <objetivo>
# Todo corre con uv; nada de pip ni requirements.txt (regla del curso).
.PHONY: help ayuda setup modulo1 app test lint check format clean datos scraping-demo indice recuperacion ensayo evaluar pdf

# El primer objetivo es el que corre `make` sin argumentos: el menú de ayuda.
help: ayuda

# $(info) imprime desde make, no desde el shell: el menú se ve igual en cmd, PowerShell o sh.
ayuda:
	$(info )
	$(info   Asistente Celsia - Taller 1 (UAO))
	$(info   =================================)
	$(info )
	$(info   PREPARAR EL EQUIPO)
	$(info     make setup           uv sync + crea .env (si falta) + descarga el modelo de embeddings)
	$(info )
	$(info   EJECUTAR LA APLICACION)
	$(info     make modulo1         App del Modulo 1: solo el corpus y las etapas del scraping  [la de la sustentacion])
	$(info     make app             App completa: Q&A, Resumen, FAQ y Corpus)
	$(info )
	$(info   DATOS Y SCRAPING)
	$(info     make scraping-demo   borra la carpeta de demo y descarga 5 paginas del blog (no toca data/1_bronze ni gasta cuota))
	$(info     make datos           reconstruye silver, gold, curaduria y fragmentos (necesita el HTML de Bronze))
	$(info     make indice          construye el indice de vectores con Ollama (sube la busqueda del 54 % al 89 %))
	$(info )
	$(info   VERIFICAR ANTES DE LA DEMO)
	$(info     make ensayo          revisa que la demo este lista, sin gastar cuota)
	$(info     make test            pruebas automaticas (gratis, sin Gemini ni Ollama))
	$(info     make lint            errores de codigo con ruff y lock vigente)
	$(info     make check           lint + pruebas: lo que corre el CI; correrlo antes de subir)
	$(info     make recuperacion    mide la recuperacion de fragmentos (gratis; necesita Ollama))
	$(info )
	$(info   OTROS)
	$(info     make evaluar         corre las 59 preguntas con Gemini (GASTA CUOTA: confirmar antes))
	$(info     make pdf             regenera el PDF del informe)
	$(info     make format          da formato al codigo con ruff (cambia archivos: revisa el diff antes del commit))
	$(info     make clean           borra caches (pytest, ruff, __pycache__))
	$(info )
	@:

setup:
	uv sync
	uv run python -c "import pathlib, shutil; p = pathlib.Path('.env'); p.exists() or shutil.copy('.env.example', p); print('Listo: .env disponible (completa GOOGLE_API_KEY si esta vacio)')"
	$(info Descargando los modelos de Ollama (si ya estan, no hace nada):)
	-ollama --version
	-ollama pull nomic-embed-text-v2-moe
	-ollama pull llama3.2:3b
	$(info )
	$(info Siguiente paso: edita .env, pon tu GOOGLE_API_KEY y ejecuta 'make modulo1'.)
	$(info Sin GOOGLE_API_KEY la app usa Ollama local (llama3.2:3b) y, si tampoco responde, las respuestas guardadas.)

modulo1:
	uv run streamlit run app/modulo1.py

app:
	uv run streamlit run app/asistente.py

test:
	uv run python -m pytest

lint:
	uvx ruff@0.17.3 check --select F,E9 src tests scripts app
	uv lock --check

check: lint test

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

evaluar:
	uv run python scripts/11_evaluar_modelo.py --modelo gemini:gemini-3.5-flash

pdf:
	uv run python scripts/utilidades/md_a_pdf.py
