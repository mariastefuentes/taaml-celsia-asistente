"""RECUPERACION: mide si los fragmentos que se recuperan para cada pregunta contienen la respuesta. No usa la API del modelo (salvo con --reordenar).

Para cada pregunta de respuesta del conjunto de prueba, toma la intención del inventario a la que apunta y su
`regex_cobertura` (el patrón que identifica un texto que responde esa intención). La recuperación acierta si alguno de
los k fragmentos recuperados cumple el patrón. Se reporta el porcentaje de aciertos (hit@k) por método y también hit@1 y hit@3
(¿la respuesta ya viene en el primer fragmento, o entre los tres primeros?), que dicen si el ranking pone arriba lo que sirve.

Uso:  uv run python scripts/10_evaluar_recuperacion.py             (usa embeddings si hay índice y Ollama responde)
      uv run python scripts/10_evaluar_recuperacion.py --k 5 --detalle
Resultado: docs/2 - Conjunto de prueba/resultados/recuperacion_k<k>.csv (una fila por método y pregunta; las cifras del informe salen de ahí)
          y recuperacion_por_pregunta.md (la misma información en tabla; `--solo-tabla --k 12` la regenera del CSV sin buscar nada)
"""
import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from taaml.recuperacion import buscar  # noqa: E402
from taaml.reordenar import buscar_reordenado  # noqa: E402

TALLER = ROOT / "docs"
INVENTARIO = TALLER / "1 - Analisis de la empresa" / "inventario_intenciones.csv"
PRUEBA = TALLER / "2 - Conjunto de prueba" / "conjunto_de_prueba.csv"
SALIDA = TALLER / "2 - Conjunto de prueba" / "resultados"
TABLA = TALLER / "2 - Conjunto de prueba" / "recuperacion_por_pregunta.md"


def escribir_tabla(filas: list[dict], k: int) -> None:
    """Tabla por pregunta: en qué posición de los k fragmentos aparece la respuesta con cada método («–» si no está)."""
    metodos = list(dict.fromkeys(f["metodo"] for f in filas))
    por_pregunta: dict[str, dict] = {}
    for f in filas:
        por_pregunta.setdefault(f["id"], {"pregunta": f["pregunta"]})[f["metodo"]] = int(f["posicion"])
    lineas = ["# Recuperación por pregunta", "",
              f"En qué posición de los {k} fragmentos recuperados aparece la respuesta (1 = primer fragmento; «–» = no aparece). "
              "Se genera con `scripts/10_evaluar_recuperacion.py --solo-tabla` desde `resultados/recuperacion_k" + str(k) + ".csv`.", "",
              "| Id | Pregunta | " + " | ".join(metodos) + " |", "|---|---|" + "---|" * len(metodos)]
    for id_, d in por_pregunta.items():
        lineas.append(f"| {id_} | {d['pregunta']} | " + " | ".join(str(d[m]) if d[m] else "–" for m in metodos) + " |")
    lineas += ["", "| Total | hit@1 | hit@3 | hit@" + str(k) + " |", "|---|---|---|---|"]
    for m in metodos:
        pos = [d[m] for d in por_pregunta.values()]
        n = len(pos)
        lineas.append(f"| {m} | {sum(0 < x <= 1 for x in pos)} de {n} | {sum(0 < x <= 3 for x in pos)} de {n} | {sum(x > 0 for x in pos)} de {n} ({sum(x > 0 for x in pos) / n:.0%}) |")
    TABLA.write_text(chr(10).join(lineas) + chr(10), encoding="utf-8")
    print(f"Tabla en {TABLA.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--detalle", action="store_true", help="muestra cada pregunta")
    ap.add_argument("--metodos", default="palabras,embeddings,hibrido", help="métodos a comparar, separados por coma")
    ap.add_argument("--reordenar", action="store_true", help="agrega la medición con reordenamiento (una llamada a Gemini por pregunta: gasta cuota)")
    ap.add_argument("--solo-tabla", action="store_true", help="regenera la tabla por pregunta desde el CSV guardado, sin buscar nada")
    a = ap.parse_args()
    if a.solo_tabla:
        ruta = SALIDA / f"recuperacion_k{a.k}.csv"
        escribir_tabla(list(csv.DictReader(ruta.open(encoding="utf-8-sig", newline=""))), a.k)
        return
    inventario = {f["id"]: f for f in csv.DictReader(INVENTARIO.open(encoding="utf-8-sig", newline=""))}
    preguntas = [p for p in csv.DictReader(PRUEBA.open(encoding="utf-8-sig", newline="")) if p["tipo_prueba"] == "respuesta"]
    filas = []
    for metodo in a.metodos.split(",") + (["reordenado"] if a.reordenar else []):
        aciertos, fallos, posiciones, usado = 0, [], [], metodo
        for p in preguntas:
            patron = re.compile(inventario[p["intencion_id"]]["regex_cobertura"], re.I)
            recuperados = buscar_reordenado(p["pregunta"], a.k) if metodo == "reordenado" else buscar(p["pregunta"], a.k, metodo)
            usado = recuperados[0].get("metodo", "reordenado")
            posicion = next((n for n, r in enumerate(recuperados, 1) if patron.search(r["texto"])), 0)  # 0 = no está entre los k
            hit = posicion > 0
            aciertos += hit
            posiciones.append(posicion)
            filas.append({"metodo": metodo, "k": a.k, "id": p["id"], "acierta": int(hit), "posicion": posicion, "pregunta": p["pregunta"]})
            if not hit:
                fallos.append(p)
            if a.detalle:
                print(f"  {'OK ' if hit else 'FALLA'} {p['id']} [{usado}] {p['pregunta'][:70]}")
        print(f"{metodo:<9} (método usado: {usado}): {aciertos} de {len(preguntas)} con la respuesta en los {a.k} primeros fragmentos ({aciertos / len(preguntas):.0%})")
        print(f"{'':<9} hit@1: {sum(0 < x <= 1 for x in posiciones)} de {len(preguntas)} ({sum(0 < x <= 1 for x in posiciones) / len(preguntas):.0%}); "
              f"hit@3: {sum(0 < x <= 3 for x in posiciones)} de {len(preguntas)} ({sum(0 < x <= 3 for x in posiciones) / len(preguntas):.0%})")
        for p in fallos:
            print(f"    no encontró: {p['id']} {p['pregunta'][:80]}")
    if a.metodos == ap.get_default("metodos"):  # solo la corrida completa se guarda: una parcial pisaría las cifras
        ruta = SALIDA / f"recuperacion_k{a.k}.csv"
        with ruta.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0]), quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(filas)
        print(f"Guardado en {ruta.relative_to(ROOT)}")
        escribir_tabla(filas, a.k)


if __name__ == "__main__":
    main()
