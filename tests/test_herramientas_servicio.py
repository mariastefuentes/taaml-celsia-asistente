import time

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


from taaml.herramientas_servicio import AhorroSolar, ahorro_solar, estimar_ahorro_solar  # noqa: E402


def test_ahorro_solar_mensual_y_anual():
    r = ahorro_solar(300, 900, 50)  # 150 kWh × 900 = 135.000 al mes, 1.620.000 al año
    assert "150.0 kWh" in r and "$135.000 al mes" in r and "$1.620.000 al año" in r


def test_ahorro_solar_aclara_que_es_un_escenario_sin_costo_de_instalacion():
    r = ahorro_solar(200, 800, 100)
    assert "no una promesa" in r and "costo de instalación" in r and "asesor de Celsia" in r


def test_esquema_solar_rechaza_porcentajes_imposibles_y_extras():
    for malo in ({"consumo_kwh_mes": 300, "tarifa_cop_kwh": 900, "porcentaje_cubierto": 0}, {"consumo_kwh_mes": 300, "tarifa_cop_kwh": 900, "porcentaje_cubierto": 101},
                 {"consumo_kwh_mes": 0, "tarifa_cop_kwh": 900, "porcentaje_cubierto": 50}, {"consumo_kwh_mes": 300, "tarifa_cop_kwh": -1, "porcentaje_cubierto": 50},
                 {"consumo_kwh_mes": 300, "tarifa_cop_kwh": 900, "porcentaje_cubierto": 50, "paneles": 4}, {"consumo_kwh_mes": 300, "tarifa_cop_kwh": 900}):
        with pytest.raises(ValidationError):
            AhorroSolar(**malo)


def test_la_herramienta_solar():
    assert "$135.000 al mes" in estimar_ahorro_solar.invoke({"consumo_kwh_mes": 300, "tarifa_cop_kwh": 900, "porcentaje_cubierto": 50})
    with pytest.raises(ValidationError):
        estimar_ahorro_solar.invoke({"consumo_kwh_mes": 300, "tarifa_cop_kwh": 900})
    assert set(estimar_ahorro_solar.tool_call_schema.model_json_schema()["properties"]) == {"consumo_kwh_mes", "tarifa_cop_kwh", "porcentaje_cubierto"}


from langgraph.store.memory import InMemoryStore  # noqa: E402

from taaml.herramientas_servicio import EstadoDeReclamo, consultar_estado_reclamo, estado_de_reclamo  # noqa: E402


def _almacen_con_reclamos():
    almacen = InMemoryStore()
    almacen.put(("reclamos", "ana"), "REC-ABCD1234", {"tipo": "falla_de_servicio", "ciudad": "Ibagué", "descripcion": "Sin luz desde las 8"})
    almacen.put(("reclamos", "luis"), "REC-99999999", {"tipo": "otro", "ciudad": "Cali", "descripcion": "reclamo de Luis"})
    return almacen


def test_el_cliente_ve_su_reclamo_con_fecha_tipo_y_ciudad_y_sin_inventar_el_estado():
    r = estado_de_reclamo(_almacen_con_reclamos(), "ana", "REC-ABCD1234")
    assert "figura radicado el" in r and "falla del servicio" in r and "Ibagué" in r and "Sin luz desde las 8" in r
    assert "no veo si ya lo están gestionando" in r and "01 8000 112 115" in r


def test_un_cliente_no_ve_el_reclamo_de_otro_y_un_anonimo_no_ve_nada():
    almacen = _almacen_con_reclamos()
    assert "No encontré el radicado REC-99999999" in estado_de_reclamo(almacen, "ana", "REC-99999999")
    assert "reclamo de Luis" not in estado_de_reclamo(almacen, "ana", "REC-99999999")
    assert "no hay un cliente identificado" in estado_de_reclamo(almacen, "anonimo", "REC-ABCD1234")


def test_el_radicado_se_normaliza_y_se_rechaza_lo_que_no_tiene_su_forma():
    normalizar = EstadoDeReclamo._formato  # el validador del campo, sin necesidad de un runtime
    assert normalizar(" rec-abcd1234 ") == "REC-ABCD1234"
    for malo in ("12345", "REC-XYZ", "REC-ABCD12345", "'; DROP TABLE", ""):
        with pytest.raises(ValueError):
            normalizar(malo)


def test_el_modelo_no_ve_el_runtime_ni_puede_pasar_el_usuario():
    assert set(consultar_estado_reclamo.tool_call_schema.model_json_schema()["properties"]) == {"numero"}


from taaml.herramientas_servicio import SoloElCliente, listar_mis_reclamos, reclamos_del_cliente  # noqa: E402


def test_lista_los_reclamos_del_cliente_con_el_total_y_sin_mezclar_clientes():
    almacen = _almacen_con_reclamos()
    r = reclamos_del_cliente(almacen, "ana")
    assert "REC-ABCD1234" in r and "falla del servicio" in r and "Ibagué" in r and r.endswith("Total: 1 reclamo.")
    assert "REC-99999999" not in r and "Cobro" not in r


def test_lista_vacia_y_anonimo():
    assert "no tiene reclamos radicados" in reclamos_del_cliente(InMemoryStore(), "ana")
    assert "no hay un cliente identificado" in reclamos_del_cliente(_almacen_con_reclamos(), "anonimo")


def test_lista_ordena_del_mas_reciente_y_topa_en_diez():
    almacen = InMemoryStore()
    for n in range(12):
        time.sleep(0.01)  # que cada uno tenga su propia hora de creación
        almacen.put(("reclamos", "ana"), f"REC-0000000{n:X}", {"tipo": "otro", "ciudad": "Cali", "descripcion": f"caso {n}"})
    r = reclamos_del_cliente(almacen, "ana")
    lineas = [x for x in r.splitlines() if x.startswith("- ")]
    assert len(lineas) == 10 and "Total: 12 reclamos (se muestran los 10 más recientes)." in r
    assert "caso 11" in lineas[0]  # el último que se guardó sale primero


def test_la_herramienta_de_listar_no_pide_nada_al_modelo():
    with pytest.raises(ValidationError):
        SoloElCliente.model_validate({"runtime": None})
    assert listar_mis_reclamos.tool_call_schema.model_json_schema()["properties"] == {}


from taaml.herramientas_servicio import DetalleDeReclamo, agregar_detalle, agregar_detalle_a_reclamo  # noqa: E402


def test_agrega_un_detalle_y_aparece_al_consultar_el_reclamo_sin_cambiar_lo_radicado():
    almacen = _almacen_con_reclamos()
    antes = almacen.get(("reclamos", "ana"), "REC-ABCD1234").created_at
    assert agregar_detalle(almacen, "ana", "REC-ABCD1234", "El medidor es el de la esquina") .startswith("Agregado al reclamo REC-ABCD1234")
    item = almacen.get(("reclamos", "ana"), "REC-ABCD1234")
    assert item.value["descripcion"] == "Sin luz desde las 8" and item.value["detalles"] == ["El medidor es el de la esquina"]
    assert item.created_at == antes  # la fecha de radicación no se mueve
    assert "Información agregada después: El medidor es el de la esquina" in estado_de_reclamo(almacen, "ana", "REC-ABCD1234")


def test_no_agrega_a_reclamos_ajenos_ni_a_anonimos_ni_vacios_ni_repetidos():
    almacen = _almacen_con_reclamos()
    assert "no encontré el radicado" in agregar_detalle(almacen, "ana", "REC-99999999", "algo")
    assert "reclamo de Luis" in almacen.get(("reclamos", "luis"), "REC-99999999").value["descripcion"]
    assert "detalles" not in almacen.get(("reclamos", "luis"), "REC-99999999").value  # el de Luis quedó intacto
    assert "no hay un cliente identificado" in agregar_detalle(almacen, "anonimo", "REC-ABCD1234", "algo")
    assert "vacío" in agregar_detalle(almacen, "ana", "REC-ABCD1234", "   ")
    agregar_detalle(almacen, "ana", "REC-ABCD1234", "uno")
    assert "ya estaba agregado" in agregar_detalle(almacen, "ana", "REC-ABCD1234", "uno")


def test_tope_de_detalles_por_reclamo():
    almacen = _almacen_con_reclamos()
    for n in range(5):
        assert agregar_detalle(almacen, "ana", "REC-ABCD1234", f"dato {n}").startswith("Agregado")
    assert "ya tiene 5 detalles" in agregar_detalle(almacen, "ana", "REC-ABCD1234", "dato 6")


def test_esquema_del_detalle_valida_el_radicado_y_el_largo():
    assert set(agregar_detalle_a_reclamo.tool_call_schema.model_json_schema()["properties"]) == {"numero", "detalle"}
    assert DetalleDeReclamo._formato("rec-abcd1234") == "REC-ABCD1234"
    campo = DetalleDeReclamo.model_fields["detalle"]
    assert {type(m).__name__ for m in campo.metadata} >= {"MinLen", "MaxLen"}


from taaml.herramientas_servicio import SolicitudDeAsesor, escalar_a_asesor, solicitar_asesor  # noqa: E402


def test_la_solicitud_de_asesor_se_guarda_con_numero_y_da_los_canales_sin_prometer_tiempos():
    almacen = InMemoryStore()
    r = solicitar_asesor(almacen, "ana", "Quiero hablar con alguien sobre mi factura")
    guardadas = almacen.search(("escalamientos", "ana"))
    assert len(guardadas) == 1 and guardadas[0].key.startswith("ESC-") and guardadas[0].value["motivo"] == "Quiero hablar con alguien sobre mi factura"
    assert guardadas[0].key in r and "01 8000 112 115" in r and "+57 310 390 3468" in r
    assert "no hay una transferencia en vivo" in r and "tiempo de respuesta" in r


def test_la_solicitud_no_se_repite_tiene_tope_y_no_mezcla_clientes():
    almacen = InMemoryStore()
    solicitar_asesor(almacen, "ana", "uno")
    assert "ya estaba registrada" in solicitar_asesor(almacen, "ana", "uno")
    solicitar_asesor(almacen, "ana", "dos")
    solicitar_asesor(almacen, "ana", "tres")
    assert "Ya hay 3 solicitudes" in solicitar_asesor(almacen, "ana", "cuatro")
    assert len(almacen.search(("escalamientos", "ana"))) == 3 and almacen.search(("escalamientos", "luis")) == []


def test_un_anonimo_no_registra_pero_recibe_los_canales_y_el_motivo_vacio_se_rechaza():
    almacen = InMemoryStore()
    r = solicitar_asesor(almacen, "anonimo", "quiero un asesor")
    assert "No pude dejar la solicitud" in r and "01 8000 112 115" in r and almacen.search(("escalamientos", "anonimo")) == []
    assert "falta el motivo" in solicitar_asesor(almacen, "ana", "   ")


def test_el_borrado_del_cliente_tambien_elimina_sus_solicitudes_de_asesor():
    from taaml.agente import olvidar_cliente

    almacen = InMemoryStore()
    solicitar_asesor(almacen, "ana", "quiero un asesor")
    solicitar_asesor(almacen, "luis", "otro")
    assert olvidar_cliente("ana", almacen) == 1
    assert almacen.search(("escalamientos", "ana")) == [] and len(almacen.search(("escalamientos", "luis"))) == 1


def test_esquema_de_la_solicitud():
    assert set(escalar_a_asesor.tool_call_schema.model_json_schema()["properties"]) == {"motivo"}
    campo = SolicitudDeAsesor.model_fields["motivo"]
    assert {type(m).__name__ for m in campo.metadata} >= {"MinLen", "MaxLen"}


from taaml.herramientas_servicio import CalificacionDeAtencion, calificar_atencion, registrar_calificacion  # noqa: E402


def test_la_calificacion_se_guarda_con_numero_puntaje_y_comentario():
    almacen = InMemoryStore()
    r = registrar_calificacion(almacen, "ana", 4, "Me ayudaron rápido")
    guardadas = almacen.search(("calificaciones", "ana"))
    assert len(guardadas) == 1 and guardadas[0].key.startswith("CAL-")
    assert guardadas[0].value == {"puntaje": 4, "comentario": "Me ayudaron rápido"}
    assert guardadas[0].key in r and "4 de 5" in r and "comentario" in r


def test_la_calificacion_sin_comentario_no_dice_que_lo_guardo():
    almacen = InMemoryStore()
    assert "comentario" not in registrar_calificacion(almacen, "ana", 5)


def test_puntajes_fuera_de_rango_o_no_enteros_se_rechazan_y_no_se_guardan():
    almacen = InMemoryStore()
    for malo in (0, 6, -1, True, 3.5):
        assert "de 1 a 5" in registrar_calificacion(almacen, "ana", malo)
    assert almacen.search(("calificaciones", "ana")) == []


def test_la_calificacion_tiene_tope_no_mezcla_clientes_y_el_anonimo_no_guarda():
    almacen = InMemoryStore()
    for _ in range(10):
        registrar_calificacion(almacen, "ana", 3)
    assert "no se guardan más" in registrar_calificacion(almacen, "ana", 3)
    assert len(almacen.search(("calificaciones", "ana"), limit=50)) == 10 and almacen.search(("calificaciones", "luis")) == []
    assert "No pude guardar" in registrar_calificacion(almacen, "anonimo", 5) and almacen.search(("calificaciones", "anonimo")) == []


def test_el_borrado_del_cliente_tambien_elimina_sus_calificaciones():
    from taaml.agente import olvidar_cliente

    almacen = InMemoryStore()
    registrar_calificacion(almacen, "ana", 5)
    registrar_calificacion(almacen, "luis", 2)
    assert olvidar_cliente("ana", almacen) == 1
    assert almacen.search(("calificaciones", "ana")) == [] and len(almacen.search(("calificaciones", "luis"))) == 1


def test_esquema_de_la_calificacion():
    assert set(calificar_atencion.tool_call_schema.model_json_schema()["properties"]) == {"puntaje", "comentario"}
    assert {type(m).__name__ for m in CalificacionDeAtencion.model_fields["puntaje"].metadata} >= {"Ge", "Le"}


from taaml.agente import ConfirmacionDeBorrado, borrar_datos_con_confirmacion, olvidar_datos_del_cliente  # noqa: E402


def _almacen_con_datos():
    almacen = InMemoryStore()
    almacen.put(("perfil", "ana"), "d1", {"dato": "vive en Cali"})
    registrar_calificacion(almacen, "ana", 5)
    solicitar_asesor(almacen, "ana", "quiero un asesor")
    registrar_calificacion(almacen, "luis", 2)
    return almacen


def test_pedir_el_borrado_solo_avisa_y_no_borra():
    almacen = _almacen_con_datos()
    r = borrar_datos_con_confirmacion(almacen, "ana", False)
    assert "confirmación" in r and "1 datos" in r and "1 calificaciones" in r and "1 solicitudes de asesor" in r and "No se puede deshacer" in r
    assert len(almacen.search(("perfil", "ana"))) == 1 and len(almacen.search(("calificaciones", "ana"))) == 1


def test_confirmar_sin_haber_avisado_antes_no_borra_nada():
    almacen = _almacen_con_datos()
    assert "No se borró nada" in borrar_datos_con_confirmacion(almacen, "ana", True)
    assert len(almacen.search(("perfil", "ana"))) == 1


def test_con_aviso_y_confirmacion_borra_todo_de_ese_cliente_y_la_marca_no_sirve_dos_veces():
    almacen = _almacen_con_datos()
    borrar_datos_con_confirmacion(almacen, "ana", False)
    assert "se borraron 3 datos" in borrar_datos_con_confirmacion(almacen, "ana", True)
    for espacio in ("perfil", "calificaciones", "escalamientos", "borrado_pendiente"):
        assert almacen.search((espacio, "ana")) == []
    assert len(almacen.search(("calificaciones", "luis"))) == 1
    assert "No se borró nada" in borrar_datos_con_confirmacion(almacen, "ana", True)


def test_la_marca_de_un_cliente_no_autoriza_el_borrado_de_otro_y_el_anonimo_no_tiene_nada():
    almacen = _almacen_con_datos()
    borrar_datos_con_confirmacion(almacen, "luis", False)
    assert "No se borró nada" in borrar_datos_con_confirmacion(almacen, "ana", True)
    assert "anónimo" in borrar_datos_con_confirmacion(almacen, "anonimo", True)
    assert "nada que borrar" in borrar_datos_con_confirmacion(InMemoryStore(), "ana", False)


def test_esquema_del_borrado():
    assert set(olvidar_datos_del_cliente.tool_call_schema.model_json_schema()["properties"]) == {"confirmo"}
    assert ConfirmacionDeBorrado.model_fields["confirmo"].default is False
