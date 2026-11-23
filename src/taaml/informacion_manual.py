"""Información escrita a mano que el agente entrega tal cual: trámites en línea y la política de datos.

Las dos fuentes viven en el repositorio y llevan su origen: `data/0_manual/tramites_en_linea.csv` (enlaces oficiales revisados) y
`docs/politica_de_privacidad.md` (la política del asistente). No hay red ni modelo: las herramientas solo filtran y devuelven texto.
"""

import csv
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
TRAMITES = RAIZ / "data" / "0_manual" / "tramites_en_linea.csv"
POLITICA = RAIZ / "docs" / "politica_de_privacidad.md"

SIN_RESULTADOS = "Sin resultados en la información disponible."


def _norm(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return sin_tildes.lower().strip()


def tramites_en_linea(texto: str = "", tipo: str = "") -> list[dict]:
    """Trámites y pagos que se pueden hacer en línea, filtrados por texto del nombre o por tipo.

    Cada fila trae el enlace, qué resuelve y de dónde salió; el agente lo cita tal cual.
    """
    with TRAMITES.open(encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f))
    buscado, clase = _norm(texto), _norm(tipo)
    return [
        fila
        for fila in filas
        if (not buscado or buscado in _norm(fila["tramite"]) or buscado in _norm(fila["que_resuelve"]))
        and (not clase or clase in _norm(fila["tipo"]))
    ]


def politica_de_datos(tema: str = "") -> list[str]:
    """Párrafos de la política de privacidad del asistente que tratan el tema (por su título o su texto); sin tema, todo el cuerpo."""
    lineas = POLITICA.read_text(encoding="utf-8").splitlines()
    secciones: list[tuple[str, list[str]]] = [("", [])]
    for linea in lineas:
        if linea.startswith("#"):
            secciones.append((linea.lstrip("# ").strip(), []))
        else:
            secciones[-1][1].append(linea)
    parrafos: list[str] = []
    buscado = _norm(tema)
    for titulo, cuerpo in secciones:
        bloques = [b.strip() for b in "\n".join(cuerpo).split("\n\n") if b.strip()]
        if not buscado:
            parrafos.extend(bloques)
        elif buscado in _norm(titulo):
            parrafos.extend(bloques)  # el tema es el título de la sección: va entera
        else:
            parrafos.extend(b for b in bloques if buscado in _norm(b))
    return parrafos
