"""La búsqueda «mezcla»: k-1 fragmentos por significado y, al final, la mejor por palabras que no esté ya."""

import numpy as np

from taaml import recuperacion


def _falsos(n=6):
    return [{"chunk_id": f"c{i}", "texto": f"texto {i}", "documento": "d", "categoria": "x", "region": "y", "fuente": "f"} for i in range(n)]


def test_la_mezcla_agrega_la_mejor_por_palabras_y_conserva_el_orden_de_significado(monkeypatch):
    monkeypatch.setattr(recuperacion, "cargar_fragmentos", lambda: _falsos())
    monkeypatch.setattr(recuperacion, "_matriz", lambda: np.zeros((6, 1)))
    monkeypatch.setattr(recuperacion, "embeddings", lambda textos, tipo: np.zeros((1, 1)))
    monkeypatch.setattr(recuperacion, "_similitudes", lambda v, f=None: np.array([0.9, 0.8, 0.7, 0.6, 0.1, 0.0]))
    monkeypatch.setattr(recuperacion, "_puntajes_por_palabras", lambda p: np.array([0.0, 0.0, 0.0, 0.0, 0.0, 5.0]))
    resultado, metodo = recuperacion._buscar("pregunta", 4, "mezcla")
    assert [r["chunk_id"] for r in resultado] == ["c0", "c1", "c2", "c5"]
    assert metodo == "mezcla"
    assert [r["metodo"] for r in resultado] == ["embeddings"] * 3 + ["palabras"]


def test_la_mezcla_no_repite_un_fragmento_ni_agrega_uno_sin_coincidencia(monkeypatch):
    monkeypatch.setattr(recuperacion, "cargar_fragmentos", lambda: _falsos())
    monkeypatch.setattr(recuperacion, "_matriz", lambda: np.zeros((6, 1)))
    monkeypatch.setattr(recuperacion, "embeddings", lambda textos, tipo: np.zeros((1, 1)))
    monkeypatch.setattr(recuperacion, "_similitudes", lambda v, f=None: np.array([0.9, 0.8, 0.7, 0.6, 0.1, 0.0]))
    monkeypatch.setattr(recuperacion, "_puntajes_por_palabras", lambda p: np.zeros(6))
    resultado, _ = recuperacion._buscar("pregunta", 4, "mezcla")
    assert [r["chunk_id"] for r in resultado] == ["c0", "c1", "c2"]
    monkeypatch.setattr(recuperacion, "_puntajes_por_palabras", lambda p: np.array([9.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
    resultado, _ = recuperacion._buscar("pregunta", 4, "mezcla")
    assert len({r["chunk_id"] for r in resultado}) == len(resultado)
