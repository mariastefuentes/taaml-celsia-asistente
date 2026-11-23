"""Pruebas de la información escrita a mano: trámites en línea y política de datos."""

from taaml.informacion_manual import politica_de_datos, tramites_en_linea


def test_los_tramites_traen_enlace_y_fuente():
    filas = tramites_en_linea(tipo="pago")
    assert filas and all(f["enlace"].startswith("https://") and f["fuente"] for f in filas)


def test_los_tramites_se_filtran_por_texto():
    assert any("paga-tus-facturas" in f["enlace"] for f in tramites_en_linea("pagar la factura"))
    assert tramites_en_linea("algo que no existe") == []


def test_la_politica_devuelve_el_cuerpo_sin_encabezados():
    parrafos = politica_de_datos()
    assert parrafos and all(not p.startswith("#") for p in parrafos)


def test_la_politica_filtra_por_tema():
    assert any("borrar" in p.lower() for p in politica_de_datos("derechos"))
    assert politica_de_datos("tema inexistente") == []
