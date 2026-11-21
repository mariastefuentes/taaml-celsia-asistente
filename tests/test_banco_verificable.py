"""El banco verificable (script 43): sus datos esperados de trámites y tarifas tienen que estar en el texto oficial."""

import importlib.util
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _cargar_banco():
    """El script fija DATABASE_URL al importarse (memoria temporal): se restaura para no afectar a las demás pruebas."""
    antes, ruta_antes = os.environ.get("DATABASE_URL"), list(sys.path)
    try:
        espec = importlib.util.spec_from_file_location("banco_verificable", RAIZ / "scripts" / "43_banco_verificable.py")
        modulo = importlib.util.module_from_spec(espec)
        espec.loader.exec_module(modulo)
        return modulo
    finally:
        sys.path[:] = ruta_antes
        if antes is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = antes


def test_los_datos_esperados_de_tramites_y_tarifas_estan_en_el_texto_oficial():
    banco = _cargar_banco()
    assert banco.hechos_sin_respaldo() == []
    assert len(banco.TRAMITES) >= 9


def test_la_regla_de_tramites_acepta_la_respuesta_completa_y_rechaza_la_incompleta():
    banco = _cargar_banco()
    caso = next(c for c in banco.casos_de_tramites() if "subsidio" in c[0])
    falla = caso[2]
    assert falla("El subsidio es de hasta el 60% para el estrato 1, 50% para el 2 y 15% para el 3.") is False
    assert falla("El subsidio es de hasta el 60% para el estrato 1.") is True
