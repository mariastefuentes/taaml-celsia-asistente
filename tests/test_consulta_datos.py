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
    assert salida.count("\n- ") <= 10 and "afina el filtro" in salida


def test_el_total_lo_calcula_el_codigo_con_pocas_o_muchas_filas():
    pocas = consultar("sedes", {"ciudad": "Ibagué"})
    assert pocas.splitlines()[-1] == f"Total: {len(sedes(ciudad='Ibagué'))} filas."
    muchas = consultar("sedes", {"departamento": "Tolima"})
    assert muchas.splitlines()[-1].startswith(f"Total: {len(sedes(departamento='Tolima'))} filas (se muestran 10")


def test_con_una_sola_fila_el_total_va_en_singular():
    una = next(f for f in sedes() if len(sedes(ciudad=f["CITY"])) == 1)
    assert consultar("sedes", {"ciudad": una["CITY"]}).splitlines()[-1] == "Total: 1 fila."
