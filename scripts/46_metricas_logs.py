"""MÉTRICAS DE LA PARTE 1 SOBRE LA BÚSQUEDA Y LOS REGISTROS DE CONVERSACIÓN (reto del Taller 3). No gasta cuota del modelo.

  uv run python scripts/46_metricas_logs.py

A) Ranking con lo que ve el agente (k = 4 fragmentos), embeddings contra mezcla, sobre las 35 preguntas con respuesta del conjunto de prueba:
   hit@4 (¿entró algún fragmento relevante?), MRR@4 (qué tan arriba está el primero) y nDCG@4. Relevante = cumple el `regex_cobertura` de la
   intención, el mismo criterio del script 21. Se comparan con rigor: intervalo de Wilson al 95 % por método y prueba exacta de McNemar
   sobre los pares (misma pregunta, dos métodos). Con 35 preguntas casi nunca hay diferencia significativa: el script lo dice.
B) Registros de conversación (simuladas y reales): tasa de uso de herramientas, de fallos y de revisión humana, con Wilson.
   Las conversaciones reales son de compañeros y conocidos, no de clientes de Celsia: no se pueden presentar como tráfico real.
Resultado: docs/2 - Conjunto de prueba/resultados/metricas_logs.csv
"""

import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from taaml.recuperacion import buscar  # noqa: E402

K = 4
INVENTARIO = ROOT / "docs" / "1 - Analisis de la empresa" / "inventario_intenciones.csv"
PRUEBA = ROOT / "docs" / "2 - Conjunto de prueba" / "conjunto_de_prueba.csv"
SALIDA = ROOT / "docs" / "2 - Conjunto de prueba" / "resultados" / "metricas_logs.csv"
REGISTROS = [
    ("simuladas", ROOT / "data" / "analisis" / "conversaciones.jsonl"),
    ("reales", ROOT / "data" / "analisis" / "reales" / "conversaciones.jsonl"),
]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confianza de Wilson para una proporción k/n."""
    if n == 0:
        return (0.0, 0.0)
    p, d = k / n, 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    mitad = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (centro - mitad, centro + mitad)


def mcnemar_exacto(b: int, c: int) -> float:
    """p-valor bilateral exacto de McNemar: b y c son los pares discordantes (uno acierta y el otro no)."""
    n = b + c
    if n == 0:
        return 1.0
    cola = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2**n
    return min(1.0, 2 * cola)


def mrr_ndcg(rel: list[int], total: int) -> tuple[float, float]:
    primero = next((i for i, r in enumerate(rel) if r), None)
    dcg = sum(r / math.log2(i + 2) for i, r in enumerate(rel))
    ideal = sum(1 / math.log2(i + 2) for i in range(min(total, K)))
    return (1 / (primero + 1) if primero is not None else 0.0, dcg / ideal if ideal else 0.0)


def parte_ranking(filas: list[dict]) -> None:
    import re

    from taaml.recuperacion import cargar_fragmentos

    inventario = {f["id"]: f for f in csv.DictReader(INVENTARIO.open(encoding="utf-8-sig", newline=""))}
    preguntas = [p for p in csv.DictReader(PRUEBA.open(encoding="utf-8-sig", newline="")) if p["tipo_prueba"] == "respuesta"]
    corpus = cargar_fragmentos()
    res: dict[str, list[tuple[int, float, float]]] = {"embeddings": [], "mezcla": []}
    for p in preguntas:
        patron = re.compile(inventario[p["intencion_id"]]["regex_cobertura"], re.I)
        total = sum(1 for f in corpus if patron.search(f["texto"]))
        for metodo in res:
            rel = [1 if patron.search(f["texto"]) else 0 for f in buscar(p["pregunta"], K, metodo)]
            mrr, ndcg = mrr_ndcg(rel, total)
            res[metodo].append((1 if any(rel) else 0, mrr, ndcg))
    n = len(preguntas)
    print(f"\nA) Ranking a k={K} sobre {n} preguntas")
    print(f"{'método':<11} | hit@{K} (Wilson 95 %)      | MRR@{K} | nDCG@{K}")
    for metodo, v in res.items():
        hits = sum(x[0] for x in v)
        lo, hi = wilson(hits, n)
        mrr, ndcg = sum(x[1] for x in v) / n, sum(x[2] for x in v) / n
        print(f"{metodo:<11} | {hits}/{n} = {hits / n:.3f} [{lo:.3f}, {hi:.3f}] | {mrr:.3f} | {ndcg:.3f}")
        filas.append({"parte": "ranking", "grupo": metodo, "n": n, "exitos": hits, "tasa": round(hits / n, 3),
                      "wilson_bajo": round(lo, 3), "wilson_alto": round(hi, 3), "mrr": round(mrr, 3), "ndcg": round(ndcg, 3)})
    b = sum(1 for e, m in zip(res["embeddings"], res["mezcla"]) if e[0] and not m[0])
    c = sum(1 for e, m in zip(res["embeddings"], res["mezcla"]) if m[0] and not e[0])
    p_val = mcnemar_exacto(b, c)
    veredicto = "diferencia significativa" if p_val < 0.05 else "sin diferencia significativa (con esta muestra no se distingue de la suerte)"
    print(f"McNemar exacto: solo embeddings acierta en {b}, solo mezcla en {c}, p = {p_val:.3f} -> {veredicto}")
    filas.append({"parte": "mcnemar", "grupo": "embeddings_vs_mezcla", "n": n, "exitos": c, "tasa": p_val,
                  "wilson_bajo": b, "wilson_alto": c, "mrr": "", "ndcg": ""})


def parte_registros(filas: list[dict]) -> None:
    print("\nB) Registros de conversación")
    for nombre, ruta in REGISTROS:
        if not ruta.exists():
            print(f"{nombre}: no hay archivo ({ruta.name})")
            continue
        hilos = [json.loads(linea) for linea in ruta.open(encoding="utf-8") if linea.strip()]
        n = len(hilos)
        for etiqueta, cuenta in (
            ("usó herramientas", sum(1 for h in hilos if h.get("herramientas"))),
            ("falló", sum(1 for h in hilos if h.get("fallida"))),
            ("pasó a revisión humana", sum(1 for h in hilos if h.get("en_revision"))),
        ):
            lo, hi = wilson(cuenta, n)
            print(f"{nombre:<10} {etiqueta:<24} {cuenta:>3}/{n} = {cuenta / max(n, 1):.3f} [{lo:.3f}, {hi:.3f}]")
            filas.append({"parte": "registros", "grupo": f"{nombre}: {etiqueta}", "n": n, "exitos": cuenta,
                          "tasa": round(cuenta / max(n, 1), 3), "wilson_bajo": round(lo, 3), "wilson_alto": round(hi, 3),
                          "mrr": "", "ndcg": ""})


def main() -> None:
    filas: list[dict] = []
    parte_ranking(filas)
    parte_registros(filas)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with SALIDA.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(filas)
    print(f"\nGuardado en {SALIDA}")


if __name__ == "__main__":
    main()
