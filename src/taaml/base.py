"""Acceso a la base de conocimiento curada (data/4_curaduria/).

Un solo lugar para leerla: lo usan la evaluación, las tres tareas y la aplicación.
"""
import json
import re
from pathlib import Path

CURADURIA = Path(__file__).resolve().parents[2] / "data" / "4_curaduria"
BASE = CURADURIA / "base_conocimiento.txt"
DOCUMENTOS = CURADURIA / "documentos_incluidos.jsonl"


def cargar_base(tipo: str = "completa", max_por_doc: int = 600) -> str:
    """Devuelve la base como texto: «completa» (toda la curaduría) o «compacta» (primeros N caracteres por documento)."""
    texto = BASE.read_text(encoding="utf-8")
    if tipo == "completa":
        return texto
    salida = []
    for b in re.split(r"(?m)^(?==== )", texto):
        if not b.strip():
            continue
        cabecera, _, cuerpo = b.partition("\n")
        # los documentos escritos a mano y las sedes ya son compactos: se dejan completos
        if "documento manual" in cabecera or "Puntos de atención y sedes" in cabecera:
            salida.append(b.strip())
        else:
            salida.append(cabecera + "\n" + cuerpo.strip()[:max_por_doc])
    return "\n\n".join(salida)


def cargar_documentos() -> list[dict]:
    """Documentos incluidos tras la curaduría, con título, categoría, fuente y texto."""
    return [json.loads(ln) for ln in DOCUMENTOS.read_text(encoding="utf-8").splitlines()]
