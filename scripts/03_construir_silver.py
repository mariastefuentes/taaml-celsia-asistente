"""CAPA SILVER: del HTML crudo (bronze) al texto util, sin menus, cookies ni duplicados.

- Quita menus, scripts, formularios y repeticiones dentro de cada pagina.
- Descarta paginas con muy poco texto (< 200 caracteres).
- Elimina duplicados EXACTOS entre paginas (mismo texto en URLs distintas) y los registra.
- Nunca modifica bronze. Se puede ejecutar de nuevo en cualquier momento.

Salida: data/2_silver/*.md  y  data/2_silver/_registro.csv (que se hizo con cada archivo de bronze)

Uso:  uv run python scripts/03_construir_silver.py
"""
import csv
import hashlib
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
BRONZE = ROOT / "data" / "1_bronze"
SILVER = ROOT / "data" / "2_silver"
NOISE_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "aside", "form", "iframe", "svg"]
BLOCK_TAGS = ["p", "div", "li", "ul", "ol", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article"]
MIN_CHARS = 200
# preferimos conservar la URL en espanol cuando hay duplicados exactos
PREFERENCIA_EN = re.compile(r"/(investors|about-us|companies|reports|relevant-information|frequent-questions)(/|$)")


def fecha_publicacion(html: str, soup: BeautifulSoup) -> str:
    """Fecha de publicación (AAAA-MM-DD) si la página la trae; vacía si no."""
    m = re.search(r'article:published_time"\s+content="(\d{4}-\d{2}-\d{2})', html) or re.search(r'"datePublished":"(\d{4}-\d{2}-\d{2})', html)
    if m:
        return m.group(1)
    t = re.search(r"(\d{2})\s*·\s*(\d{2})\s*·\s*(\d{4})", soup.get_text(" "))
    return f"{t.group(3)}-{t.group(2)}-{t.group(1)}" if t else ""


def extraer(html: str) -> tuple[str, str, str]:
    soup = BeautifulSoup(html, "lxml")
    fecha = fecha_publicacion(html, soup)
    titulo = soup.find("h1") or soup.find("title")
    titulo = titulo.get_text(" ", strip=True) if titulo else ""
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    for tag in main.find_all(BLOCK_TAGS):
        tag.insert_before("\n")
        tag.insert_after("\n")
    lineas = [re.sub(r"\s+", " ", ln).strip() for ln in main.get_text(" ").splitlines()]
    vistas: set[str] = set()
    conservadas = []
    for ln in lineas:
        if len(ln) < 3 or ln in vistas:  # ruido de carruseles ("1", "/") y lineas repetidas
            continue
        vistas.add(ln)
        conservadas.append(ln)
    return titulo, "\n".join(conservadas).strip(), fecha


def resumen_descubrimiento(filas: list[dict]) -> dict:
    """Cuenta lo que el scraper encontró en los sitemaps: URLs descubiertas, descargadas, bloqueadas por robots.txt y con error HTTP, y el detalle por sección."""
    def estado(r: dict) -> str:
        if "error" not in r:
            return "descargadas"
        return "bloqueadas" if "robots" in r["error"] else "con_error"

    resumen = {"descubiertas": len(filas), "descargadas": 0, "bloqueadas": 0, "con_error": 0, "por_seccion": {}}
    for r in filas:
        e = estado(r)
        resumen[e] += 1
        seccion = resumen["por_seccion"].setdefault(r["section"], {"descubiertas": 0, "descargadas": 0})
        seccion["descubiertas"] += 1
        seccion["descargadas"] += e == "descargadas"
    return resumen


def main() -> None:
    if not any(BRONZE.glob("*.html")):
        raise SystemExit("Falta el HTML crudo en data/1_bronze/ (no se sube a GitHub: pesa unos 250 MB). Descárgalo con scripts/01_scrape_celsia.py; Silver, Gold y la curaduría ya vienen versionados.")
    indice = {}
    filas = [json.loads(ln) for ln in (BRONZE / "_indice.jsonl").read_text(encoding="utf-8").splitlines()]
    for r in filas:
        indice[r["slug"]] = r

    if SILVER.exists():
        for f in SILVER.glob("*.md"):
            f.unlink()
    SILVER.mkdir(parents=True, exist_ok=True)

    candidatos = []  # (slug, url, section, titulo, texto, hash)
    registro = []
    for html_path in sorted(BRONZE.glob("*.html")):
        slug = html_path.stem
        meta = indice.get(slug)
        if not meta:
            registro.append((slug, "", "sin_indice", ""))
            continue
        titulo, texto, fecha = extraer(html_path.read_text(encoding="utf-8", errors="replace"))
        if len(texto) < MIN_CHARS:
            registro.append((slug, meta["url"], "descartada_muy_corta", f"{len(texto)} caracteres"))
            continue
        candidatos.append((slug, meta["url"], meta["section"], titulo, texto, hashlib.sha1(texto.encode("utf-8")).hexdigest(), fecha))

    por_hash: dict[str, list] = {}
    for c in candidatos:
        por_hash.setdefault(c[5], []).append(c)

    escritas = 0
    for grupo in por_hash.values():
        # entre duplicados exactos: primero la URL en espanol, luego la mas corta
        grupo.sort(key=lambda c: (bool(PREFERENCIA_EN.search(c[1])), len(c[1])))
        slug, url, section, titulo, texto, h, fecha = grupo[0]
        (SILVER / f"{slug}.md").write_text(
            f"---\nurl: {url}\ntitle: {titulo}\nsection: {section}\nfecha_publicacion: {fecha}\nhash: {h}\n---\n\n# {titulo}\n\n{texto}\n",
            encoding="utf-8",
        )
        registro.append((slug, url, "conservada", ""))
        escritas += 1
        for dup in grupo[1:]:
            registro.append((dup[0], dup[1], "duplicado_exacto", f"igual a {slug}"))

    (SILVER / "_descubrimiento.json").write_text(json.dumps(resumen_descubrimiento(filas), ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    with (SILVER / "_registro.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["archivo_bronze", "url", "resultado", "detalle"])
        w.writerows(sorted(registro))

    resumen: dict[str, int] = {}
    for r in registro:
        resumen[r[2]] = resumen.get(r[2], 0) + 1
    print(f"Silver: {escritas} documentos. Detalle: {resumen}")

    sedes_silver()


def limpiar(valor) -> str:
    return " ".join(str(valor).split()) if valor else ""


def sedes_silver() -> None:
    """Sedes: desde el JSON crudo de la capa publica de gis.celsia.com a texto legible."""
    crudo = BRONZE / "sedes_raw.json"
    if not crudo.exists():
        return
    campos = ["COUNTRY", "DEPARTMENT", "CITY", "NAME", "HQ_TYPE", "ADDRESS", "PHONE", "SHEDULE", "LATITUDE", "LONGITUDE"]
    sedes = [f["attributes"] for f in json.loads(crudo.read_text(encoding="utf-8"))["features"]]
    sedes = [{c: s.get(c) if c in ("LATITUDE", "LONGITUDE") else limpiar(s.get(c)) for c in campos} for s in sedes]
    sedes.sort(key=lambda s: (s["COUNTRY"], s["DEPARTMENT"], s["CITY"], s["NAME"]))
    (SILVER / "_sedes.json").write_text(json.dumps(sedes, ensure_ascii=False, indent=2), encoding="utf-8")

    lineas, actual = [], None
    for s in sedes:
        zona = f"{s['COUNTRY']} - {s['DEPARTMENT']}"
        if zona != actual:
            actual = zona
            lineas += ["", f"## {zona}", ""]
        partes = [f"**{s['NAME']}** ({s['CITY']}) - {s['HQ_TYPE']}", f"Dirección: {s['ADDRESS'] or 'no disponible'}",
                  f"Horario: {s['SHEDULE'] or 'no disponible'}"]
        if s["PHONE"]:
            partes.append(f"Teléfono: {s['PHONE']}")
        lineas.append("- " + ". ".join(partes))
    texto = "\n".join(lineas).strip()
    titulo = "Puntos de atención y sedes de Celsia"
    h = hashlib.sha1(texto.encode("utf-8")).hexdigest()
    (SILVER / "sedes-puntos-de-atencion.md").write_text(
        f"---\nurl: https://www.celsia.com/es/encuentranos/\ntitle: {titulo}\nsection: sedes\nhash: {h}\n---\n\n# {titulo}\n\n{texto}\n",
        encoding="utf-8",
    )
    print(f"Silver: {len(sedes)} sedes")


if __name__ == "__main__":
    main()
