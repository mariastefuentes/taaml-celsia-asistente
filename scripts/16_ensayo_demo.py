"""ENSAYO DE LA DEMO: comprueba que todo lo necesario para la sustentación está listo.

Por defecto no llama a ningún modelo (no gasta cuota): revisa que existan las claves (solo si están definidas; nunca se imprimen), que Ollama responda,
que el índice y las respuestas guardadas estén y qué cadena de modelos usaría la app si el elegido fallara.
Con `--llamar` hace UNA llamada corta por proveedor disponible (Gemini, DeepSeek y Ollama) para ver cuál responde de verdad.

Uso:  uv run python scripts/16_ensayo_demo.py [--llamar]
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from langchain_core.messages import HumanMessage  # noqa: E402

from taaml.recuperacion import INDICE, buscar  # noqa: E402
from taaml.respaldo import cadena_de_modelos, preguntas_guardadas  # noqa: E402
from taaml.tareas import MODELO_POR_DEFECTO, _tag_instalado, obtener_modelo  # noqa: E402


def marca(ok: bool) -> str:
    return "OK   " if ok else "FALTA"


def etiquetas_ollama() -> list[str]:
    """Modelos que Ollama tiene instalados; lista vacía si está apagado."""
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as r:
            return [m["name"] for m in json.loads(r.read().decode("utf-8")).get("models", [])]
    except Exception:  # noqa: BLE001
        return []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llamar", action="store_true", help="una llamada corta por proveedor (gasta cuota: hasta 3 llamadas en total)")
    a = ap.parse_args()

    print("Sin llamadas a modelos:")
    print(f"  {marca(bool(os.environ.get('GOOGLE_API_KEY')))} clave de Gemini (GOOGLE_API_KEY); sin ella responde el modelo local")
    print(f"  {marca(bool(os.environ.get('DEEPSEEK_API_KEY')))} clave de DeepSeek (DEEPSEEK_API_KEY), respaldo opcional")
    print(f"  {marca(INDICE.exists())} índice de embeddings ({INDICE.name})")
    try:
        metodo = buscar("teléfono de atención al cliente", 3)[0]["metodo"]
        print(f"  {marca(metodo == 'embeddings')} recuperación con embeddings (método usado: {metodo}; si es «palabras», Ollama no respondió)")
    except Exception as e:  # noqa: BLE001
        print(f"  FALTA recuperación: {str(e)[:100]}")
    print(f"  {marca(len(preguntas_guardadas()) > 0)} respuestas guardadas para el último recurso ({len(preguntas_guardadas())} preguntas)")
    instalados = etiquetas_ollama()
    local = cadena_de_modelos(MODELO_POR_DEFECTO)[-1]
    tag = _tag_instalado(local.removeprefix("ollama:")) if local.startswith("ollama:") else local
    print(f"  {marca(tag in instalados)} modelo local de respaldo ({tag}); si no hay clave, responde este")
    print(f"  Cadena de modelos si el elegido falla: {' -> '.join(cadena_de_modelos(MODELO_POR_DEFECTO))}")

    if not a.llamar:
        print("\nPara probar de verdad cada proveedor: uv run python scripts/16_ensayo_demo.py --llamar")
        return
    print("\nCon llamadas (una por proveedor):")
    for modelo in cadena_de_modelos(MODELO_POR_DEFECTO):
        inicio = time.time()
        try:
            texto = obtener_modelo(modelo).invoke([HumanMessage("Responde solo con la palabra: listo")]).text.strip()
            print(f"  OK    {modelo}: «{texto[:40]}» en {time.time() - inicio:.1f} s")
        except Exception as e:  # noqa: BLE001
            print(f"  FALLA {modelo}: {str(e)[:120]}")


if __name__ == "__main__":
    main()
