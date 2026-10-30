import numpy as np
import pytest

from taaml import recuperacion
from taaml.recuperacion import almacen_vectorial, buscar, cargar_fragmentos, construir_chroma, _coleccion, _matriz

hay_chroma = pytest.mark.skipif(almacen_vectorial() != "chroma", reason="falta data/4_curaduria/chroma (se crea con scripts/07_construir_indice.py)")


@hay_chroma
def test_chroma_ordena_igual_que_la_matriz():
    matriz, ids = _matriz(), [f["chunk_id"] for f in cargar_fragmentos()]
    coleccion = _coleccion()
    for i in (0, 123, 777, 1500):
        vector = matriz[i]  # la consulta es el vector de un fragmento: él mismo debe quedar primero
        por_matriz = [ids[j] for j in np.argsort(-(matriz @ vector))[:12]]
        respuesta = coleccion.query(query_embeddings=[vector.tolist()], n_results=12)
        assert respuesta["ids"][0][0] == ids[i] == por_matriz[0]
        assert len(set(respuesta["ids"][0]) & set(por_matriz)) >= 11  # HNSW es aproximado: puede cambiar un vecino del final


@hay_chroma
def test_las_similitudes_de_chroma_coinciden_con_las_de_la_matriz():
    matriz = _matriz()
    vector = matriz[42]
    de_chroma, de_matriz = recuperacion._similitudes(vector), matriz @ vector
    assert np.allclose(de_chroma, de_matriz, atol=1e-3)


def test_la_misma_pregunta_devuelve_los_mismos_fragmentos_en_el_mismo_orden():
    corridas = [[(r["chunk_id"], r["puntaje"]) for r in buscar("¿Cuál es el teléfono de atención al cliente?", 12, "palabras")] for _ in range(3)]
    assert corridas[0] == corridas[1] == corridas[2] and len(corridas[0]) == 12


def test_buscar_devuelve_los_puntajes_de_mayor_a_menor():
    puntajes = [r["puntaje"] for r in buscar("factura de energía", 12, "palabras")]
    assert puntajes == sorted(puntajes, reverse=True)


def test_construir_chroma_reemplaza_la_coleccion(monkeypatch, tmp_path):
    monkeypatch.setattr(recuperacion, "CHROMA", tmp_path / "chroma")
    ids = ["a", "b", "c"]
    vectores = np.eye(3, dtype=np.float32)
    construir_chroma(ids, vectores, [{"categoria": "x", "region": "y", "fuente": "z"}] * 3)
    construir_chroma(ids[:2], vectores[:2], [{"categoria": "x", "region": "y", "fuente": "z"}] * 2)  # reconstruir no duplica
    coleccion = recuperacion._cliente_chroma().get_collection(recuperacion.COLECCION)
    assert coleccion.count() == 2
    assert coleccion.query(query_embeddings=[[1.0, 0.0, 0.0]], n_results=1)["ids"][0] == ["a"]
