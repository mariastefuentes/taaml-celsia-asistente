"""Pruebas de componentes (nivel de componentes): deterministas, sin modelos ni red."""

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

# Las pruebas no deben enviar trazas a LangSmith aunque el .env tenga la clave: se fija antes de importar taaml (tareas.py solo usa setdefault)
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def sin_limite_de_mensajes(monkeypatch):
    """El límite por teléfono de la API se apaga en las pruebas que no lo miden (varias escriben muchos mensajes seguidos)."""
    try:
        import api.main
        from taaml.limite import LimitePorTelefono
    except ImportError:
        return
    monkeypatch.setattr(api.main, "LIMITE", LimitePorTelefono(0, 60))
