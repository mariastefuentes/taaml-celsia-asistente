"""ENSAYO DEL AGENTE (spec 011): una conversación de cuatro preguntas con memoria y router. GASTA CUOTA de Gemini (unas 8 a 12 llamadas).

Comprueba que el agente elija la herramienta correcta, que recuerde el turno anterior y que no invente datos. Muestra además qué
modelo respondió, para notar si entró el respaldo local. Necesita GOOGLE_API_KEY con facturación y Ollama encendido (embeddings).
Uso:  uv run python scripts/18_ensayo_agente.py
"""
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from taaml.agente import conversar, crear_agente, etiqueta_herramientas  # noqa: E402

# (pregunta, herramienta que debe usar o None si da igual, texto que debe aparecer o None)
CONVERSACION = [
    ("¿Qué sedes hay en Ibagué?", "consultar_datos", None),
    ("¿Y cuál es el teléfono de la sede administrativa?", None, "608 277 08 22")  # basta la memoria: el dato ya está en el turno 1,
    ("¿Cómo cancelo mi servicio?", "buscar_en_base", None),
    ("¿Cuánto cuesta un viaje a Cartagena?", None, "No tengo esa información")  # puede buscar antes de rendirse,
]


def modelos_del_turno(agente, hilo: str) -> set[str]:
    mensajes = agente.get_state({"configurable": {"thread_id": hilo}}).values["messages"]
    ultimo = max(i for i, m in enumerate(mensajes) if m.type == "human")
    return {m.response_metadata.get("model_name", "?") for m in mensajes[ultimo:] if m.type == "ai"}


def main() -> None:
    agente, hilo, fallas = crear_agente(), uuid4().hex, 0
    for pregunta, esperada, texto in CONVERSACION:
        respuesta, llamadas = conversar(pregunta, hilo, agente=agente)
        usadas = {ll["herramienta"] for ll in llamadas}
        ok_herramienta = esperada is None or esperada in usadas
        ok_texto = texto is None or texto in respuesta
        fallas += not (ok_herramienta and ok_texto)
        print(f"\nPregunta: {pregunta}\n{etiqueta_herramientas(llamadas)}  |  modelo: {', '.join(sorted(modelos_del_turno(agente, hilo)))}")
        print(f"Respuesta: {respuesta}\nHerramienta esperada: {'sí' if ok_herramienta else 'NO'}  |  texto esperado: {'sí' if ok_texto else 'NO'}")
    print(f"\nResultado: {len(CONVERSACION) - fallas} de {len(CONVERSACION)} preguntas correctas")


if __name__ == "__main__":
    main()
