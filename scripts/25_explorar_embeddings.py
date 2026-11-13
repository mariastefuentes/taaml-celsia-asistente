"""EXPLORAR LOS EMBEDDINGS (clase de embeddings): medidas de similitud, recorte Matryoshka y mapa t-SNE. No gasta cuota de ningún modelo de pago; las preguntas
se convierten en vectores con Ollama (local) y los fragmentos salen de data/4_curaduria/indice_embeddings.npz.

1. Similitud: ordena el corpus para cada pregunta con coseno, producto punto y distancia L2 y compara los tres (con vectores de norma 1 dan el mismo orden: ver el informe).
2. Matryoshka: recorta los vectores a las primeras N dimensiones, los vuelve a normalizar y mide precision@10, recall@10 y nDCG@10 con el mismo criterio de relevancia de
   10_evaluar_recuperacion.py y 21_metricas_ranking.py. Solo es válido si el modelo se entrenó con Matryoshka; aquí se mide si el recorte pierde calidad o no.
3. t-SNE: proyecta los fragmentos (y las preguntas) a 2 dimensiones y dibuja un SVG coloreado por categoría. t-SNE está escrito con NumPy (sin dependencias nuevas).
Uso:  uv run python scripts/25_explorar_embeddings.py              (todo)
      uv run python scripts/25_explorar_embeddings.py --sin-tsne   (solo 1 y 2)
Resultados: docs/2 - Conjunto de prueba/resultados/embeddings_similitud_y_matryoshka.csv  y  docs/3 - Informe/tsne_corpus.svg
"""

import csv
import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from taaml.recuperacion import cargar_fragmentos, embeddings  # noqa: E402
from taaml.sinonimos import ampliar_consulta  # noqa: E402

_spec = importlib.util.spec_from_file_location("ranking", ROOT / "scripts" / "21_metricas_ranking.py")
ranking = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(
    ranking
)  # reutiliza K, el criterio de relevancia y nDCG: lo que se mide aquí es lo mismo que allá

INDICE = ROOT / "data" / "4_curaduria" / "indice_embeddings.npz"
SALIDA_CSV = ROOT / "docs" / "2 - Conjunto de prueba" / "resultados" / "embeddings_similitud_y_matryoshka.csv"
SALIDA_SVG = ROOT / "docs" / "3 - Informe" / "tsne_corpus.svg"
DIMENSIONES = [768, 512, 256, 128, 64]
COLORES = [
    "#2563eb",
    "#dc2626",
    "#16a34a",
    "#d97706",
    "#7c3aed",
    "#0891b2",
    "#db2777",
    "#65a30d",
]  # las ocho categorías más grandes; el resto, gris


# --- medidas de similitud ---
def puntajes(medida: str, matriz: np.ndarray, consulta: np.ndarray) -> np.ndarray:
    """Mayor = más parecido, para las tres medidas (la L2 se usa con signo negativo)."""
    if medida == "coseno":
        return (matriz @ consulta) / (np.linalg.norm(matriz, axis=1) * np.linalg.norm(consulta))
    if medida == "producto_punto":
        return matriz @ consulta
    if medida == "l2":
        return -np.linalg.norm(matriz - consulta, axis=1)
    raise ValueError(medida)


def recortar(vectores: np.ndarray, dimensiones: int) -> np.ndarray:
    """Matryoshka: las primeras `dimensiones` coordenadas, vueltas a normalizar a norma 1."""
    corte = vectores[..., :dimensiones]
    return corte / np.linalg.norm(corte, axis=-1, keepdims=True)


def evaluar(
    matriz: np.ndarray, consultas: np.ndarray, medida: str, patrones: list, corpus: list[dict], totales: list[int]
) -> tuple[float, float, float, list[list[int]]]:
    p_, r_, n_, tops = [], [], [], []
    for q, patron, total in zip(consultas, patrones, totales):
        orden = np.argsort(-puntajes(medida, matriz, q))[: ranking.K]
        rel = [int(bool(patron.search(corpus[i]["texto"]))) for i in orden]
        p_.append(sum(rel) / ranking.K)
        r_.append(sum(rel) / total if total else 0.0)
        n_.append(ranking.ndcg(rel, total))
        tops.append(orden.tolist())
    return float(np.mean(p_)), float(np.mean(r_)), float(np.mean(n_)), tops


# --- t-SNE (van der Maaten y Hinton, 2008), exacto, en NumPy ---
def _probabilidades(distancias: np.ndarray, perplejidad: float) -> np.ndarray:
    n = distancias.shape[0]
    P, objetivo = np.zeros((n, n)), np.log(perplejidad)
    for i in range(n):
        d = np.delete(distancias[i], i)
        beta, bajo, alto = 1.0, 0.0, np.inf
        for _ in range(60):  # búsqueda binaria de la precisión que da la perplejidad pedida
            p = np.exp(-d * beta)
            suma = max(p.sum(), 1e-12)
            entropia = np.log(suma) + beta * float((d * p).sum()) / suma
            if abs(entropia - objetivo) < 1e-4:
                break
            if entropia > objetivo:
                bajo, beta = beta, beta * 2 if alto == np.inf else (beta + alto) / 2
            else:
                alto, beta = beta, beta / 2 if bajo == 0 else (beta + bajo) / 2
        P[i, np.arange(n) != i] = p / max(p.sum(), 1e-12)
    return P


def tsne(X: np.ndarray, perplejidad: float = 30.0, iteraciones: int = 750, semilla: int = 0) -> np.ndarray:
    n = X.shape[0]
    centrado = X - X.mean(axis=0)
    _, _, vt = np.linalg.svd(centrado, full_matrices=False)
    Z = centrado @ vt[:50].T  # PCA a 50 dimensiones: acelera y quita ruido, como en el artículo original
    sq = (Z**2).sum(axis=1)
    distancias = np.maximum(sq[:, None] + sq[None, :] - 2 * Z @ Z.T, 0)
    P = _probabilidades(distancias, perplejidad)
    P = np.maximum((P + P.T) / (2 * n), 1e-12)
    rng = np.random.default_rng(semilla)
    Y, delta, ganancias = rng.normal(0, 1e-4, (n, 2)), np.zeros((n, 2)), np.ones((n, 2))
    for it in range(iteraciones):
        exagerar = 12.0 if it < 250 else 1.0  # primeras iteraciones: los grupos se separan más fácil
        sq_y = (Y**2).sum(axis=1)
        num = 1.0 / (1.0 + np.maximum(sq_y[:, None] + sq_y[None, :] - 2 * Y @ Y.T, 0))
        np.fill_diagonal(num, 0)
        Q = np.maximum(num / num.sum(), 1e-12)
        mult = (exagerar * P - Q) * num
        gradiente = 4 * (mult.sum(axis=1)[:, None] * Y - mult @ Y)
        ganancias = np.where((gradiente > 0) != (delta > 0), ganancias + 0.2, ganancias * 0.8)
        ganancias = np.maximum(ganancias, 0.01)
        delta = (0.5 if it < 250 else 0.8) * delta - 200 * ganancias * gradiente
        Y = Y + delta
        Y -= Y.mean(axis=0)
    return Y


def pureza_de_vecindad(X: np.ndarray, categorias: np.ndarray, k: int = 10) -> float:
    """Fracción de los k vecinos más cercanos (distancia euclídea) de cada punto que comparte su categoría: mide si el mapa conserva los grupos."""
    sq = (X**2).sum(axis=1)
    d = np.maximum(sq[:, None] + sq[None, :] - 2 * X @ X.T, 0)
    np.fill_diagonal(d, np.inf)
    vecinos = np.argsort(d, axis=1)[:, :k]
    return float((categorias[vecinos] == categorias[:, None]).mean())


def dibujar_svg(Y: np.ndarray, categorias: list[str], es_pregunta: np.ndarray, ruta: Path) -> None:
    ancho, alto, margen = 960, 640, 30
    mn, mx = np.percentile(Y, 1, axis=0), np.percentile(Y, 99, axis=0)  # los puntos extremos no aplastan el resto
    xy = np.clip((Y - mn) / (mx - mn), 0, 1)
    px = margen + xy[:, 0] * (ancho - 2 * margen)
    py = margen + xy[:, 1] * (alto - 2 * margen - 40)
    grandes = [c for c, _ in Counter(c for c, q in zip(categorias, es_pregunta) if not q).most_common(len(COLORES))]
    color = {c: COLORES[i] for i, c in enumerate(grandes)}
    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" role="img" aria-label="Mapa t-SNE de los fragmentos del corpus coloreados por categoría">',
        f'<rect width="{ancho}" height="{alto}" fill="#ffffff"/>',
    ]
    for x, y, c, q in zip(px, py, categorias, es_pregunta):
        if not q:
            partes.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{color.get(c, "#9ca3af")}" fill-opacity="0.75"/>'
            )
    for x, y, q in zip(px, py, es_pregunta):
        if q:
            partes.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="#111827" stroke="#ffffff" stroke-width="1.2"/>'
            )
    lx = margen
    for c in [*grandes, "otras categorías", "preguntas de prueba"]:
        relleno = color.get(c, "#9ca3af") if c != "preguntas de prueba" else "#111827"
        partes.append(f'<circle cx="{lx + 5}" cy="{alto - 22}" r="5" fill="{relleno}"/>')
        partes.append(
            f'<text x="{lx + 15}" y="{alto - 18}" font-family="sans-serif" font-size="12" fill="#374151">{c}</text>'
        )
        lx += 20 + 6 * len(c)
    partes.append("</svg>")
    ruta.write_text("\n".join(partes), encoding="utf-8")


def main() -> None:
    corpus = cargar_fragmentos()
    z = np.load(INDICE, allow_pickle=False)
    ids = [f["chunk_id"] for f in corpus]
    if list(z["ids"]) != ids:
        sys.exit("El índice de vectores no corresponde a chunks.jsonl: regenéralo con `make indice`.")
    vectores = z["vectores"].astype(np.float64)
    inventario = {f["id"]: f for f in csv.DictReader(ranking.INVENTARIO.open(encoding="utf-8-sig", newline=""))}
    preguntas = [
        p
        for p in csv.DictReader(ranking.PRUEBA.open(encoding="utf-8-sig", newline=""))
        if p["tipo_prueba"] == "respuesta"
    ]
    patrones = [re.compile(inventario[p["intencion_id"]]["regex_cobertura"], re.I) for p in preguntas]
    totales = [sum(1 for f in corpus if pat.search(f["texto"])) for pat in patrones]
    consultas = np.array(embeddings([ampliar_consulta(p["pregunta"]) for p in preguntas], "query"), dtype=np.float64)
    print(
        f"{len(corpus)} fragmentos de {vectores.shape[1]} dimensiones (norma media {np.linalg.norm(vectores, axis=1).mean():.4f}); {len(preguntas)} preguntas.\n"
    )

    filas, tops = [], {}
    print("1. Medidas de similitud (768 dimensiones)")
    print(f"{'medida':<15} | precision@10 | recall@10 | nDCG@10 | mismo top-10 que el coseno")
    for medida in ("coseno", "producto_punto", "l2"):
        p, r, n, top = evaluar(vectores, consultas, medida, patrones, corpus, totales)
        tops[medida] = top
        iguales = sum(set(a) == set(b) for a, b in zip(top, tops["coseno"]))
        print(f"{medida:<15} | {p:>12.3f} | {r:>9.3f} | {n:>7.3f} | {iguales} de {len(preguntas)}")
        filas.append(
            {
                "experimento": "similitud",
                "variante": medida,
                "dimensiones": 768,
                "precision": round(p, 3),
                "recall": round(r, 3),
                "ndcg": round(n, 3),
                "megabytes": round(vectores.size * 4 / 1e6, 1),
                "mismo_top10_que_coseno": iguales,
            }
        )

    print("\n2. Recorte Matryoshka (coseno)")
    print(f"{'dimensiones':<12} | precision@10 | recall@10 | nDCG@10 | MB de vectores")
    for d in DIMENSIONES:
        p, r, n, _ = evaluar(recortar(vectores, d), recortar(consultas, d), "coseno", patrones, corpus, totales)
        mb = vectores.shape[0] * d * 4 / 1e6
        print(f"{d:<12} | {p:>12.3f} | {r:>9.3f} | {n:>7.3f} | {mb:>6.1f}")
        filas.append(
            {
                "experimento": "matryoshka",
                "variante": f"{d}d",
                "dimensiones": d,
                "precision": round(p, 3),
                "recall": round(r, 3),
                "ndcg": round(n, 3),
                "megabytes": round(mb, 1),
            }
        )

    with SALIDA_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "experimento",
                "variante",
                "dimensiones",
                "precision",
                "recall",
                "ndcg",
                "megabytes",
                "mismo_top10_que_coseno",
                "vecinos_misma_categoria",
            ],
            quoting=csv.QUOTE_ALL,
        )
        w.writeheader()
        w.writerows(filas)
    print(f"\nGuardado en {SALIDA_CSV}")

    if "--sin-tsne" in sys.argv:
        return
    print("\n3. t-SNE (exacto, 750 iteraciones; tarda unos minutos)")
    todos = np.vstack([vectores, consultas])
    Y = tsne(todos)
    categorias = [f["categoria"] for f in corpus] + ["pregunta"] * len(preguntas)
    cat = np.array(categorias[: len(corpus)])
    azar = sum((n / len(cat)) ** 2 for n in Counter(cat).values())
    pureza_768, pureza_2d = pureza_de_vecindad(vectores, cat), pureza_de_vecindad(Y[: len(corpus)], cat)
    print(
        f"Vecinos (los 10 más cercanos) de la misma categoría: {pureza_768:.1%} en 768 dimensiones, {pureza_2d:.1%} en el mapa de 2 dimensiones; al azar sería {azar:.1%}."
    )
    with SALIDA_CSV.open("a", encoding="utf-8-sig", newline="") as f:
        csv.writer(f, quoting=csv.QUOTE_ALL).writerows(
            [
                ["tsne", "768d", 768, "", "", "", "", "", round(pureza_768, 3)],
                ["tsne", "mapa_2d", 2, "", "", "", "", "", round(pureza_2d, 3)],
                ["tsne", "azar", "", "", "", "", "", "", round(azar, 3)],
            ]
        )
    dibujar_svg(Y, categorias, np.array([False] * len(corpus) + [True] * len(preguntas)), SALIDA_SVG)
    print(f"Mapa guardado en {SALIDA_SVG}")


if __name__ == "__main__":
    main()
