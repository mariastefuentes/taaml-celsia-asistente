"""Pruebas de componentes (nivel de componentes): deterministas, sin Gemini y sin Ollama."""

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

# Las pruebas no deben enviar trazas a LangSmith aunque el .env tenga la clave: se fija antes de importar taaml (tareas.py solo usa setdefault)
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
