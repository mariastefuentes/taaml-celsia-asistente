"""Pruebas de componentes (nivel de componentes): deterministas, sin Gemini y sin Ollama."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
