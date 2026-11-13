from taaml.consulta_datos import SIN_RESULTADOS, catalogo, consultar, contactos, sedes


def test_sedes_por_ciudad_ignora_tildes_y_mayusculas():
    assert sedes(ciudad="IBAGUE") and all("ibague" in f["CITY"].lower().replace("é", "e") for f in sedes(ciudad="Ibagué"))


def test_sedes_por_departamento_y_tipo():
    filas = sedes(departamento="Tolima", tipo="Tiendas")
    assert filas and all(f["DEPARTMENT"] == "Tolima" and f["HQ_TYPE"] == "Tiendas Celsia" for f in filas)


def test_contactos_por_tipo():
    filas = contactos(tipo="whatsapp")
    assert filas and all(c["tipo"] == "whatsapp" for c in filas)


def test_catalogo_por_seccion():
    assert catalogo(seccion="page") and all(r["section"] == "page" for r in catalogo(seccion="page"))


def test_consultar_sin_coincidencias_lo_dice():
    assert consultar("sedes", {"ciudad": "Ciudad que no existe"}) == SIN_RESULTADOS


def test_consultar_tabla_desconocida_avisa_cuales_hay():
    salida = consultar("facturas")
    assert "Tabla desconocida" in salida and "sedes" in salida


def test_consultar_ignora_filtros_de_otra_tabla():
    assert consultar("contactos", {"ciudad": "Ibagué", "tipo": "telefono"}).startswith("- telefono")


def test_consultar_limita_las_filas():
    salida = consultar("sedes", {"departamento": "Tolima"})
    assert salida.count("\n- ") <= 10 and "Afina el filtro" in salida
