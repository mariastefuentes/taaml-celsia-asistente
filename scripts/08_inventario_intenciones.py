"""Verifica la cobertura del inventario de intenciones contra la base de conocimiento.

Fuente unica: 1 - Analisis de la empresa/inventario_intenciones.csv (editable en Excel).
Las intenciones se definieron DESDE EL ENUNCIADO (horarios, sedes, productos, historia, contacto, procesos basicos),
preguntandose que preguntaria un cliente nuevo, haya o no respuesta. Este script contrasta cada una con la base:
cuenta cuantos documentos la responden (busca su 'regex_cobertura') y deja el resultado en el CSV y en un .md legible.

Uso:  uv run python scripts/08_inventario_intenciones.py
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARPETA = ROOT / "docs" / "1 - Analisis de la empresa"
CSV_PATH = CARPETA / "inventario_intenciones.csv"
MD_PATH = CARPETA / "inventario_intenciones.md"
BASE = ROOT / "data" / "4_curaduria" / "base_conocimiento.txt"
COLUMNAS = ["id", "categoria", "tipo_pregunta", "momento", "intencion", "ejemplos_de_pregunta", "fuente_origen",
            "region", "regex_cobertura", "por_que_no_responde"]
SIN_RESPUESTA = "Sin respuesta en la base"
# los seis primeros son los ejemplos del enunciado; los tres últimos se agregaron al recorrer todo el recorrido del cliente nuevo
TIPOS = ["horarios", "sedes", "productos y servicios", "historia y empresa", "contacto", "procesos básicos",
         "confianza y regulación", "calidad y evaluación", "derechos y datos",
         # agregados al ampliar la base a todo el contenido oficial (no solo lo del cliente nuevo)
         "sostenibilidad y proyectos", "inversionistas y gobierno corporativo", "regulación y autogeneración"]


def main() -> None:
    bloques = re.split(r"(?m)^=== ", BASE.read_text(encoding="utf-8"))[1:]
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f))

    for fila in filas:
        patron = re.compile(fila["regex_cobertura"], re.I)
        n = sum(bool(patron.search(b)) for b in bloques)
        fila["documentos_que_la_responden"] = n
        fila["estado"] = "SIN COBERTURA" if n == 0 else ("cubierta (1 fuente)" if n == 1 else "cubierta")

    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig: Excel muestra bien las tildes
        w = csv.DictWriter(f, fieldnames=COLUMNAS + ["documentos_que_la_responden", "estado"], quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(filas)

    alcance = [f for f in filas if f["categoria"] != SIN_RESPUESTA]
    huecos = [f for f in filas if f["categoria"] == SIN_RESPUESTA]
    sin = [f for f in alcance if f["estado"] == "SIN COBERTURA"]
    una = [f for f in alcance if f["estado"] == "cubierta (1 fuente)"]
    cats: dict[str, list] = {}
    for fila in filas:
        cats.setdefault(fila["categoria"], []).append(fila)
    momentos: dict[str, int] = {}
    for f in alcance:
        momentos[f["momento"]] = momentos.get(f["momento"], 0) + 1

    md = ["# Inventario de intenciones: Celsia (definido desde el recorrido del cliente nuevo)", "",
          "Generado automáticamente desde `inventario_intenciones.csv` (que se puede editar en Excel). "
          "Una **intención** es lo que el cliente quiere lograr.", "",
          "**Cómo se definió.** El enunciado pide definir qué debería poder preguntar un cliente que interactúa por primera vez con la empresa, "
          "y da seis **ejemplos** (horarios, sedes, productos, historia, contacto y procesos básicos). Los ejemplos no son una lista cerrada: "
          "se recorrió todo el trayecto de un cliente nuevo (conocer la empresa, evaluarla, contratar, usar el servicio, resolver problemas) "
          "preguntando qué querría saber una persona nueva (hogar, pyme o empresa), **sin mirar antes si el sitio lo responde**. "
          "Eso hizo aparecer tres tipos más: confianza y regulación, calidad y evaluación, y derechos y datos. "
          "Después se contrastó con la base de conocimiento. Las que no tienen respuesta están al final, con el motivo.", "",
          "**Ampliación del alcance (27/10/2026).** El objetivo del asistente es responder cualquier pregunta que el sitio oficial conteste, "
          "no solo las de un cliente nuevo. Por eso la base pasó de 107 a más de 350 documentos (sostenibilidad, inversionistas, proyectos, "
          "regulación y más) y se agregaron intenciones de esos temas (códigos J) y tres tipos de pregunta nuevos. "
          "Las que antes no tenían respuesta por haber sido excluidas (comprar acciones, quién dirige Celsia, plazo de una PQR) pasaron al alcance.", "",
          "## Resumen por tipo de pregunta", "",
          "| Tipo | Intenciones | Con respaldo | Con una sola fuente | Sin respuesta en la base |", "|---|---|---|---|---|"]
    for t in TIPOS:
        a = [f for f in alcance if f["tipo_pregunta"] == t]
        h = [f for f in huecos if f["tipo_pregunta"] == t]
        md.append(f"| {t} | {len(a)} | {len(a) - len([f for f in a if f['estado'] == 'SIN COBERTURA'])} | "
                  f"{len([f for f in a if f['estado'] == 'cubierta (1 fuente)'])} | {len(h)} |")
    md += ["", f"**Total:** {len(alcance)} intenciones en el alcance ({len(alcance) - len(sin)} con respaldo, {len(una)} con una sola fuente) "
               f"y {len(huecos)} preguntas típicas de un cliente nuevo que hoy la base no responde. "
               "**Momento del cliente** (dentro del alcance): " + "; ".join(f"{k}: {v}" for k, v in sorted(momentos.items())) +
               ". «Primer contacto» es lo que pregunta quien interactúa por primera vez; «cliente actual» quien ya tiene el servicio; «ambos» sirve a los dos.", ""]
    for cat, items in cats.items():
        es_hueco = cat == SIN_RESPUESTA
        md += [f"## {cat} ({len(items)})", ""]
        if es_hueco:
            md += ["Preguntas que un cliente nuevo haría y la base no responde. El asistente debe reconocerlo y remitir a un canal oficial. "
                   "Si alguna llegara a aparecer en el corpus, su estado cambia solo.", "",
                   "| ID | Tipo | Pregunta | Ejemplos | Por qué no se responde |", "|---|---|---|---|---|"]
            for i in items:
                md.append(f"| {i['id']} | {i['tipo_pregunta']} | {i['intencion']} | {i['ejemplos_de_pregunta']} | {i['por_que_no_responde']} |")
        else:
            md += ["| ID | Tipo | Momento | Intención | Ejemplos de pregunta | Región | Fuente de origen | Docs | Estado |", "|---|---|---|---|---|---|---|---|---|"]
            for i in items:
                md.append(f"| {i['id']} | {i['tipo_pregunta']} | {i['momento']} | {i['intencion']} | {i['ejemplos_de_pregunta']} | {i['region']} | "
                          f"{i['fuente_origen']} | {i['documentos_que_la_responden']} | {i['estado']} |")
        md.append("")
    if sin or una:
        md += ["## Atención: cobertura débil", ""]
        md += [f"- **{f['id']}** {f['intencion']}: {f['estado']}" for f in sin + una]
        md.append("")
    MD_PATH.write_text("\n".join(md), encoding="utf-8")

    print(f"{len(alcance)} intenciones en alcance | cubiertas: {len(alcance) - len(sin)} | 1 sola fuente: {len(una)} | sin cobertura: {len(sin)}")
    print(f"{len(huecos)} sin respuesta en la base: " + "; ".join(f"{h['id']}={h['estado']}" for h in huecos))
    print("momentos:", momentos)
    for t in TIPOS:
        a = [f for f in alcance if f["tipo_pregunta"] == t]
        print(f"  {t:24} {len(a):3} intenciones | huecos: {len([h for h in huecos if h['tipo_pregunta'] == t])}")
    for f in sin:
        print(f"  SIN COBERTURA en alcance: {f['id']} {f['intencion']}")


if __name__ == "__main__":
    main()
