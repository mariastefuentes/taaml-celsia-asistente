"""Convierte los documentos .md del curso a PDF (con Microsoft Edge en modo sin ventana).

Por defecto convierte solo el documento que se lee o imprimen fuera del repositorio (PDF_DEL_REPOSITORIO: el informe); el resto de docs/ se lee en GitHub como .md. Con --curso recorre también el resto de la carpeta del curso
(bitácora y alistamiento). Solo regenera un PDF si su .md es mas nuevo (o si falta). Usa --force para regenerar todo.

Uso (desde proyecto-taaml):
    uv run python scripts/utilidades/md_a_pdf.py
    uv run python scripts/utilidades/md_a_pdf.py --force
    uv run python scripts/utilidades/md_a_pdf.py --curso
"""
import argparse
import re
import subprocess
import tempfile
import time
from pathlib import Path

import markdown

PROYECTO = Path(__file__).resolve().parents[2]
CURSO = PROYECTO.parents[1]  # ...\TECNICAS AVANZADAS DE IA (solo con --curso)
EXCLUIR = ("Clase 1", "Clase 2", "Clase 3", "Clase 4", "Clase 5", ".venv", ".git")
EDGE = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10.5pt; line-height: 1.5; color: #1f2937; }
h1 { font-size: 20pt; border-bottom: 2px solid #2563eb; padding-bottom: 6px; color: #1e3a8a; }
h2 { font-size: 14.5pt; margin-top: 22px; color: #1e3a8a; border-bottom: 1px solid #d1d5db; padding-bottom: 3px; }
h3 { font-size: 12pt; margin-top: 16px; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9.5pt; page-break-inside: avoid; }
th, td { border: 1px solid #d1d5db; padding: 5px 8px; vertical-align: top; text-align: left; }
th { background: #eff6ff; }
pre { background: #f3f4f6; padding: 10px 12px; border-radius: 4px; font-family: Consolas, 'Courier New', monospace;
      font-size: 8.8pt; line-height: 1.35; page-break-inside: avoid; white-space: pre-wrap; }
code { font-family: Consolas, 'Courier New', monospace; background: #f3f4f6; padding: 1px 4px; border-radius: 3px; font-size: 9.5pt; }
pre code { background: none; padding: 0; }
hr { border: none; border-top: 1px solid #d1d5db; margin: 18px 0; }
li { margin: 2px 0; }
"""
ITEM = re.compile(r"^\s*([-*]|\d+\.)\s")


def a_html(texto: str) -> str:
    # python-markdown exige una linea en blanco antes de una lista (fuera de bloques de codigo)
    salida, en_codigo = [], False
    for ln in texto.splitlines():
        if ln.strip().startswith("```"):
            en_codigo = not en_codigo
        if (not en_codigo and ITEM.match(ln) and salida and salida[-1].strip()
                and not ITEM.match(salida[-1]) and not salida[-1].lstrip().startswith("|")):
            salida.append("")
        salida.append(ln)
    cuerpo = markdown.markdown("\n".join(salida), extensions=["tables", "fenced_code"])
    return f"<!doctype html><html lang='es'><head><meta charset='utf-8'><style>{CSS}</style></head><body>{cuerpo}</body></html>"


PDF_DEL_REPOSITORIO = {"3 - Informe/informe_taller1.md"}


def convertir(md: Path, pdf: Path, edge: str) -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:  # Edge puede tardar en soltar su perfil
        html = Path(tmp) / "doc.html"
        html.write_text(a_html(md.read_text(encoding="utf-8")), encoding="utf-8")
        subprocess.run(
            [edge, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--user-data-dir={Path(tmp) / 'perfil'}",  # perfil propio: con Edge ya abierto, sin esto el PDF no se escribe
             f"--print-to-pdf={pdf}", html.as_uri()],
            check=True, capture_output=True, timeout=120,
        )
        for _ in range(120):  # Edge entrega el PDF unos segundos después de que el comando devuelve
            if pdf.exists() and pdf.stat().st_mtime >= md.stat().st_mtime:
                break
            time.sleep(0.5)
        else:
            raise SystemExit(f"Edge no escribió {pdf.name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="regenerar todos los PDF")
    ap.add_argument("--curso", action="store_true", help="incluir los .md del resto de la carpeta del curso, no solo docs/")
    args = ap.parse_args()

    edge = next((e for e in EDGE if Path(e).exists()), None)
    if not edge:
        raise SystemExit("No se encontro Microsoft Edge.")

    hechos = omitidos = 0
    raiz = CURSO if args.curso else PROYECTO / "docs"
    for md in sorted(raiz.rglob("*.md")):
        if not args.curso and md.relative_to(raiz).as_posix() not in PDF_DEL_REPOSITORIO:
            continue
        if any(p in md.parts or any(p in parte for parte in md.parts) for p in EXCLUIR):
            continue
        if "proyecto-taaml" in md.parts and "docs" not in md.parts:  # del repositorio solo se convierte docs/
            continue
        pdf = md.with_suffix(".pdf")
        if not args.force and pdf.exists() and pdf.stat().st_mtime >= md.stat().st_mtime:
            omitidos += 1
            continue
        convertir(md, pdf, edge)
        print(f"PDF actualizado: {pdf.relative_to(raiz)}")
        hechos += 1
    print(f"Listo: {hechos} actualizados, {omitidos} ya estaban al dia.")


if __name__ == "__main__":
    main()
