import numpy as np
import pytest

from taaml import recuperacion
from taaml.recuperacion import almacen_vectorial, buscar, cargar_fragmentos, construir_qdrant, _coleccion, _matriz

hay_qdrant = pytest.mark.skipif(almacen_vectorial() != "qdrant", reason="falta data/4_curaduria/qdrant o la carpeta está abierta por otro proceso (se crea con scripts/07_construir_indice.py)")


@hay_qdrant
def test_qdrant_ordena_igual_que_la_matriz():
    matriz, ids = _matriz(), [f["chunk_id"] for f in cargar_fragmentos()]
    assert matriz is not None
    cliente = _coleccion()
    for i in (0, 123, 777, 1500):
        vector = matriz[i]  # la consulta es el vector de un fragmento: él mismo debe quedar primero
        por_matriz = [ids[j] for j in np.argsort(-(matriz @ vector))[:12]]
        puntos = cliente.query_points(recuperacion.COLECCION, query=vector.tolist(), limit=12, with_payload=["chunk_id"]).points
        de_qdrant = [p.payload["chunk_id"] for p in puntos]
        assert de_qdrant[0] == ids[i] == por_matriz[0]
        assert len(set(de_qdrant) & set(por_matriz)) >= 11  # empates de puntaje pueden cambiar un vecino del final


@hay_qdrant
def test_las_similitudes_de_qdrant_coinciden_con_las_de_la_matriz():
    matriz = _matriz()
    assert matriz is not None
    vector = matriz[42]
    de_qdrant, de_matriz = recuperacion._similitudes(vector), matriz @ vector
    assert np.allclose(de_qdrant, de_matriz, atol=1e-3)


def test_la_misma_pregunta_devuelve_los_mismos_fragmentos_en_el_mismo_orden():
    corridas = [[(r["chunk_id"], r["puntaje"]) for r in buscar("¿Cuál es el teléfono de atención al cliente?", 12, "palabras")] for _ in range(3)]
    assert corridas[0] == corridas[1] == corridas[2] and len(corridas[0]) == 12


def test_buscar_devuelve_los_puntajes_de_mayor_a_menor():
    puntajes = [r["puntaje"] for r in buscar("factura de energía", 12, "palabras")]
    assert puntajes == sorted(puntajes, reverse=True)


def test_construir_qdrant_reemplaza_la_coleccion(monkeypatch, tmp_path):
    monkeypatch.setattr(recuperacion, "QDRANT", tmp_path / "qdrant")
    recuperacion._cliente_qdrant.cache_clear()  # el cliente de la carpeta real queda abierto; este apunta a la carpeta temporal
    ids = ["a", "b", "c"]
    vectores = np.eye(3, dtype=np.float32)
    construir_qdrant(ids, vectores, [{"categoria": "x", "region": "y", "fuente": "z"}] * 3)
    construir_qdrant(ids[:2], vectores[:2], [{"categoria": "x", "region": "y", "fuente": "z"}] * 2)  # reconstruir no duplica
    cliente = recuperacion._cliente_qdrant()
    assert cliente.count(recuperacion.COLECCION).count == 2
    mejor = cliente.query_points(recuperacion.COLECCION, query=[1.0, 0.0, 0.0], limit=1, with_payload=["chunk_id"]).points[0]
    assert mejor.payload["chunk_id"] == "a"
    cliente.close()
    recuperacion._cliente_qdrant.cache_clear()
    recuperacion._coleccion.cache_clear()
