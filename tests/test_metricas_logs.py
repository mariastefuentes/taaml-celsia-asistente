"""Las dos funciones estadísticas del script 46 (Wilson y McNemar exacto), con valores conocidos."""

import importlib.util
from pathlib import Path

_ruta = Path(__file__).resolve().parent.parent / "scripts" / "46_metricas_logs.py"
_spec = importlib.util.spec_from_file_location("metricas_logs", _ruta)
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


def test_wilson_25_de_35():
    lo, hi = m.wilson(25, 35)
    assert round(lo, 3) == 0.549 and round(hi, 3) == 0.837


def test_wilson_sin_datos_no_divide_por_cero():
    assert m.wilson(0, 0) == (0.0, 0.0)


def test_mcnemar_exacto_casos_conocidos():
    assert m.mcnemar_exacto(0, 0) == 1.0
    assert m.mcnemar_exacto(1, 2) == 1.0
    assert round(m.mcnemar_exacto(0, 8), 4) == 0.0078  # 2 * (1/2**8)
