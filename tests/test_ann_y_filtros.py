import importlib.util
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("ann_y_filtros", RAIZ / "scripts" / "26_explorar_ann_y_filtros.py")
ann = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ann)


def _datos(n=200, d=16, semilla=0):
    v = np.random.default_rng(semilla).normal(size=(n, d))
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def test_ivf_con_todas_las_celdas_equivale_a_la_busqueda_exacta_y_con_una_compara_menos():
    v, q = _datos(), _datos(1, semilla=1)[0]
    ivf = ann.IVF(v, 8)
    todos, comparados = ivf.buscar(q, 8)
    assert todos == ann.top_exacto(v, q) and comparados == len(v)
    _, pocos = ivf.buscar(q, 1)
    assert pocos < len(v)


def test_pq_comprime_a_un_byte_por_trozo_y_el_reranking_mejora_el_recall():
    v = _datos(300, 16)
    pq = ann.PQ(v, m=4, centroides_por_trozo=16)
    assert pq.codigos.shape == (300, 4) and pq.codigos.dtype == np.uint8
    consultas = _datos(20, 16, semilla=2)
    sin = np.mean([ann.recall(pq.buscar(q), ann.top_exacto(v, q)) for q in consultas])
    con = np.mean([ann.recall(pq.buscar(q, rerank=60), ann.top_exacto(v, q)) for q in consultas])
    assert con >= sin


def test_recall_cuenta_los_vecinos_exactos_recuperados():
    assert ann.recall([1, 2, 3], [1, 2, 3, 4]) == 0.75 and ann.recall([], []) == 1.0


def test_el_prefiltrado_devuelve_los_k_pedidos_y_el_postfiltrado_con_k_chico_se_queda_corto():
    v, q = _datos(), _datos(1, semilla=3)[0]
    permitidos = np.zeros(len(v), dtype=bool)
    permitidos[::20] = True  # 5 % de los puntos cumplen el filtro
    pre = ann.top_exacto(v, q, permitidos=permitidos)
    post = [i for i in ann.top_exacto(v, q, k=10) if permitidos[i]]
    assert len(pre) == 10 and all(permitidos[i] for i in pre)
    assert len(post) < len(pre)
