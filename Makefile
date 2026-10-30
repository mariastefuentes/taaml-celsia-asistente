# Atajos del proyecto. Uso: make <objetivo>   (make sin objetivo muestra la ayuda)
# Todo corre con uv; nada de pip ni requirements.txt (regla del curso).
.PHONY: ayuda test lint datos scraping-demo indice recuperacion evaluar app

ayuda:
	@echo "make test         pruebas de componentes (gratis, sin Gemini ni Ollama)"
	@echo "make lint         revision de errores del codigo con ruff"
	@echo "make datos        reconstruye silver, gold, curaduria y fragmentos (no vuelve a descargar el sitio ni necesita Ollama)"
	@echo "make scraping-demo descarga 5 paginas de celsia.com para ver el scraper en vivo (no toca data/1_bronze)"
	@echo "make indice       construye el indice de vectores (Chroma) a partir de los fragmentos; necesita Ollama"
	@echo "make recuperacion mide la recuperacion de fragmentos (gratis; necesita Ollama encendido)"
	@echo "make evaluar      corre las 59 preguntas con Gemini (GASTA CUOTA O SALDO: confirmar antes)"
	@echo "make app          abre la aplicacion Streamlit (necesita Ollama y GOOGLE_API_KEY en .env)"

test:
	uv run python -m pytest

lint:
	uvx ruff@0.17.3 check --select F,E9 src tests scripts app.py
	uv lock --check

datos:
	uv run python scripts/03_construir_silver.py
	uv run python scripts/04_construir_gold.py
	uv run python scripts/05_curar_base.py
	uv run python scripts/06_construir_chunks.py

scraping-demo:
	uv run python scripts/01_scrape_celsia.py --sections page --limit 5 --salida data/_demo_scraping

indice:
	uv run python scripts/07_construir_indice.py

recuperacion:
	uv run python scripts/10_evaluar_recuperacion.py --k 12

evaluar:
	uv run python scripts/11_evaluar_modelo.py --modelo gemini:gemini-3.5-flash

app:
	uv run streamlit run app.py
