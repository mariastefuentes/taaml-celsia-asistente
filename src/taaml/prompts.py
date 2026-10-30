"""Prompts del asistente de Celsia.

Los textos viven en prompts/ (versionados, uno por archivo). Aquí solo se cargan y se arman.
Un solo lugar para armar el prompt: lo usan la evaluación (scripts/11_evaluar_modelo.py) y, más adelante,
la aplicación en Streamlit. Así lo que se mide es exactamente lo que se entrega.

Estándar de diseño: cinco bloques (rol, contexto, instrucción, formato, restricciones), instrucciones críticas
repetidas al final (sandwich) y entrada del cliente delimitada con etiquetas XML.
"""
from datetime import date
from pathlib import Path

PROMPTS = Path(__file__).resolve().parents[2] / "prompts"
VERSION_VIGENTE = "v3"
PARAMETROS_MODELO = {"temperature": 0.0, "top_p": 0.1}  # regla del proyecto para RAG y agentes


def leer_prompt(nombre: str) -> str:
    """Lee un prompt versionado sin su encabezado (frontmatter)."""
    texto = (PROMPTS / nombre).read_text(encoding="utf-8")
    return texto.split("---", 2)[2].strip() if texto.startswith("---") else texto.strip()


def construir_prompt_sistema(contexto: str, version: str = VERSION_VIGENTE) -> str:
    """Inserta la base de conocimiento en el prompt de sistema de la versión pedida."""
    return leer_prompt(f"{version}_asistente.md").replace("{contexto}", contexto).replace("{hoy}", date.today().isoformat()) + "\n"


def construir_mensaje_usuario(pregunta: str, version: str = VERSION_VIGENTE) -> str:
    """Envuelve la pregunta en <user_input> y repite lo esencial después (sándwich).

    v1 no usaba etiquetas: la pregunta viajaba tal cual.
    """
    if version == "v1":
        return pregunta
    # se neutraliza una etiqueta de cierre dentro de la pregunta, para que no pueda "salirse" del bloque
    segura = pregunta.replace("</user_input>", "").replace("<user_input>", "")
    recordatorio = leer_prompt(f"{version}_recordatorio.md")
    return f"<user_input>\n{segura}\n</user_input>\n\n{recordatorio}"
