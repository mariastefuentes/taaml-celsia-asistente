import pytest
from pydantic import ValidationError

from taaml.herramientas_servicio import CiudadesConAtencion, SedesCercanas, ciudades_con_atencion, ciudades_con_atencion_en, distancia_km, sedes_cercanas, sedes_cercanas_a


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


def test_ciudades_por_departamento_con_total_contado_por_el_codigo():
    texto = ciudades_con_atencion_en("Tolima")
    assert "Tolima:" in texto and "Ibagué" in texto and "Valle del Cauca" not in texto
    ciudades = texto.splitlines()[0].split(": ", 1)[1].split(", ")
    assert texto.splitlines()[-1] == f"Total: {len(ciudades)} ciudades."


def test_ciudades_varios_departamentos_y_sin_filtro_excluye_otros_paises():
    dos = ciudades_con_atencion_en("Tolima, Valle del Cauca")
    todo = ciudades_con_atencion_en()
    assert "Tolima:" in dos and "Valle del Cauca:" in dos and "Antioquia:" not in dos
    assert "Antioquia:" in todo and "Panam" not in todo and "Costa Rica" not in todo and "Honduras" not in todo
    assert int(todo.rsplit("Total: ", 1)[1].split()[0]) > int(dos.rsplit("Total: ", 1)[1].split()[0])


def test_ciudades_departamento_inexistente_dice_sin_resultados():
    assert ciudades_con_atencion_en("Atlántida") == "Sin resultados en los datos estructurados."


def test_ciudades_esquema_y_herramienta():
    with pytest.raises(ValidationError):
        CiudadesConAtencion(departamento="Tolima", otro="x")
    assert CiudadesConAtencion().departamento == ""
    assert "Ibagué" in ciudades_con_atencion.invoke({"departamento": "tolima"})  # sin tildes ni mayúsculas
    assert set(ciudades_con_atencion.tool_call_schema.model_json_schema()["properties"]) == {"departamento"}


from taaml.herramientas_servicio import CanalAVerificar, verificar_canal, verificar_canal_oficial  # noqa: E402


@pytest.mark.parametrize(
    "valor",
    ["01 8000 112 115", "018000112115", "+57 310 390 3468", "3103903468", "311 321 0000", "servicioalcliente@celsia.com", "SERVICIOALCLIENTE@celsia.com"],
)
def test_canales_oficiales_se_reconocen_aunque_cambie_el_formato(valor):
    assert verificar_canal(valor).startswith("Sí figura")


def test_el_whatsapp_y_el_telefono_se_nombran_bien_y_el_de_una_sede_tambien():
    assert "WhatsApp" in verificar_canal("3103903468")
    assert "teléfono" in verificar_canal("01 8000 112 115")
    assert "Sede" in verificar_canal("604 326 66 00")


def test_numero_ajeno_o_parecido_no_figura_y_no_se_dice_que_sea_falso():
    for ajeno in ("310 390 3469", "300 123 4567", "326 66 00"):  # el último es un pedazo de un número oficial: no cuenta
        r = verificar_canal(ajeno)
        assert r.startswith("No figura") and "01 8000 112 115" in r and "falso" in r.lower() and "no prueba" in r


def test_correo_del_dominio_de_celsia_que_no_esta_en_la_lista_lo_avisa_distinto():
    assert "dominio del correo es de Celsia" in verificar_canal("pagos@celsia.com")
    assert verificar_canal("servicioalcliente@celsia.co.ru").startswith("No figura")  # dominio parecido
    assert verificar_canal("atencion@celsia-energia.com").startswith("No figura")


def test_enlaces_exactos_del_sitio_o_con_otra_ruta_y_dominios_parecidos():
    assert verificar_canal("https://clientes.celsia.com/clientes/paga-tus-facturas").startswith("Sí figura")
    assert verificar_canal("clientes.celsia.com/clientes/paga-tus-facturas/").startswith("Sí figura")  # sin esquema y con «/» final
    assert "esa dirección exacta no está" in verificar_canal("https://clientes.celsia.com/promo-gana-ya")
    assert verificar_canal("https://clientes-celsia.com/paga-tus-facturas").startswith("No figura")
    assert verificar_canal("https://celsia.com.pagos-seguros.co/").startswith("No figura")


def test_entrada_que_no_es_un_canal_pide_el_dato_completo():
    assert "No entendí" in verificar_canal("hola")


def test_esquema_y_herramienta_de_verificar_canal():
    with pytest.raises(ValidationError):
        CanalAVerificar()
    with pytest.raises(ValidationError):
        CanalAVerificar(canal="ab")
    with pytest.raises(ValidationError):
        CanalAVerificar(canal="3103903468", otro="x")
    assert verificar_canal_oficial.invoke({"canal": "01 8000 112 115"}).startswith("Sí figura")
    assert set(verificar_canal_oficial.tool_call_schema.model_json_schema()["properties"]) == {"canal"}


from taaml.herramientas_servicio import SinParametros, canales_de_emergencia, canales_de_emergencia_texto  # noqa: E402


def test_los_canales_de_emergencia_traen_la_123_y_los_datos_oficiales_de_los_contactos():
    texto = canales_de_emergencia_texto()
    assert "123" in texto and "+57 310 390 3468" in texto and "reporta-un-dano" in texto and "01 8000 112 115" in texto
    assert len(texto.splitlines()) == 4


def test_el_whatsapp_de_emergencia_es_el_de_energia_y_no_el_de_internet():
    assert "311 321 0000" not in canales_de_emergencia_texto()


def test_si_faltan_los_contactos_igual_da_la_123(monkeypatch):
    monkeypatch.setattr("taaml.herramientas_servicio.contactos", lambda **filtros: [])
    assert canales_de_emergencia_texto().splitlines() == [
        "- Peligro inmediato (cable caído, chispas, humo, descarga): llama a la línea nacional de emergencias 123."
    ]


def test_la_herramienta_no_pide_nada_al_modelo():
    with pytest.raises(ValidationError):
        SinParametros(algo="x")
    assert canales_de_emergencia.invoke({}) == canales_de_emergencia_texto()
    assert canales_de_emergencia.tool_call_schema.model_json_schema()["properties"] == {}


from datetime import datetime, timezone  # noqa: E402

from taaml.herramientas_servicio import fecha_y_hora_actual, fecha_y_hora_texto  # noqa: E402


def test_la_hora_se_convierte_a_colombia_con_dia_y_mes_en_espanol():
    utc = datetime(2026, 11, 23, 19, 35, tzinfo=timezone.utc)  # lunes 23/11/2026, 14:35 en Colombia
    assert fecha_y_hora_texto(utc) == "Hoy es lunes 23 de noviembre de 2026, 14:35 (hora de Colombia, UTC-5)."


def test_pasada_la_medianoche_utc_en_colombia_sigue_siendo_el_dia_anterior():
    utc = datetime(2026, 11, 28, 3, 5, tzinfo=timezone.utc)  # 22:05 del viernes 27 en Colombia
    assert "viernes 27 de noviembre" in fecha_y_hora_texto(utc) and "22:05" in fecha_y_hora_texto(utc)


def test_domingo_y_enero():
    assert fecha_y_hora_texto(datetime(2027, 1, 3, 17, 0, tzinfo=timezone.utc)).startswith("Hoy es domingo 3 de enero de 2027, 12:00")


def test_la_herramienta_usa_el_reloj_real_y_no_pide_nada_al_modelo():
    assert fecha_y_hora_actual.invoke({}).startswith("Hoy es ")
    assert fecha_y_hora_actual.tool_call_schema.model_json_schema()["properties"] == {}


from taaml.herramientas_servicio import FacturaEstimada, calcular_factura_estimada, factura_estimada, pesos  # noqa: E402


def test_pesos_con_punto_de_miles():
    assert pesos(1234567) == "$1.234.567" and pesos(999.6) == "$1.000" and pesos(0) == "$0"


def test_factura_solo_energia():
    r = factura_estimada(200, 900)
    assert "200 kWh × $900 por kWh = $180.000" in r and "Total estimado: $180.000" in r and "estimado" not in r.split("Total")[0]
    assert "Cargo fijo" not in r and "Subsidio" not in r and "Contribución" not in r


def test_factura_con_cargo_fijo_y_contribucion():
    r = factura_estimada(100, 1000, cargo_fijo_cop=5000, ajuste_pct=20)  # 100.000 + 5.000 + 20.000
    assert "Cargo fijo: $5.000" in r and "Contribución (20 % de la energía): +$20.000" in r and "Total estimado: $125.000" in r


def test_factura_con_subsidio_resta():
    r = factura_estimada(130, 800, ajuste_pct=-50)  # 104.000 - 52.000
    assert "Subsidio (50 % de la energía): -$52.000" in r and "Total estimado: $52.000" in r


def test_siempre_advierte_que_es_un_estimado_y_que_la_factura_oficial_puede_variar():
    assert "la factura oficial puede variar" in factura_estimada(50, 700)


def test_esquema_rechaza_valores_imposibles_y_campos_extra():
    for malo in ({"consumo_kwh": 0, "tarifa_cop_kwh": 900}, {"consumo_kwh": -5, "tarifa_cop_kwh": 900}, {"consumo_kwh": 100, "tarifa_cop_kwh": 0},
                 {"consumo_kwh": 100, "tarifa_cop_kwh": 99_999}, {"consumo_kwh": 100, "tarifa_cop_kwh": 900, "ajuste_pct": 150},
                 {"consumo_kwh": 100, "tarifa_cop_kwh": 900, "cargo_fijo_cop": -1}, {"consumo_kwh": 100, "tarifa_cop_kwh": 900, "iva": 19}):
        with pytest.raises(ValidationError):
            FacturaEstimada(**malo)
    assert FacturaEstimada(consumo_kwh=100, tarifa_cop_kwh=900).ajuste_pct == 0


def test_la_herramienta_calcula_y_rechaza_argumentos_invalidos():
    assert "Total estimado: $90.000" in calcular_factura_estimada.invoke({"consumo_kwh": 100, "tarifa_cop_kwh": 900})
    with pytest.raises(ValidationError):
        calcular_factura_estimada.invoke({"consumo_kwh": "mucho", "tarifa_cop_kwh": 900})
    assert set(calcular_factura_estimada.tool_call_schema.model_json_schema()["properties"]) == {
        "consumo_kwh", "tarifa_cop_kwh", "cargo_fijo_cop", "ajuste_pct",
    }


from taaml.herramientas_servicio import ConsumoDeAparato, consumo_aparato, consumo_de_un_aparato  # noqa: E402


def test_consumo_de_un_aparato_sin_y_con_tarifa():
    sin = consumo_aparato(150, 24)  # nevera: 150 W × 24 h × 30 d = 108 kWh
    assert "= 108.00 kWh" in sin and "pídesela al cliente" in sin and "cuestan" not in sin
    con = consumo_aparato(150, 24, tarifa_cop_kwh=900)
    assert "= 108.00 kWh" in con and "cuestan $97.200" in con and "estimado" in con


def test_consumo_con_otros_dias_y_horas_fraccionadas():
    assert "= 2.50 kWh" in consumo_aparato(100, 2.5, dias=10)  # 100 × 2,5 × 10 ÷ 1000


def test_esquema_del_aparato_rechaza_imposibles_y_extras():
    for malo in ({"potencia_vatios": 0, "horas_por_dia": 2}, {"potencia_vatios": 100, "horas_por_dia": 25}, {"potencia_vatios": 100, "horas_por_dia": 0},
                 {"potencia_vatios": 100, "horas_por_dia": 2, "dias": 0}, {"potencia_vatios": 100, "horas_por_dia": 2, "dias": 400},
                 {"potencia_vatios": 100, "horas_por_dia": 2, "tarifa_cop_kwh": -1}, {"potencia_vatios": 100, "horas_por_dia": 2, "marca": "x"}):
        with pytest.raises(ValidationError):
            ConsumoDeAparato(**malo)
    assert ConsumoDeAparato(potencia_vatios=60, horas_por_dia=5).dias == 30


def test_la_herramienta_del_aparato():
    assert "= 3.00 kWh" in consumo_de_un_aparato.invoke({"potencia_vatios": 100, "horas_por_dia": 1})
    with pytest.raises(ValidationError):
        consumo_de_un_aparato.invoke({"potencia_vatios": "mucha", "horas_por_dia": 1})
    assert set(consumo_de_un_aparato.tool_call_schema.model_json_schema()["properties"]) == {"potencia_vatios", "horas_por_dia", "dias", "tarifa_cop_kwh"}
