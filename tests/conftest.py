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
def sin_clave_de_chat(monkeypatch):
    """Las pruebas llaman a /chat sin clave aunque el .env tenga CHAT_TOKEN (la que la mide la fija ella misma)."""
    monkeypatch.delenv("CHAT_TOKEN", raising=False)


@pytest.fixture(autouse=True)
def sin_avisos_reales(monkeypatch):
    """Ninguna prueba manda mensajes por OpenClaw ni hereda pendientes de otra."""
    monkeypatch.delenv("OPENCLAW_AVISOS", raising=False)
    try:
        from taaml import aprobaciones
    except ImportError:
        yield
        return
    aprobaciones.vaciar()
    yield
    aprobaciones.vaciar()


@pytest.fixture(autouse=True)
def sin_limite_de_mensajes(monkeypatch):
    """El límite por teléfono de la API se apaga en las pruebas que no lo miden (varias escriben muchos mensajes seguidos)."""
    try:
        import api.main
        from taaml.limite import LimitePorTelefono
    except ImportError:
        return
    monkeypatch.setattr(api.main, "LIMITE", LimitePorTelefono(0, 60))


@pytest.fixture(autouse=True)
def sin_revision_de_datos_en_la_api(monkeypatch):
    """Las pruebas de la API con un agente falso no revisan datos sin respaldo (eso lo prueba su propia prueba)."""
    try:
        import api.main
    except ImportError:
        return
    monkeypatch.setattr(api.main, "aviso_de_datos_dudosos", lambda *a, **k: "")
    monkeypatch.setattr(api.main, "costo_del_turno", lambda *a, **k: None)
