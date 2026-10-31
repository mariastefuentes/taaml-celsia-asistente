from taaml.errores import MENSAJE_API_KEY, MENSAJE_CUOTA, mensaje_error


def test_un_error_de_cuota_muestra_el_mensaje_de_reintento():
    assert mensaje_error(RuntimeError("429 RESOURCE_EXHAUSTED")) == MENSAJE_CUOTA


def test_un_error_de_api_key_muestra_el_mensaje_de_configuracion():
    assert MENSAJE_API_KEY in mensaje_error(RuntimeError("Falta GOOGLE_API_KEY en el archivo .env"))
    assert MENSAJE_API_KEY in mensaje_error(RuntimeError("Falta DEEPSEEK_API_KEY en el archivo .env"))


def test_un_error_de_api_key_no_incluye_el_valor_de_la_clave(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "sk-valor-secreto-de-prueba")
    mensaje = mensaje_error(RuntimeError("Falta GOOGLE_API_KEY en el archivo .env"))
    assert "sk-valor-secreto-de-prueba" not in mensaje


def test_un_error_despues_muestra_el_motivo_sin_valores_de_configuracion():
    error = RuntimeError("ConnectionError connection refused")
    assert mensaje_error(error) == f"No se pudo completar la tarea: {str(error)[:200]}"
