"""CAPA BRONZE: descarga el HTML crudo de celsia.com, sin modificarlo.

- Lee los sitemaps de WordPress (no navega a ciegas).
- Respeta robots.txt (incluye el bloqueo de PDF) y espera entre peticiones.
- Es reanudable: no vuelve a descargar lo que ya esta en data/1_bronze.
- Guarda un indice (data/1_bronze/_indice.jsonl) con la URL, la fecha, el codigo HTTP y el hash (sha1) de cada archivo;
  las paginas bloqueadas por robots.txt y las que fallan tambien quedan registradas (campo `error`), sin archivo HTML.

La limpieza se hace en la capa Silver (03_construir_silver.py) y el enriquecimiento en Gold (04_construir_gold.py).

Uso:
    uv run python scripts/01_scrape_celsia.py --sections page,blog-celsia
    uv run python scripts/01_scrape_celsia.py --sections page --limit 10
    uv run python scripts/01_scrape_celsia.py --sections noticias --filtro "tarifa|factura|estafa"
    uv run python scripts/01_scrape_celsia.py --sections page --limit 5 --salida data/_demo_scraping   # demo, no toca data/1_bronze
"""
import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import hashlib

import requests

BASE = "https://www.celsia.com"
UA = "UAO-TAAML-StudentProject/1.0 (proyecto academico, Maestria IA UAO)"
ROOT = Path(__file__).resolve().parent.parent
BRONZE = ROOT / "data" / "1_bronze"
INDICE = BRONZE / "_indice.jsonl"


def sha1_archivo(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def completar_hash() -> int:
    """Agrega el hash a las filas del indice que no lo tienen (calculado del HTML ya guardado, sin volver a la web)."""
    if not INDICE.exists():
        return 0
    filas, nuevas = [], 0
    for ln in INDICE.read_text(encoding="utf-8").splitlines():
        r = json.loads(ln)
        archivo = BRONZE / f"{r['slug']}.html"
        if "sha1" not in r and archivo.exists():
            r["sha1"], nuevas = sha1_archivo(archivo), nuevas + 1
        filas.append(r)
    if nuevas:
        INDICE.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in filas), encoding="utf-8")
    return nuevas


def registrar(indice, slug: str, url: str, section: str, http: int, **extra) -> None:
    indice.write(json.dumps({"slug": slug, "url": url, "section": section, "http": http,
                             "fetched_at": datetime.now(timezone.utc).isoformat(), **extra}, ensure_ascii=False) + "\n")


def slugify(url: str) -> str:
    path = urlparse(url).path.strip("/") or "home"
    return re.sub(r"[^a-zA-Z0-9]+", "-", path).strip("-").lower()[:120]


def sitemap_urls(session: requests.Session, section: str) -> list[str]:
    r = session.get(f"{BASE}/es/{section}-sitemap.xml", timeout=30)
    r.raise_for_status()
    urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)
    # el sitio replica /es/ en /en/ con el mismo texto en espanol: nos quedamos con /es/
    return [u for u in urls if "/en/" not in u]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sections", default="page", help="sitemaps separados por coma: page,blog-celsia")
    ap.add_argument("--limit", type=int, default=0, help="max paginas por seccion (0 = todas)")
    ap.add_argument("--delay", type=float, default=1.0, help="segundos entre peticiones")
    ap.add_argument("--solo-completar", action="store_true", help="solo agrega el hash al indice existente, sin descargar nada")
    ap.add_argument("--filtro", default="", help="expresion regular: solo descarga las URLs que la cumplan (ej. noticias)")
    ap.add_argument("--salida", default="", help="carpeta donde guardar el HTML y el indice en lugar de data/1_bronze (para demostraciones)")
    args = ap.parse_args()
    if args.salida:
        global BRONZE, INDICE
        BRONZE = Path(args.salida)
        INDICE = BRONZE / "_indice.jsonl"
    if args.solo_completar:
        print(f"Hash agregado a {completar_hash()} filas del indice")
        return
    filtro = re.compile(args.filtro, re.I) if args.filtro else None

    BRONZE.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = UA
    robots = RobotFileParser()
    robots.parse(session.get(f"{BASE}/robots.txt", timeout=30).text.splitlines())

    guardadas = omitidas = bloqueadas = errores = 0
    with INDICE.open("a", encoding="utf-8") as indice:
        for section in args.sections.split(","):
            urls = sitemap_urls(session, section)
            if filtro:
                urls = [u for u in urls if filtro.search(u)]
            if args.limit:
                urls = urls[: args.limit]
            print(f"[{section}] {len(urls)} URLs")
            for url in urls:
                slug = slugify(url)
                if not robots.can_fetch(UA, url):
                    bloqueadas += 1
                    registrar(indice, slug, url, section, 0, error="bloqueada por robots.txt")
                    continue
                destino = BRONZE / f"{slug}.html"
                if destino.exists():
                    omitidas += 1
                    continue
                try:
                    resp = session.get(url, timeout=30)
                    resp.raise_for_status()
                except requests.RequestException as exc:
                    print(f"  ERROR {url}: {exc}")
                    errores += 1
                    registrar(indice, slug, url, section, getattr(exc.response, "status_code", 0), error=str(exc)[:200])
                    time.sleep(args.delay)
                    continue
                destino.write_text(resp.text, encoding="utf-8")
                registrar(indice, slug, url, section, resp.status_code, sha1=sha1_archivo(destino))
                guardadas += 1
                time.sleep(args.delay)
    print(f"Listo: {guardadas} descargadas, {omitidas} ya existian, {bloqueadas} bloqueadas por robots.txt, {errores} con error")


if __name__ == "__main__":
    main()
