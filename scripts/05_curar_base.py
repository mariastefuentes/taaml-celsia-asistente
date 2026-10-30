"""CURADURIA: de Gold a la base de conocimiento oficial de Celsia.

Criterio: el asistente debe poder responder CUALQUIER pregunta sobre la empresa que su sitio oficial conteste
(no solo las de un cliente nuevo). Por eso se incluye todo el contenido oficial en espanol y se descarta solo
lo que es ruido o esta vencido, con reglas explicitas y ordenadas. Cada documento queda con una decision
(incluido / excluido) y la regla que la produjo, en data/4_curaduria/registro_curaduria.csv.
Nada se borra: Gold sigue intacto, y se puede volver a ejecutar cambiando las reglas.

Reglas:
  R1  excluye lo que esta en ingles (las paginas /en/ son copias de las /es/)
  R6  excluye casi-duplicados (mas de 65 % de palabras en comun), conservando la version en espanol
  R7  noticias: entran las de menos de 12 meses y las atemporales (fraude, explicacion de la tarifa); el resto esta vencido
  R8  excluye paginas con casi nada de texto (menos de 150 caracteres)
  R0  todo lo demas entra
  M0  documentos escritos a mano en data/0_manual/ (datos que el sitio muestra solo como enlaces)

La base completa es muy grande para un solo prompt: el asistente consulta solo los fragmentos relevantes a cada
pregunta (ver src/taaml/recuperacion.py).

Salida:
  data/4_curaduria/base_conocimiento.txt      texto consolidado y ordenado (la base de conocimiento)
  data/4_curaduria/documentos_incluidos.jsonl los mismos documentos, uno por linea, con metadatos
  data/4_curaduria/registro_curaduria.csv     decision y motivo por documento

Uso:  uv run python scripts/05_curar_base.py
"""
import csv
import json
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "data" / "3_gold"
SALIDA = ROOT / "data" / "4_curaduria"
MANUAL = ROOT / "data" / "0_manual"

# R7: las noticias envejecen (lo dicho en una de 2021 suele estar vencido); los avisos de fraude y la explicacion de la tarifa no
MESES_VIGENCIA_NOTICIAS = 12
FECHA_CAPTURA = date(2026, 10, 17)  # primer día del scraping (data/1_bronze/_indice.jsonl: 521 páginas el 17/10, 751 el 27/10 y 1 el 29/10); se deja fija en el 17/10 porque moverla cambiaría qué noticias vencen y con ello el corpus ya evaluado
NOTICIA_ATEMPORAL = re.compile(r"suplant|enga[ñn]ad|estafa|c[oó]mo entender la tarifa", re.I)

MIN_CARACTERES = 150  # R8

# Marcas de URL en ingles: entre dos paginas casi iguales, se prefiere la que NO las tiene
URL_INGLES = re.compile(r"teacher|training|special-projects|improving|about-us|the-new-era|investors|companies|"
                        r"foundation|culture|energy|solutions|efficient|sales|projects", re.I)
UMBRAL_CASI_DUPLICADO = 0.65  # similitud de palabras entre dos documentos para considerarlos el mismo


def fecha_publicacion(d: dict) -> str:
    """Fecha de publicacion para el encabezado, solo en blogs y noticias (en las demas paginas es la del sitio, no la del contenido).
    Permite que el asistente avise cuando un dato viene de un texto antiguo."""
    return f" | publicado: {d['fecha_publicacion']}" if d["categoria"] in ("blog", "noticias") and d.get("fecha_publicacion") else ""


def decidir(d: dict) -> tuple[bool, str, str]:
    """Devuelve (incluir, regla, motivo)."""
    if d["idioma"] == "en":
        return False, "R1", "contenido en inglés"
    if d["caracteres"] < MIN_CARACTERES:
        return False, "R8", f"casi sin texto ({d['caracteres']} caracteres)"
    if d["categoria"] == "noticias":
        if NOTICIA_ATEMPORAL.search(d["title"]):
            return True, "R7", "noticia atemporal: aviso de fraude o explicación de la tarifa"
        fecha = d.get("fecha_publicacion", "")
        corte = (FECHA_CAPTURA - timedelta(days=30 * MESES_VIGENCIA_NOTICIAS)).isoformat()
        if not fecha or fecha < corte:
            return False, "R7", f"noticia con más de {MESES_VIGENCIA_NOTICIAS} meses ({fecha or 'sin fecha'}): vencida"
        return True, "R7", f"noticia reciente ({fecha})"
    return True, "R0", f"categoría {d['categoria']}: contenido oficial en español"


def main() -> None:
    docs = [json.loads(ln) for ln in (GOLD / "corpus.jsonl").read_text(encoding="utf-8").splitlines()]
    SALIDA.mkdir(parents=True, exist_ok=True)

    # primero las páginas en español y más largas, para que ante un casi-duplicado se conserve la mejor
    docs.sort(key=lambda x: (bool(URL_INGLES.search(x["url"])), -x["caracteres"], x["title"]))
    conservados: list[tuple[str, set]] = []
    filas, elegidos, total = [], [], 0
    for d in docs:
        incluir, regla, motivo = decidir(d)
        if incluir:
            palabras = {p for p in re.findall(r"[a-záéíóúñ]{4,}", d["text"].lower())}
            for otro_titulo, otras in conservados:
                if palabras and otras and len(palabras & otras) / len(palabras | otras) >= UMBRAL_CASI_DUPLICADO:
                    incluir, regla, motivo = False, "R6", f"casi duplicado de «{otro_titulo}»"
                    break
            else:
                conservados.append((d["title"], palabras))
        filas.append({"decision": "incluido" if incluir else "excluido", "regla": regla, "motivo": motivo,
                      "categoria": d["categoria"], "region": d["region"], "caracteres": d["caracteres"],
                      "title": d["title"], "archivo": d["archivo"], "url": d["url"]})
        if incluir:
            elegidos.append(d)
    # documentos escritos a mano (datos que el sitio muestra solo como enlaces): siempre incluidos
    for md in sorted(MANUAL.glob("*.md")):
        _, cab, cuerpo = md.read_text(encoding="utf-8").split("---", 2)
        titulo = next(ln.split(": ", 1)[1] for ln in cab.splitlines() if ln.startswith("title: "))
        texto = cuerpo.strip()
        d = {"title": titulo, "categoria": "atencion", "region": "General", "caracteres": len(texto), "text": texto,
             "archivo": md.name, "url": "documento manual (ver encabezado)"}
        filas.append({"decision": "incluido", "regla": "M0", "motivo": "escrito a mano con datos de páginas oficiales",
                      "categoria": "atencion", "region": "General", "caracteres": len(texto),
                      "title": titulo, "archivo": md.name, "url": d["url"]})
        elegidos.append(d)
    elegidos.sort(key=lambda x: (x["categoria"], x["title"]))
    filas.sort(key=lambda f: (f["decision"], f["categoria"], f["title"]))
    bloques = []
    for d in elegidos:
        total += d["caracteres"]
        bloques.append(f"=== {d['title']} | categoría: {d['categoria']} | región: {d['region']}{fecha_publicacion(d)} | fuente: {d['url']} ===\n{d['text']}")

    (SALIDA / "base_conocimiento.txt").write_text("\n\n".join(bloques) + "\n", encoding="utf-8")
    # los mismos documentos, uno por línea y con sus metadatos: insumo del chunking (06_construir_chunks.py)
    with (SALIDA / "documentos_incluidos.jsonl").open("w", encoding="utf-8") as f:
        for d in elegidos:
            f.write(json.dumps({k: d.get(k, "") for k in ("archivo", "title", "categoria", "region", "url", "caracteres", "fecha_publicacion", "text")}, ensure_ascii=False) + "\n")
    with (SALIDA / "registro_curaduria.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)

    inc = [f for f in filas if f["decision"] == "incluido"]
    print(f"Incluidos: {len(inc)} de {len(filas)} documentos, {total:,} caracteres (~{total // 4:,} tokens, estimado como caracteres/4)")
    por_regla: dict[str, int] = {}
    for f in filas:
        k = f"{f['decision']} {f['regla']}"
        por_regla[k] = por_regla.get(k, 0) + 1
    print("Por regla:", dict(sorted(por_regla.items())))
    por_cat: dict[str, list] = {}
    for f in inc:
        c = por_cat.setdefault(f["categoria"], [0, 0])
        c[0] += 1
        c[1] += f["caracteres"]
    print("Incluidos por categoría:", {k: f"{v[0]} docs / {v[1]:,} car." for k, v in por_cat.items()})


if __name__ == "__main__":
    main()
