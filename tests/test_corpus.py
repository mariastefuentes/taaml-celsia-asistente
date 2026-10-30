"""Las cifras de la pestaña «Corpus y scraping» salen de los archivos de data/ y cada etapa conserva la cuenta."""
from taaml import corpus
from taaml.corpus import metricas

M = metricas()


def test_cada_etapa_conserva_la_cuenta():
    for e in M["etapas"][:4]:  # descubrir, extraer, limpiar y deduplicar: entra − descartes = sale
        assert e["entra"] - sum(e["descartes"].values()) == e["sale"], e["etapa"]
    curar = next(e for e in M["etapas"] if e["etapa"].startswith("6."))
    assert curar["entra"] - sum(curar["descartes"].values()) == curar["sale"]


def test_las_etapas_se_encadenan():
    etapas = M["etapas"]
    assert etapas[1]["entra"] == etapas[0]["sale"]
    assert etapas[2]["entra"] == etapas[1]["sale"]
    assert etapas[3]["entra"] == etapas[2]["sale"]
    assert etapas[4]["entra"] == etapas[3]["sale"]  # Gold parte de lo que quedó en Silver
    assert etapas[6]["entra"] == etapas[5]["sale"]  # se fragmenta lo curado


def test_las_cifras_coinciden_con_las_del_informe():
    assert (M["paginas_descargadas"], M["paginas_en_silver"], M["documentos"], M["fragmentos"]) == (1272, 1100, 393, 1690)
    assert sum(M["por_categoria"].values()) == M["documentos"]


def test_los_tokens_son_los_del_corpus(monkeypatch):
    assert 310_000 < M["tokens"] < 325_000 or not M["tokens_con_o200k"]  # ~316.800 con o200k
    import tiktoken

    def sin_red(*args, **kwargs):
        raise OSError("sin red")

    monkeypatch.setattr(tiktoken, "get_encoding", sin_red)
    estimado = corpus.metricas()
    assert not estimado["tokens_con_o200k"] and 280_000 < estimado["tokens"] < 360_000  # respaldo: caracteres/4, cerca del valor exacto
    monkeypatch.setattr(corpus, "_tokens", lambda incluidos: (1, False))
    assert corpus.metricas()["tokens"] == 1


def test_todo_descarte_tiene_motivo_legible():
    assert set(corpus.MOTIVOS) >= {k for e in M["etapas"] for k in e["descartes"]}
    assert all(v > 0 for v in M["descartes"].values())


def test_descubrir_separa_bloqueadas_y_con_error():
    descubrir, extraer = M["etapas"][0], M["etapas"][1]
    assert (descubrir["entra"], descubrir["sale"]) == (1273, 1273)
    assert (extraer["entra"], extraer["sale"]) == (1273, 1272)
    assert extraer["descartes"] == {"error_http": 1}  # un 500 del propio sitio; robots.txt no bloqueó ninguna
    assert M["paginas_descubiertas"] == 1273


def test_resumen_del_descubrimiento_cuenta_cada_estado():
    from importlib import util
    from pathlib import Path

    ruta = Path(__file__).resolve().parents[1] / "scripts" / "03_construir_silver.py"
    spec = util.spec_from_file_location("silver", ruta)
    modulo = util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    filas = [{"section": "page"}, {"section": "page", "error": "bloqueada por robots.txt"},
             {"section": "noticias", "error": "500 Server Error"}, {"section": "noticias"}]
    r = modulo.resumen_descubrimiento(filas)
    assert (r["descubiertas"], r["descargadas"], r["bloqueadas"], r["con_error"]) == (4, 2, 1, 1)
    assert r["por_seccion"] == {"page": {"descubiertas": 2, "descargadas": 1}, "noticias": {"descubiertas": 2, "descargadas": 1}}


def test_las_primeras_cinco_etapas_son_las_del_scraping():
    nombres = [e["etapa"].split(". ")[1].split(" ")[0] for e in M["etapas"] if e["bloque"] == corpus.SCRAPING]
    assert nombres == ["Descubrir", "Extraer", "Limpiar", "Deduplicar", "Enriquecer"]
    assert [e["etapa"].split(". ")[1] for e in M["etapas"] if e["bloque"] == corpus.RAG] == ["Curar", "Fragmentar"]
