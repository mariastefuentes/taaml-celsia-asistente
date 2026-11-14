"""RANKING (clase 7): precision@10, recall@10 y nDCG@10 por método de recuperación. No usa la API del modelo; los embeddings necesitan Ollama.

Un fragmento es relevante si cumple el `regex_cobertura` de la intención a la que apunta la pregunta (el mismo criterio de 10_evaluar_recuperacion.py).
  - precision@10: de los 10 recuperados, qué fracción es relevante.
  - recall@10: de todos los fragmentos relevantes del corpus, qué fracción entró en los 10.
  - nDCG@10: premia que los relevantes estén arriba (descuento 1/log2(posición+1)); 1,0 = orden perfecto.
Uso:  uv run python scripts/21_metricas_ranking.py
Resultado: docs/2 - Conjunto de prueba/resultados/ranking_k10.csv
"""

import csv
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from taaml.recuperacion import buscar, cargar_fragmentos  # noqa: E402

TALLER = ROOT / "docs"
INVENTARIO = TALLER / "1 - Analisis de la empresa" / "inventario_intenciones.csv"
PRUEBA = TALLER / "2 - Conjunto de prueba" / "conjunto_de_prueba.csv"
SALIDA = TALLER / "2 - Conjunto de prueba" / "resultados" / "ranking_k10.csv"
if os.environ.get(
    "TAAML_CURADURIA"
):  # ensayo con otro índice: el resultado se queda en esa carpeta y no pisa el del informe
    SALIDA = Path(os.environ["TAAML_CURADURIA"]) / "ranking_k10.csv"
K = 10
METODOS = ["palabras", "embeddings", "hibrido"]


def ndcg(relevantes: list[int], total_relevantes: int) -> float:
    """`relevantes` es 1/0 por posición recuperada; el ideal pone primero todos los relevantes que caben en K."""
    dcg = sum(r / math.log2(i + 2) for i, r in enumerate(relevantes))
    ideal = sum(1 / math.log2(i + 2) for i in range(min(total_relevantes, K)))
    return dcg / ideal if ideal else 0.0


def main() -> None:
    inventario = {f["id"]: f for f in csv.DictReader(INVENTARIO.open(encoding="utf-8-sig", newline=""))}
    preguntas = [
        p for p in csv.DictReader(PRUEBA.open(encoding="utf-8-sig", newline="")) if p["tipo_prueba"] == "respuesta"
    ]
    corpus = cargar_fragmentos()
    filas = []
    print(f"{'método':<11} | precision@{K} | recall@{K} | nDCG@{K}")
    for metodo in METODOS:
        p_, r_, n_ = [], [], []
        for p in preguntas:
            patron = re.compile(inventario[p["intencion_id"]]["regex_cobertura"], re.I)
            total = sum(1 for f in corpus if patron.search(f["texto"]))
            recuperados = buscar(p["pregunta"], K, metodo)
            if recuperados[0]["metodo"] != metodo:
                sys.exit(
                    f"El método «{metodo}» no se pudo usar (¿Ollama apagado?): se usó «{recuperados[0]['metodo']}»."
                )
            rel = [int(bool(patron.search(r["texto"]))) for r in recuperados]
            p_.append(sum(rel) / K)
            r_.append(sum(rel) / total if total else 0.0)
            n_.append(ndcg(rel, total))
            filas.append(
                {
                    "metodo": metodo,
                    "id": p["id"],
                    "relevantes_en_corpus": total,
                    "relevantes_en_top10": sum(rel),
                    "precision": round(p_[-1], 3),
                    "recall": round(r_[-1], 3),
                    "ndcg": round(n_[-1], 3),
                }
            )
        n = len(preguntas)
        print(f"{metodo:<11} | {sum(p_) / n:>12.3f} | {sum(r_) / n:>9.3f} | {sum(n_) / n:>7.3f}")
    with SALIDA.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(filas)
    print(f"{len(preguntas)} preguntas con respuesta. Guardado en {SALIDA}")


if __name__ == "__main__":
    main()
