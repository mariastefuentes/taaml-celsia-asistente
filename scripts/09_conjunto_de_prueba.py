"""Valida el conjunto de prueba y genera su documento legible.

Fuente unica: 2 - Conjunto de prueba/conjunto_de_prueba.csv (editable en Excel).
Une cada pregunta con su intencion del inventario (tipo de pregunta, momento del cliente, cobertura) y comprueba
automaticamente los criterios acordados:
  - al menos 20 preguntas;
  - al menos la mitad de primer contacto o «ambos»;
  - estan todas las intenciones de primer contacto que dependen de una sola fuente;
  - hay preguntas negativas (sin respuesta o fuera de alcance) para medir si el asistente inventa;
  - hay variedad de formas (directa, coloquial, incompleta, con contexto).

Uso:  uv run python scripts/09_conjunto_de_prueba.py
"""
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TALLER = ROOT / "docs"
INVENTARIO = TALLER / "1 - Analisis de la empresa" / "inventario_intenciones.csv"
CARPETA = TALLER / "2 - Conjunto de prueba"
CSV_PATH = CARPETA / "conjunto_de_prueba.csv"
MD_PATH = CARPETA / "conjunto_de_prueba.md"
COLUMNAS = ["id", "tipo_prueba", "pregunta", "forma", "intencion_id", "region", "respuesta_esperada", "debe_remitir_a", "fuente"]
SIN_RESPUESTA = "Sin respuesta en la base"


def main() -> None:
    inv = {f["id"]: f for f in csv.DictReader(INVENTARIO.open(encoding="utf-8-sig", newline=""))}
    filas = list(csv.DictReader(CSV_PATH.open(encoding="utf-8-sig", newline="")))
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig: Excel muestra bien las tildes
        w = csv.DictWriter(f, fieldnames=COLUMNAS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(filas)

    problemas = []
    for p in filas:
        i = inv.get(p["intencion_id"])
        if p["intencion_id"] != "FUERA" and not i:
            problemas.append(f"{p['id']}: la intención {p['intencion_id']} no existe en el inventario")
        p["_tipo"] = i["tipo_pregunta"] if i else "fuera de alcance"
        p["_momento"] = i["momento"] if i else "ambos"
        p["_estado"] = i["estado"] if i else "fuera de alcance"

    positivas = [p for p in filas if p["tipo_prueba"] == "respuesta"]
    negativas = [p for p in filas if p["tipo_prueba"] == "negativa"]
    primer_o_ambos = [p for p in filas if p["_momento"] in ("primer contacto", "ambos")]
    unica_fuente_pc = [i for i in inv.values() if i["momento"] == "primer contacto" and i["estado"] == "cubierta (1 fuente)"]
    probadas = {p["intencion_id"] for p in filas}
    faltan = [i for i in unica_fuente_pc if i["id"] not in probadas]
    huecos_sin_probar = [i for i in inv.values() if i["categoria"] == SIN_RESPUESTA and i["id"] not in probadas]
    formas = Counter(p["forma"] for p in filas)

    checks = [
        (len(filas) >= 20, f"Al menos 20 preguntas: {len(filas)}"),
        (len(primer_o_ambos) * 2 >= len(filas), f"Al menos la mitad de primer contacto o «ambos»: {len(primer_o_ambos)} de {len(filas)}"),
        (not faltan, "Están las intenciones de primer contacto con una sola fuente: " +
         (f"faltan {', '.join(i['id'] for i in faltan)}" if faltan else f"las {len(unica_fuente_pc)} están")),
        (len(negativas) >= 5, f"Preguntas negativas para medir si inventa: {len(negativas)}"),
        (len(formas) >= 3, "Variedad de formas: " + ", ".join(f"{k} {v}" for k, v in sorted(formas.items()))),
        (not problemas, "Todas las preguntas apuntan a una intención válida" if not problemas else "; ".join(problemas)),
    ]

    md = ["# Conjunto de prueba: asistente Q&A de Celsia", "",
          "Generado automáticamente desde `conjunto_de_prueba.csv` (que se puede editar en Excel).", "",
          "## Qué es y para qué sirve", "",
          "Es una lista de preguntas, escritas como las escribiría un cliente, **con la respuesta que el asistente debería dar**. "
          "Sirve para medir si el asistente funciona: se le hace cada pregunta, se compara su respuesta con la esperada y se anota si acertó. "
          "El taller exige al menos 20 y que se analice la calidad de las respuestas.", "",
          "Tiene dos clases de preguntas:",
          f"- **De respuesta ({len(positivas)}):** la base sí tiene la información. Miden si el asistente la encuentra y la dice bien, sin agregar datos que no están.",
          f"- **Negativas ({len(negativas)}):** la base **no** tiene la información (o es de un cliente en particular). Miden lo más importante contra las alucinaciones: "
          "que el asistente **reconozca que no sabe** y remita a un canal oficial, en vez de inventar.", "",
          "Se escriben de distintas formas (directa, coloquial, incompleta, con contexto) porque los clientes no preguntan como un formulario.", "",
          "## Cómo se califica cada respuesta", "",
          "| Calificación | Significa |", "|---|---|",
          "| Correcta | Dice lo esperado, sin datos inventados |",
          "| Parcial | Acierta pero omite algo importante |",
          "| Incorrecta o inventada | Da un dato que no está en la base o equivocado |",
          "| Reconoce que no sabe *(negativas)* | No inventa y remite al canal indicado: es lo correcto |", "",
          "## Comprobación automática de los criterios", ""]
    md += [f"- {'✅' if ok else '❌'} {txt}" for ok, txt in checks]
    if huecos_sin_probar:
        md += ["", "Preguntas sin respuesta del inventario que **no** están en la prueba (se pueden agregar): " +
               ", ".join(f"{i['id']} ({i['intencion']})" for i in huecos_sin_probar) + "."]
    md += ["", "## Preguntas de respuesta", "",
           "| ID | Pregunta | Forma | Tipo | Momento | Región | Respuesta esperada | Fuente |", "|---|---|---|---|---|---|---|---|"]
    for p in positivas:
        md.append(f"| {p['id']} | {p['pregunta']} | {p['forma']} | {p['_tipo']} | {p['_momento']} | {p['region']} | {p['respuesta_esperada']} | {p['fuente']} |")
    md += ["", "## Preguntas negativas (el asistente debe reconocer que no sabe)", "",
           "| ID | Pregunta | Forma | Qué debe hacer | Debe remitir a | Motivo |", "|---|---|---|---|---|---|"]
    for p in negativas:
        md.append(f"| {p['id']} | {p['pregunta']} | {p['forma']} | {p['respuesta_esperada']} | {p['debe_remitir_a']} | {p['fuente']} |")
    md += ["", "## Registro de resultados", "",
           "Cuando el asistente esté construido, se corre cada pregunta y se anota aquí (o en una copia del CSV): la respuesta que dio, la calificación y un comentario. "
           "El informe debe analizar los aciertos, los errores y las limitaciones que aparezcan.", ""]
    MD_PATH.write_text("\n".join(md), encoding="utf-8")

    print(f"{len(filas)} preguntas: {len(positivas)} de respuesta y {len(negativas)} negativas")
    for ok, txt in checks:
        print(("OK  " if ok else "FALLA ") + txt)
    if huecos_sin_probar:
        print("Sin probar:", ", ".join(i["id"] for i in huecos_sin_probar))


if __name__ == "__main__":
    main()
