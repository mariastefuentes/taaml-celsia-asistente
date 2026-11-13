import importlib.util
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("explorar_embeddings", RAIZ / "scripts" / "25_explorar_embeddings.py")
ex = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ex)


def _vectores(n=40, d=16, semilla=0):
    v = np.random.default_rng(semilla).normal(size=(n, d))
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def test_con_vectores_de_norma_uno_coseno_producto_punto_y_l2_ordenan_igual():
    v = _vectores()
    q = _vectores(1, semilla=1)[0]
    ordenes = [np.argsort(-ex.puntajes(m, v, q)).tolist() for m in ("coseno", "producto_punto", "l2")]
    assert ordenes[0] == ordenes[1] == ordenes[2]


def test_con_vectores_sin_normalizar_el_producto_punto_ya_no_coincide_con_el_coseno():
    v = _vectores() * np.linspace(0.2, 5, 40)[:, None]  # normas muy distintas
    q = _vectores(1, semilla=1)[0]
    assert np.argsort(-ex.puntajes("coseno", v, q)).tolist() != np.argsort(-ex.puntajes("producto_punto", v, q)).tolist()


def test_recortar_deja_las_primeras_dimensiones_con_norma_uno():
    v = _vectores()
    r = ex.recortar(v, 4)
    assert r.shape == (40, 4) and np.allclose(np.linalg.norm(r, axis=1), 1.0)


def test_la_vecindad_de_categorias_separadas_es_perfecta_y_la_mezclada_no():
    x = np.vstack([np.random.default_rng(0).normal(0, 0.1, (30, 2)), np.random.default_rng(1).normal(10, 0.1, (30, 2))])
    separadas = np.array(["a"] * 30 + ["b"] * 30)
    assert ex.pureza_de_vecindad(x, separadas) == 1.0
    assert ex.pureza_de_vecindad(x, np.array(["a", "b"] * 30)) < 0.6


def test_tsne_devuelve_dos_coordenadas_por_punto_y_separa_dos_grupos():
    x = np.vstack([np.random.default_rng(0).normal(0, 0.1, (40, 8)), np.random.default_rng(1).normal(3, 0.1, (40, 8))])
    y = ex.tsne(x, perplejidad=10, iteraciones=200)
    assert y.shape == (80, 2)
    assert ex.pureza_de_vecindad(y, np.array(["a"] * 40 + ["b"] * 40)) > 0.9
