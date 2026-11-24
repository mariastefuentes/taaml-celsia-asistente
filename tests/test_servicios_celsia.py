"""Dos herramientas de servicio: comprobar un canal oficial y estimar la factura (sin modelo ni red)."""

import pytest
from pydantic import ValidationError

from taaml.agente import CanalAVerificar, verificar_canal_oficial
from taaml.agente import FacturaEstimada, calcular_factura_estimada
from taaml.servicios_celsia import factura_estimada, pesos
from taaml.servicios_celsia import verificar_canal

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
