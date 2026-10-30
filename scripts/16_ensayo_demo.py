"""ENSAYO DE LA DEMO: comprueba que todo lo necesario para la sustentación está listo.

Por defecto no llama a ningún modelo (no gasta cuota): revisa que existan las claves (solo si están definidas; nunca se imprimen), que Ollama responda,
que el índice y las respuestas guardadas estén y qué cadena de modelos usaría la app si el elegido fallara.
Con `--llamar` hace UNA llamada corta por proveedor disponible (Gemini, DeepSeek y Ollama) para ver cuál responde de verdad.

Uso:  uv run python scripts/16_ensayo_demo.py [--llamar]
"""
import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from langchain_core.messages import HumanMessage  # noqa: E402

from taaml.recuperacion import INDICE, buscar  # noqa: E402
from taaml.respaldo import cadena_de_modelos, preguntas_guardadas  # noqa: E402
from taaml.tareas import MODELO_POR_DEFECTO, obtener_modelo  # noqa: E402


def marca(ok: bool) -> str:
    return "OK   " if ok else "FALTA"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llamar", action="store_true", help="una llamada corta por proveedor (gasta cuota: hasta 3 llamadas en total)")
    a = ap.parse_args()

    print("Sin llamadas a modelos:")
    print(f"  {marca(bool(os.environ.get('GOOGLE_API_KEY')))} clave de Gemini (GOOGLE_API_KEY) en el entorno")
    print(f"  {marca(bool(os.environ.get('DEEPSEEK_API_KEY')))} clave de DeepSeek (DEEPSEEK_API_KEY), respaldo opcional")
    print(f"  {marca(INDICE.exists())} índice de embeddings ({INDICE.name})")
    try:
        metodo = buscar("teléfono de atención al cliente", 3)[0]["metodo"]
        print(f"  {marca(metodo == 'embeddings')} recuperación con embeddings (método usado: {metodo}; si es «palabras», Ollama no respondió)")
    except Exception as e:  # noqa: BLE001
        print(f"  FALTA recuperación: {str(e)[:100]}")
    print(f"  {marca(len(preguntas_guardadas()) > 0)} respuestas guardadas para el último recurso ({len(preguntas_guardadas())} preguntas)")
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
