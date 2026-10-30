"""AGENTE CON HERRAMIENTA: hace unas preguntas a un agente `create_agent` que consulta la base de Celsia con una herramienta.

Usa un modelo local de Ollama (sin costo); necesita Ollama encendido y `ollama pull llama3.2`.
Uso:  uv run python scripts/15_probar_agente.py ["pregunta"]   (sin argumento, hace tres preguntas de ejemplo; en CPU cada una tarda varios minutos)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from taaml.agente import FRAGMENTOS_AGENTE, preguntar  # noqa: E402
from taaml.recuperacion import buscar  # noqa: E402
from taaml.validacion import datos_sin_respaldo  # noqa: E402

EJEMPLOS = ["¿Cuál es el teléfono de atención al cliente de Celsia?", "¿Cómo puedo pagar mi factura de energía?", "¿Cuánto cuesta un viaje a Cartagena?"]


def main() -> None:
    for pregunta in sys.argv[1:] or EJEMPLOS:
        respuesta, consultas = preguntar(pregunta)
        dudosos = datos_sin_respaldo(respuesta, [f for c in consultas for f in buscar(c, k=FRAGMENTOS_AGENTE)])
        print(f"\nPregunta: {pregunta}\nConsultas a la herramienta: {consultas or 'ninguna'}\nRespuesta: {respuesta}")
        print(f"Datos sin respaldo: {dudosos or 'ninguno'}")


if __name__ == "__main__":
    main()
