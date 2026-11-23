import pytest
from pydantic import ValidationError

from taaml.herramientas_servicio import SedesCercanas, distancia_km, sedes_cercanas, sedes_cercanas_a


def test_distancia_conocida_y_cero_consigo_misma():
    assert distancia_km(4.0, -75.0, 4.0, -75.0) == 0
    assert 110 < distancia_km(4.0, -75.0, 5.0, -75.0) < 112  # un grado de latitud ≈ 111 km


def test_por_ciudad_la_primera_es_una_sede_de_esa_ciudad_y_son_tres():
    texto = sedes_cercanas_a(ciudad="Ibagué")
    lineas = [x for x in texto.splitlines() if x.startswith("- ")]
    assert len(lineas) == 3 and "Ibagué" in lineas[0] and "a 0." in lineas[0]
    assert "línea recta" in texto


def test_por_coordenadas_ordena_de_menor_a_mayor_distancia():
    texto = sedes_cercanas_a(latitud=3.4516, longitud=-76.5320)  # centro de Cali
    km = [float(x.split(" a ")[1].split(" km")[0]) for x in texto.splitlines() if x.startswith("- ")]
    assert km == sorted(km) and km[0] < 60


def test_ciudad_sin_sede_no_inventa_coordenadas():
    assert "No tengo coordenadas" in sedes_cercanas_a(ciudad="Ciudad Inventada")


def test_solo_sedes_de_colombia():
    assert "Panam" not in sedes_cercanas_a(latitud=8.98, longitud=-79.52)  # Ciudad de Panamá: igual responde con sedes colombianas


def test_el_esquema_exige_punto_completo_o_ciudad_y_rechaza_extras():
    with pytest.raises(ValidationError):
        SedesCercanas()
    with pytest.raises(ValidationError):
        SedesCercanas(latitud=3.4)
    with pytest.raises(ValidationError):
        SedesCercanas(latitud=95, longitud=0)
    with pytest.raises(ValidationError):
        SedesCercanas(ciudad="Cali", pais="Colombia")
    assert SedesCercanas(ciudad="Cali").ciudad == "Cali"


def test_la_herramienta_se_invoca_con_los_argumentos_del_modelo():
    salida = sedes_cercanas.invoke({"ciudad": "Palmira"})
    assert "Palmira" in salida
    assert {"latitud", "longitud", "ciudad"} == set(sedes_cercanas.tool_call_schema.model_json_schema()["properties"])
