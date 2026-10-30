from taaml.sinonimos import ampliar_consulta, etiquetas_fragmento


def test_pregunta_con_atraso_recibe_el_vocabulario_del_sitio():
    ampliada = ampliar_consulta("¿Qué pasa si me atraso con la factura?")
    assert ampliada.startswith("¿Qué pasa si me atraso con la factura?")
    assert "intereses de mora" in ampliada and "reconexión" in ampliada


def test_pregunta_sin_tema_no_cambia():
    assert ampliar_consulta("¿Dónde queda la sede de Tuluá?") == "¿Dónde queda la sede de Tuluá?"


def test_historia_y_valores_se_amplian():
    assert "Colinversiones" in ampliar_consulta("¿Desde cuándo existe Celsia?")
    assert "Cultura Celsia" in ampliar_consulta("¿Cuáles son los valores de Celsia?")


def test_etiquetas_solo_para_fragmentos_que_encajan():
    assert "intereses de mora" in etiquetas_fragmento("Se cobran intereses de mora desde el vencimiento.")
    assert etiquetas_fragmento("Horario de la Tienda Palmira: lunes a viernes.") == ""
