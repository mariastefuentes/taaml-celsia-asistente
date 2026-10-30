"""El scraper respeta robots.txt, usa su User-Agent y timeout, espera entre peticiones, es reanudable y registra errores. Sin red."""
import hashlib
import json
import sys

import pytest
import requests

from test_datos import _cargar_script

scraper = _cargar_script("01_scrape_celsia")

ROBOTS = "User-agent: *\nDisallow: /es/privado/\n"
SITEMAP = """<urlset>
<url><loc>https://www.celsia.com/es/factura/</loc></url>
<url><loc>https://www.celsia.com/en/invoice/</loc></url>
<url><loc>https://www.celsia.com/es/privado/documento/</loc></url>
<url><loc>https://www.celsia.com/es/falla/</loc></url>
</urlset>"""


class Respuesta:
    def __init__(self, texto="", codigo=200):
        self.text, self.status_code = texto, codigo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)


class SesionFalsa:
    """Sustituye a requests.Session: responde con páginas de ejemplo y anota cada petición."""
    llamadas: list = []

    def __init__(self):
        self.headers = {}

    def get(self, url, timeout=None):
        SesionFalsa.llamadas.append((url, timeout, dict(self.headers)))
        if url.endswith("robots.txt"):
            return Respuesta(ROBOTS)
        if url.endswith("sitemap.xml"):
            return Respuesta(SITEMAP)
        if url.endswith("/falla/"):
            return Respuesta("", 500)
        return Respuesta(f"<html><body>{url}</body></html>")


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    SesionFalsa.llamadas = []
    pausas = []
    monkeypatch.setattr(scraper.requests, "Session", SesionFalsa)
    monkeypatch.setattr(scraper.time, "sleep", pausas.append)
    monkeypatch.setattr(scraper, "BRONZE", tmp_path)
    monkeypatch.setattr(scraper, "INDICE", tmp_path / "_indice.jsonl")
    return tmp_path, pausas


def correr(monkeypatch, *argumentos):
    monkeypatch.setattr(sys, "argv", ["01_scrape_celsia.py", "--sections", "page", *argumentos])
    scraper.main()


def indice(carpeta):
    return [json.loads(ln) for ln in (carpeta / "_indice.jsonl").read_text(encoding="utf-8").splitlines()]


def test_sitemap_descarta_las_urls_en_ingles():
    urls = scraper.sitemap_urls(SesionFalsa(), "page")
    assert "https://www.celsia.com/en/invoice/" not in urls and len(urls) == 3


def test_usa_su_user_agent_y_un_timeout_en_cada_peticion(entorno, monkeypatch):
    correr(monkeypatch)
    assert SesionFalsa.llamadas and all(timeout == 30 for _, timeout, _ in SesionFalsa.llamadas)
    assert all(cab["User-Agent"] == scraper.UA for _, _, cab in SesionFalsa.llamadas)


def test_no_descarga_lo_que_robots_bloquea_y_lo_deja_registrado(entorno, monkeypatch):
    carpeta, _ = entorno
    correr(monkeypatch)
    assert not any("privado" in url for url, _, _ in SesionFalsa.llamadas)
    bloqueada = next(r for r in indice(carpeta) if "privado" in r["url"])
    assert bloqueada["error"] == "bloqueada por robots.txt" and not (carpeta / f"{bloqueada['slug']}.html").exists()


def test_guarda_el_html_con_codigo_http_y_hash(entorno, monkeypatch):
    carpeta, _ = entorno
    correr(monkeypatch)
    fila = next(r for r in indice(carpeta) if r["url"].endswith("/factura/"))
    archivo = carpeta / f"{fila['slug']}.html"
    assert fila["http"] == 200 and fila["sha1"] == hashlib.sha1(archivo.read_bytes()).hexdigest()


def test_espera_entre_peticiones(entorno, monkeypatch):
    _, pausas = entorno
    correr(monkeypatch, "--delay", "2.5")
    assert pausas and set(pausas) == {2.5}


def test_es_reanudable_y_no_repite_descargas(entorno, monkeypatch):
    correr(monkeypatch)
    primera = [url for url, _, _ in SesionFalsa.llamadas if url.endswith("/factura/")]
    correr(monkeypatch)
    assert primera == [url for url, _, _ in SesionFalsa.llamadas if url.endswith("/factura/")]


def test_una_pagina_que_falla_se_registra_y_el_resto_sigue(entorno, monkeypatch):
    carpeta, _ = entorno
    correr(monkeypatch)
    filas = {r["url"]: r for r in indice(carpeta)}
    assert "error" in filas["https://www.celsia.com/es/falla/"]
    assert filas["https://www.celsia.com/es/factura/"]["http"] == 200


def test_salida_aparte_no_toca_bronze(entorno, monkeypatch, tmp_path):
    carpeta_bronze, _ = entorno
    demo = tmp_path / "demo"
    correr(monkeypatch, "--limit", "1", "--salida", str(demo))
    assert list(demo.glob("*.html")) and (demo / "_indice.jsonl").exists()
    assert not list(carpeta_bronze.glob("_indice.jsonl")) or carpeta_bronze == scraper.BRONZE.parent
