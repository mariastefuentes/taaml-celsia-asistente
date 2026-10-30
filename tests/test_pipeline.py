"""Pruebas de las reglas del pipeline de datos (curaduría, limpieza del HTML y fragmentado) con datos de ejemplo, sin tocar data/."""
from datetime import timedelta

from langchain_text_splitters import RecursiveCharacterTextSplitter

import json

from conftest import RAIZ
from test_datos import _cargar_script

curar = _cargar_script("05_curar_base")
silver = _cargar_script("03_construir_silver")
chunks = _cargar_script("06_construir_chunks")


def _doc(**cambios):
    return {"idioma": "es", "caracteres": 5000, "categoria": "servicios", "title": "Pagar la factura", "fecha_publicacion": "", **cambios}


def _divisor(tamano=1000, solape=150):
    return RecursiveCharacterTextSplitter(chunk_size=tamano, chunk_overlap=solape)


# --- curaduría: decidir ---

def test_curaduria_excluye_ingles_y_paginas_sin_texto():
    assert curar.decidir(_doc(idioma="en"))[:2] == (False, "R1")
    assert curar.decidir(_doc(caracteres=curar.MIN_CARACTERES - 1))[:2] == (False, "R8")


def test_curaduria_incluye_por_defecto_el_contenido_oficial_en_espanol():
    assert curar.decidir(_doc())[:2] == (True, "R0")


def test_curaduria_noticia_vieja_o_sin_fecha_se_excluye_y_la_reciente_se_incluye():
    reciente = (curar.FECHA_CAPTURA - timedelta(days=10)).isoformat()
    vieja = (curar.FECHA_CAPTURA - timedelta(days=30 * curar.MESES_VIGENCIA_NOTICIAS + 5)).isoformat()
    noticia = {"categoria": "noticias", "title": "Celsia inaugura una planta"}
    assert curar.decidir(_doc(**noticia, fecha_publicacion=reciente))[:2] == (True, "R7")
    assert curar.decidir(_doc(**noticia, fecha_publicacion=vieja))[:2] == (False, "R7")
    assert curar.decidir(_doc(**noticia))[:2] == (False, "R7")


def test_curaduria_noticia_atemporal_se_incluye_aunque_sea_vieja():
    for titulo in ("Cuidado con la suplantación de Celsia", "Cómo entender la tarifa de energía"):
        assert curar.decidir(_doc(categoria="noticias", title=titulo, fecha_publicacion="2019-01-01"))[:2] == (True, "R7")


# --- limpieza del HTML: extraer ---

HTML = """<html><head><title>Celsia | Factura</title>
<meta property="article:published_time" content="2026-09-15T10:00:00"></head>
<body><header>Menú principal</header><nav>Inicio Contacto</nav>
<main><h1>Paga tu factura</h1><script>var x = 1;</script>
<p>Puedes pagar en línea o en puntos autorizados.</p><p>Puedes pagar en línea o en puntos autorizados.</p>
<ul><li>1</li><li>Línea 01 8000 112 115</li></ul></main>
<footer>Todos los derechos reservados</footer></body></html>"""


def test_extraer_quita_navegacion_scripts_y_pie_y_conserva_el_contenido():
    titulo, texto, _ = silver.extraer(HTML)
    assert titulo == "Paga tu factura"
    assert "Puedes pagar en línea" in texto and "01 8000 112 115" in texto
    for ruido in ("Menú principal", "Inicio Contacto", "var x", "derechos reservados"):
        assert ruido not in texto


def test_extraer_quita_lineas_repetidas_y_ruido_de_carruseles():
    _, texto, _ = silver.extraer(HTML)
    assert texto.count("Puedes pagar en línea") == 1
    assert "1" not in texto.splitlines()


def test_extraer_lee_la_fecha_de_publicacion():
    assert silver.extraer(HTML)[2] == "2026-09-15"
    assert silver.extraer("<html><body><main><p>sin fecha en la página</p></main></body></html>")[2] == ""
    assert silver.extraer("<html><body><p>Publicado 05 · 03 · 2025</p></body></html>")[2] == "2025-03-05"


# --- fragmentado ---

def test_fragmentar_respeta_el_tamano_y_no_pierde_texto():
    texto = " ".join(f"Oración número {n} sobre el servicio de energía." for n in range(120))
    partes = chunks.fragmentar({"text": texto, "categoria": "servicios"}, _divisor())
    assert len(partes) > 1
    assert all(0 < len(p["texto"]) < chunks.TAMANO_POR_DEFECTO + chunks.MINIMO for p in partes)
    assert "Oración número 0 " in partes[0]["texto"] and "Oración número 119 " in partes[-1]["texto"]


def test_fragmentar_pega_el_resto_corto_al_fragmento_anterior():
    texto = ("a" * 900 + " ") * 1 + "b" * 900 + " fin corto"
    partes = chunks.fragmentar({"text": texto, "categoria": "servicios"}, _divisor())
    assert all(len(p["texto"]) >= chunks.MINIMO for p in partes)
    assert partes[-1]["texto"].endswith("fin corto")


def test_fragmentar_un_texto_corto_da_un_solo_fragmento():
    assert len(chunks.fragmentar({"text": "Línea de atención 01 8000 112 115.", "categoria": "servicios"}, _divisor())) == 1


def test_identificador_es_estable_unico_y_acotado():
    assert chunks.identificador("Pagar Factura.md") == chunks.identificador("Pagar Factura.md")
    largos = [chunks.identificador("Documento " + "x" * 100 + sufijo) for sufijo in (" A", " B")]
    assert largos[0] != largos[1] and all(len(i) <= 70 for i in largos)
    assert chunks.identificador("Pagar Factura.md") == "pagar-factura-md"


def _bronze_de_ejemplo(carpeta, paginas):
    """Crea un Bronze mínimo (HTML + índice) con {slug: (url, texto)} y apunta Silver a otra carpeta."""
    bronze, silver_dir = carpeta / "bronze", carpeta / "silver"
    bronze.mkdir()
    filas = []
    for slug, (url, texto) in paginas.items():
        (bronze / f"{slug}.html").write_text(f"<html><head><title>{slug}</title></head><body><main><p>{texto}</p></main></body></html>", encoding="utf-8")
        filas.append(json.dumps({"slug": slug, "url": url, "section": "page", "http": 200, "fetched_at": "2026-10-17T00:00:00+00:00", "sha1": slug}))
    (bronze / "_indice.jsonl").write_text(chr(10).join(filas), encoding="utf-8")
    return bronze, silver_dir


def test_silver_descarta_paginas_casi_vacias_y_duplicados_exactos(tmp_path, monkeypatch):
    largo = "Información de servicio al cliente de Celsia. " * 12
    bronze, silver_dir = _bronze_de_ejemplo(tmp_path, {
        "es-nosotros": ("https://www.celsia.com/es/nosotros/", largo),
        "es-about-us": ("https://www.celsia.com/es/about-us/", largo),
        "es-vacia": ("https://www.celsia.com/es/vacia/", "Hola"),
    })
    monkeypatch.setattr(silver, "BRONZE", bronze)
    monkeypatch.setattr(silver, "SILVER", silver_dir)
    silver.main()
    resultado = {fila.split(",")[0]: fila.split(",")[2] for fila in (silver_dir / "_registro.csv").read_text(encoding="utf-8").splitlines()[1:]}
    assert resultado == {"es-nosotros": "conservada", "es-about-us": "duplicado_exacto", "es-vacia": "descartada_muy_corta"}  # entre duplicados se queda la URL sin ruta en inglés
    assert [f.name for f in silver_dir.glob("*.md")] == ["es-nosotros.md"]


def test_silver_avisa_si_falta_el_html_crudo(tmp_path, monkeypatch):
    import pytest

    monkeypatch.setattr(silver, "BRONZE", tmp_path)
    with pytest.raises(SystemExit, match="scripts/01_scrape_celsia.py"):
        silver.main()


def test_gold_conserva_la_seccion_del_sitemap():
    corpus = [json.loads(ln) for ln in (RAIZ / "data" / "3_gold" / "corpus.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all(d.get("section") for d in corpus)
    assert {d["section"] for d in corpus} >= {"page", "blog-celsia", "noticias"}
