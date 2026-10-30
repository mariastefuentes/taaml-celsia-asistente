from taaml.validacion import datos_sin_respaldo

FRAGMENTOS = [{"texto": "Llama a la Línea de atención 01 8000 112 115 o escribe a servicioalcliente@celsia.com. Tarifa: $1.200 por kWh. "
                        "Más en https://www.celsia.com/es/zona-clientes/.", "fuente": "https://www.celsia.com/es/atencion/"}]


def test_datos_con_respaldo_no_se_marcan():
    respuesta = "Llame al 01 8000 112 115, escriba a servicioalcliente@celsia.com o entre a https://www.celsia.com/es/zona-clientes. Son $1.200 por kWh."
    assert datos_sin_respaldo(respuesta, FRAGMENTOS) == []


def test_cifra_inventada_se_marca():
    assert "999" in datos_sin_respaldo("El cargo es de 999 pesos.", FRAGMENTOS)


def test_correo_y_enlace_inventados_se_marcan():
    respuesta = "Escriba a pagos@celsia-seguro.example.net o vea https://celsia-pagos.example.net/pagar."
    marcados = datos_sin_respaldo(respuesta, FRAGMENTOS)
    assert "pagos@celsia-seguro.example.net" in marcados and "https://celsia-pagos.example.net/pagar" in marcados


def test_numeros_de_una_cifra_y_enumeraciones_no_cuentan():
    assert datos_sin_respaldo("1. Entre a la página.\n2. Pulse el botón en 3 pasos.", FRAGMENTOS) == []


def test_el_formato_del_numero_no_importa():
    assert datos_sin_respaldo("Son 1200 pesos y el teléfono 018000112115.", FRAGMENTOS) == []
