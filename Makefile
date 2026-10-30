# Atajos del proyecto. Uso: make <objetivo>   (make sin objetivo muestra la ayuda)
# Todo corre con uv; nada de pip ni requirements.txt (regla del curso).
.PHONY: ayuda test lint datos scraping-demo

ayuda:
	@echo "make test         pruebas de componentes (gratis, sin Gemini ni Ollama)"
	@echo "make lint         revision de errores del codigo con ruff"
	@echo "make datos        reconstruye silver, gold, curaduria y fragmentos (no vuelve a descargar el sitio ni necesita Ollama)"
	@echo "make scraping-demo descarga 5 paginas de celsia.com para ver el scraper en vivo (no toca data/1_bronze)"

test:
	uv run python -m pytest

lint:
	uvx ruff@0.17.3 check --select F,E9 tests scripts
	uv lock --check

datos:
	uv run python scripts/03_construir_silver.py
	uv run python scripts/04_construir_gold.py
	uv run python scripts/05_curar_base.py
	uv run python scripts/06_construir_chunks.py

scraping-demo:
	uv run python scripts/01_scrape_celsia.py --sections page --limit 5 --salida data/_demo_scraping
