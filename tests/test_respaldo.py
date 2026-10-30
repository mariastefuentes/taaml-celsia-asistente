import pytest

from taaml import respaldo
from taaml.respaldo import cadena_de_modelos, con_respaldo, es_falla_del_proveedor, preguntas_guardadas, respuesta_guardada


def test_la_cuota_y_la_conexion_son_fallas_del_proveedor_y_un_error_de_codigo_no():
    assert es_falla_del_proveedor(RuntimeError("429 RESOURCE_EXHAUSTED"))
    assert es_falla_del_proveedor(RuntimeError("Falta GOOGLE_API_KEY en el archivo .env"))
    assert es_falla_del_proveedor(ConnectionError("no hay red"))
    assert not es_falla_del_proveedor(KeyError("campo"))


def test_la_cadena_agrega_deepseek_solo_con_clave_y_siempre_el_local(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert cadena_de_modelos("gemini-3.5-flash") == ["gemini-3.5-flash", "ollama:llama3.2"]
    monkeypatch.setenv("DEEPSEEK_API_KEY", "x")
    assert cadena_de_modelos("gemini-3.5-flash") == ["gemini-3.5-flash", "deepseek-flash", "ollama:llama3.2"]
    assert cadena_de_modelos("deepseek-flash") == ["deepseek-flash", "ollama:llama3.2"]
    assert cadena_de_modelos("ollama:llama3.2") == ["ollama:llama3.2"]


def test_pasa_al_siguiente_modelo_y_avisa(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    llamados = []

    def tarea(modelo):
        llamados.append(modelo)
        if modelo.startswith("gemini"):
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return "ok"

    resultado, usado, avisos = con_respaldo(tarea, "gemini-3.5-flash")
    assert (resultado, usado) == ("ok", "ollama:llama3.2") and llamados == ["gemini-3.5-flash", "ollama:llama3.2"]
    assert "gemini-3.5-flash no respondió" in avisos[0] and "más lento" in avisos[-1]


def test_si_responde_el_primero_no_hay_avisos_ni_se_llama_a_los_demas():
    llamados = []
    resultado, usado, avisos = con_respaldo(lambda m: llamados.append(m) or "ok", "gemini-3.5-flash")
    assert usado == "gemini-3.5-flash" and avisos == [] and llamados == ["gemini-3.5-flash"]


def test_un_error_de_codigo_no_se_esconde_con_otro_modelo():
    with pytest.raises(KeyError):
        con_respaldo(lambda m: {}["x"], "gemini-3.5-flash")


def test_si_fallan_todos_se_propaga_el_ultimo_error(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    def tarea(modelo):
        raise RuntimeError(f"503 UNAVAILABLE {modelo}")

    with pytest.raises(RuntimeError, match="ollama:llama3.2"):
        con_respaldo(tarea, "gemini-3.5-flash")


def test_la_respuesta_guardada_ignora_tildes_y_mayusculas_y_trae_las_fuentes():
    pregunta = preguntas_guardadas()[0]
    guardada = respuesta_guardada(pregunta.upper().replace("Á", "A").replace("É", "E").replace("Ó", "O").replace("¿", "").replace("?", ""))
    assert guardada is not None and guardada[0] and guardada[1] and "fuente" in guardada[1][0]
    assert respuesta_guardada("¿Cuál es la capital de Francia?") is None


def test_sin_archivo_de_resultados_no_hay_respuestas_guardadas(monkeypatch, tmp_path):
    monkeypatch.setattr(respaldo, "RESULTADOS", tmp_path / "no_existe.csv")
    assert preguntas_guardadas() == [] and respuesta_guardada("hola") is None


def test_un_numero_o_una_palabra_suelta_no_se_confunde_con_una_falla_del_proveedor():
    assert not es_falla_del_proveedor(KeyError("campo 4290"))
    assert not es_falla_del_proveedor(ValueError("falta un campo"))
    assert es_falla_del_proveedor(RuntimeError("503 Service Unavailable"))
    assert es_falla_del_proveedor(TimeoutError("timed out"))
