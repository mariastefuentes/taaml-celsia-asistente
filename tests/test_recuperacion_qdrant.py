import numpy as np
import pytest

from taaml import recuperacion
from taaml.recuperacion import almacen_vectorial, buscar, cargar_fragmentos, construir_qdrant, _coleccion, _matriz

hay_qdrant = pytest.mark.skipif(
    almacen_vectorial() != "qdrant",
    reason="falta data/4_curaduria/qdrant o la carpeta está abierta por otro proceso (se crea con scripts/07_construir_indice.py)",
)


@hay_qdrant
def test_qdrant_ordena_igual_que_la_matriz():
    matriz, ids = _matriz(), [f["chunk_id"] for f in cargar_fragmentos()]
    assert matriz is not None
    cliente = _coleccion()
    for i in (0, 123, 777, 1500):
        vector = matriz[i]  # la consulta es el vector de un fragmento: él mismo debe quedar primero
        por_matriz = [ids[j] for j in np.argsort(-(matriz @ vector))[:12]]
        puntos = cliente.query_points(
            recuperacion.COLECCION, query=vector.tolist(), limit=12, with_payload=["chunk_id"]
        ).points
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
    corridas = [
        [(r["chunk_id"], r["puntaje"]) for r in buscar("¿Cuál es el teléfono de atención al cliente?", 12, "palabras")]
        for _ in range(3)
    ]
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
    construir_qdrant(
        ids[:2], vectores[:2], [{"categoria": "x", "region": "y", "fuente": "z"}] * 2
    )  # reconstruir no duplica
    cliente = recuperacion._cliente_qdrant()
    assert cliente.count(recuperacion.COLECCION).count == 2
    mejor = cliente.query_points(
        recuperacion.COLECCION, query=[1.0, 0.0, 0.0], limit=1, with_payload=["chunk_id"]
    ).points[0]
    assert mejor.payload["chunk_id"] == "a"
    cliente.close()
    recuperacion._cliente_qdrant.cache_clear()
    recuperacion._coleccion.cache_clear()


# --- migración blue/green y filtros por payload ---
META = {"categoria": "x", "region": "y", "fuente": "z"}


@pytest.fixture
def carpeta_temporal(monkeypatch, tmp_path):
    monkeypatch.setattr(recuperacion, "QDRANT", tmp_path / "qdrant")
    recuperacion._cliente_qdrant.cache_clear()  # el cliente de la carpeta real queda abierto; este apunta a la carpeta temporal
    yield recuperacion._cliente_qdrant()
    recuperacion._cliente_qdrant().close()
    recuperacion._cliente_qdrant.cache_clear()
    recuperacion._coleccion.cache_clear()


def _alias(cliente):
    return next(a.collection_name for a in cliente.get_aliases().aliases if a.alias_name == recuperacion.COLECCION)


def test_la_migracion_blue_green_mueve_el_alias_y_conserva_solo_la_version_anterior(carpeta_temporal):
    cliente, vectores = carpeta_temporal, np.eye(3, dtype=np.float32)
    assert construir_qdrant(["a", "b", "c"], vectores, [META] * 3) == "celsia_v1" and _alias(cliente) == "celsia_v1"
    assert construir_qdrant(["a", "b"], vectores[:2], [META] * 2) == "celsia_v2" and _alias(cliente) == "celsia_v2"
    construir_qdrant(["a"], vectores[:1], [META])
    nombres = {c.name for c in cliente.get_collections().collections}
    assert (
        nombres == {"celsia_v2", "celsia_v3"} and _alias(cliente) == "celsia_v3"
    )  # v1 se borró; v2 queda para revertir
    assert cliente.count(recuperacion.COLECCION).count == 1


def test_si_la_validacion_falla_el_alias_sigue_en_la_version_anterior(carpeta_temporal):
    cliente, vectores = carpeta_temporal, np.eye(3, dtype=np.float32)
    construir_qdrant(["a", "b", "c"], vectores, [META] * 3)
    with pytest.raises(RuntimeError, match="no pasó la validación"):
        construir_qdrant(
            ["a", "b", "c"], vectores, [META] * 2
        )  # llegan 2 puntos de 3: la colección nueva está incompleta
    assert _alias(cliente) == "celsia_v1" and cliente.count(recuperacion.COLECCION).count == 3
    assert {c.name for c in cliente.get_collections().collections} == {"celsia_v1"}  # la nueva se borró


def test_revertir_vuelve_a_la_version_anterior(carpeta_temporal):
    cliente, vectores = carpeta_temporal, np.eye(3, dtype=np.float32)
    construir_qdrant(["a", "b", "c"], vectores, [META] * 3)
    construir_qdrant(["a"], vectores[:1], [META])
    assert cliente.count(recuperacion.COLECCION).count == 1
    assert recuperacion.revertir_qdrant() == "celsia_v1" and cliente.count(recuperacion.COLECCION).count == 3
    with pytest.raises(RuntimeError, match="anterior"):
        recuperacion._cliente_qdrant().delete_collection("celsia_v2")
        recuperacion.revertir_qdrant()


def test_un_indice_del_formato_anterior_se_migra_al_primer_alias(carpeta_temporal):
    from qdrant_client import models

    cliente = carpeta_temporal
    cliente.create_collection(
        recuperacion.COLECCION, vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE)
    )  # una colección con el nombre del alias
    construir_qdrant(["a", "b"], np.eye(3, dtype=np.float32)[:2], [META] * 2)
    assert _alias(cliente) == "celsia_v1" and cliente.count(recuperacion.COLECCION).count == 2


def test_el_filtro_por_payload_solo_compara_los_puntos_que_lo_cumplen(carpeta_temporal, monkeypatch):
    from taaml.recuperacion import _similitudes

    fragmentos = [
        {"chunk_id": "a", "categoria": "sedes", "region": "Tolima"},
        {"chunk_id": "b", "categoria": "blog", "region": "Tolima"},
        {"chunk_id": "c", "categoria": "sedes", "region": "Valle"},
    ]
    monkeypatch.setattr(recuperacion, "cargar_fragmentos", lambda: fragmentos)
    construir_qdrant(
        ["a", "b", "c"], np.eye(3, dtype=np.float32), [{k: f[k] for k in ("categoria", "region")} for f in fragmentos]
    )
    puntajes = _similitudes(np.array([0.0, 1.0, 0.0], dtype=np.float32), {"categoria": "sedes"})
    assert np.isneginf(puntajes[1]) and np.isfinite(puntajes[[0, 2]]).all()  # «b» (la mejor sin filtro) queda fuera
    solo_tolima_sedes = _similitudes(
        np.array([1.0, 0.0, 0.0], dtype=np.float32), {"categoria": "sedes", "region": "Tolima"}
    )
    assert np.isfinite(solo_tolima_sedes).tolist() == [True, False, False]


def test_buscar_con_filtro_devuelve_solo_fragmentos_que_lo_cumplen():
    resultado = buscar("oficina de atención en Ibagué", 5, "palabras", {"categoria": "sedes"})
    assert resultado and all(r["categoria"] == "sedes" for r in resultado)
    sin_filtro = buscar("oficina de atención en Ibagué", 5, "palabras")
    assert any(r["categoria"] != "sedes" for r in sin_filtro) or resultado == sin_filtro


def test_un_filtro_que_nadie_cumple_devuelve_vacio_y_un_campo_desconocido_falla():
    assert buscar("sedes", 5, "palabras", {"categoria": "no-existe"}) == []
    with pytest.raises(ValueError, match="No se puede filtrar"):
        buscar("sedes", 5, "palabras", {"autor": "x"})
