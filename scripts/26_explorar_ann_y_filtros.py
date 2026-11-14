"""BÚSQUEDA EXACTA FRENTE A ANN Y ESTRATEGIAS DE FILTRADO (clase de bases vectoriales). No gasta cuota de modelos de pago; las preguntas se vectorizan con Ollama.

Qdrant en modo local (el que usa el proyecto) hace búsqueda exacta: compara la pregunta con los 1.690 vectores. Un índice aproximado (ANN) como HNSW solo existe en un servidor Qdrant;
aquí se mide, sobre los mismos vectores, qué pierden y qué ahorran dos familias de ANN escritas con NumPy, y cómo se comportan las estrategias de filtrado.

1. IVF (lista invertida): los vectores se agrupan con k-means en `nlist` celdas; la pregunta solo se compara con los de las `nprobe` celdas más cercanas.
2. PQ (cuantización de producto): cada vector de 768 números se parte en 8 trozos y cada trozo se reemplaza por el número de su centroide más cercano (1 byte): 8 bytes por vector.
   La distancia se calcula contra los centroides (ADC); opcionalmente se vuelve a ordenar con los vectores completos los mejores candidatos (reranking).
3. Filtrado por payload (`categoria`): pre-filtrado (se comparan solo los puntos que lo cumplen, como hace Qdrant) frente a post-filtrado (se buscan los K' más parecidos y después se descartan los que no cumplen).
La calidad se mide como recall@10 frente a la búsqueda exacta (cuántos de los 10 vecinos exactos se recuperan).
Uso:  uv run python scripts/26_explorar_ann_y_filtros.py
Resultado: docs/2 - Conjunto de prueba/resultados/ann_y_filtros.csv
"""

import csv
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from taaml.recuperacion import cargar_fragmentos, embeddings  # noqa: E402
from taaml.sinonimos import ampliar_consulta  # noqa: E402

INDICE = ROOT / "data" / "4_curaduria" / "indice_embeddings.npz"
PRUEBA = ROOT / "docs" / "2 - Conjunto de prueba" / "conjunto_de_prueba.csv"
SALIDA = ROOT / "docs" / "2 - Conjunto de prueba" / "resultados" / "ann_y_filtros.csv"
K = 10


def kmeans(X: np.ndarray, k: int, iteraciones: int = 25, semilla: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """k-means (Lloyd) con centroides iniciales tomados de puntos distintos al azar. Devuelve (centroides, asignación)."""
    rng = np.random.default_rng(semilla)
    centroides = X[rng.choice(len(X), size=k, replace=False)].copy()
    for _ in range(iteraciones):
        distancias = (X**2).sum(1)[:, None] - 2 * X @ centroides.T + (centroides**2).sum(1)[None, :]
        asignacion = distancias.argmin(1)
        for j in range(k):
            miembros = X[asignacion == j]
            if len(miembros):
                centroides[j] = miembros.mean(0)
    distancias = (X**2).sum(1)[:, None] - 2 * X @ centroides.T + (centroides**2).sum(1)[None, :]
    return centroides, distancias.argmin(1)


def top_exacto(V: np.ndarray, q: np.ndarray, k: int = K, permitidos: np.ndarray | None = None) -> list[int]:
    puntajes = V @ q
    if permitidos is not None:
        puntajes = np.where(permitidos, puntajes, -np.inf)
    return [int(i) for i in np.argsort(-puntajes)[:k] if np.isfinite(puntajes[i])]


def recall(aprox: list[int], exacto: list[int]) -> float:
    return len(set(aprox) & set(exacto)) / len(exacto) if exacto else 1.0


class IVF:
    def __init__(self, V: np.ndarray, nlist: int):
        self.V, (self.centroides, asignacion) = V, kmeans(V, nlist)
        self.celdas = [np.where(asignacion == j)[0] for j in range(nlist)]

    def buscar(self, q: np.ndarray, nprobe: int, k: int = K) -> tuple[list[int], int]:
        celdas = np.argsort(-(self.centroides @ q))[:nprobe]
        candidatos = np.concatenate([self.celdas[j] for j in celdas])
        mejores = candidatos[np.argsort(-(self.V[candidatos] @ q))[:k]]
        return [int(i) for i in mejores], len(candidatos)


class PQ:
    def __init__(self, V: np.ndarray, m: int = 8, centroides_por_trozo: int = 256):
        self.V, self.m, self.d = V, m, V.shape[1] // m
        self.libros, codigos = [], np.empty((len(V), m), dtype=np.uint8)
        for j in range(m):
            libro, asignacion = kmeans(
                V[:, j * self.d : (j + 1) * self.d], centroides_por_trozo, iteraciones=15, semilla=j
            )
            self.libros.append(libro)
            codigos[:, j] = asignacion
        self.codigos = codigos

    def puntajes(self, q: np.ndarray) -> np.ndarray:
        """Producto punto aproximado (ADC): una tabla de q contra los centroides de cada trozo y una suma por vector."""
        tablas = [self.libros[j] @ q[j * self.d : (j + 1) * self.d] for j in range(self.m)]
        return sum(tablas[j][self.codigos[:, j]] for j in range(self.m))

    def buscar(self, q: np.ndarray, k: int = K, rerank: int = 0) -> list[int]:
        orden = np.argsort(-self.puntajes(q))
        if not rerank:
            return [int(i) for i in orden[:k]]
        candidatos = orden[:rerank]
        return [int(i) for i in candidatos[np.argsort(-(self.V[candidatos] @ q))[:k]]]


def main() -> None:
    corpus = cargar_fragmentos()
    z = np.load(INDICE, allow_pickle=False)
    if list(z["ids"]) != [f["chunk_id"] for f in corpus]:
        sys.exit("El índice de vectores no corresponde a chunks.jsonl: regenéralo con `make indice`.")
    V = z["vectores"].astype(np.float64)
    preguntas = [
        p["pregunta"]
        for p in csv.DictReader(PRUEBA.open(encoding="utf-8-sig", newline=""))
        if p["tipo_prueba"] == "respuesta"
    ]
    Q = np.array(embeddings([ampliar_consulta(p) for p in preguntas], "query"), dtype=np.float64)
    exactos = [top_exacto(V, q) for q in Q]
    filas = []
    mb_completo = V.size * 4 / 1e6

    t0 = time.perf_counter()
    for q in Q:
        top_exacto(V, q)
    t_exacto = (time.perf_counter() - t0) / len(Q) * 1e6
    print(
        f"Búsqueda exacta: {len(V)} vectores de {V.shape[1]} dimensiones, {mb_completo:.1f} MB, {t_exacto:.0f} µs por pregunta, recall 1,000 (es la referencia).\n"
    )
    filas.append(
        {
            "experimento": "exacta",
            "variante": "fuerza bruta",
            "recall10": 1.0,
            "fraccion_comparada": 1.0,
            "microsegundos": round(t_exacto),
            "megabytes": round(mb_completo, 2),
        }
    )

    print("1. IVF (nlist = 41, unos √N)")
    print(f"{'nprobe':<8} | recall@10 | % de vectores comparados | µs por pregunta")
    ivf = IVF(V, 41)
    for nprobe in (1, 2, 4, 8, 16, 41):
        t0 = time.perf_counter()
        resultados = [ivf.buscar(q, nprobe) for q in Q]
        micro = (time.perf_counter() - t0) / len(Q) * 1e6
        r = float(np.mean([recall(res[0], ex) for res, ex in zip(resultados, exactos)]))
        frac = float(np.mean([res[1] for res in resultados])) / len(V)
        print(f"{nprobe:<8} | {r:>9.3f} | {frac:>24.1%} | {micro:>8.0f}")
        filas.append(
            {
                "experimento": "ivf",
                "variante": f"nlist=41 nprobe={nprobe}",
                "recall10": round(r, 3),
                "fraccion_comparada": round(frac, 3),
                "microsegundos": round(micro),
                "megabytes": round(mb_completo + ivf.centroides.size * 4 / 1e6, 2),
            }
        )

    print("\n2. PQ (8 trozos de 96 dimensiones, 256 centroides por trozo)")
    print(f"{'variante':<26} | recall@10 | MB (vectores + libros)")
    pq = PQ(V)
    mb_pq = (pq.codigos.size + sum(libro.size for libro in pq.libros) * 4) / 1e6
    for nombre, rerank in (("PQ solo", 0), ("PQ + reranking de 50", 50), ("PQ + reranking de 100", 100)):
        r = float(np.mean([recall(pq.buscar(q, rerank=rerank), ex) for q, ex in zip(Q, exactos)]))
        mb = mb_pq + (mb_completo if rerank else 0)  # el reranking necesita guardar también los vectores completos
        print(f"{nombre:<26} | {r:>9.3f} | {mb:>6.2f}")
        filas.append({"experimento": "pq", "variante": nombre, "recall10": round(r, 3), "megabytes": round(mb, 2)})
    print(f"(vectores completos: {mb_completo:.2f} MB; solo los códigos de PQ: {pq.codigos.size / 1e6:.3f} MB)")

    print("\n3. Filtrado por categoría: pre-filtrado frente a post-filtrado")
    por_categoria = Counter(f["categoria"] for f in corpus)
    categorias = np.array([f["categoria"] for f in corpus])
    print(f"{'filtro':<20} | cumplen | post-filtrado con K'=10: resultados / recall | K'=50 | K'=200")
    for cat in ("blog", "servicios", "sedes"):
        permitidos = categorias == cat
        pre = [top_exacto(V, q, permitidos=permitidos) for q in Q]
        celdas = []
        for kp in (10, 50, 200):
            post = [[i for i in top_exacto(V, q, k=kp) if permitidos[i]][:K] for q in Q]
            devueltos = float(np.mean([len(p) for p in post]))
            r = float(np.mean([recall(p, e) for p, e in zip(post, pre)]))
            celdas.append(f"{devueltos:>4.1f} de {min(K, por_categoria[cat])} / {r:.3f}")
            filas.append(
                {
                    "experimento": "filtro",
                    "variante": f"{cat} post K'={kp}",
                    "recall10": round(r, 3),
                    "fraccion_comparada": round(por_categoria[cat] / len(V), 3),
                    "resultados_devueltos": round(devueltos, 1),
                }
            )
        print(f"{cat:<20} | {por_categoria[cat]:>3} ({por_categoria[cat] / len(V):>5.1%}) | " + " | ".join(celdas))
        filas.append(
            {
                "experimento": "filtro",
                "variante": f"{cat} pre-filtrado",
                "recall10": 1.0,
                "fraccion_comparada": round(por_categoria[cat] / len(V), 3),
                "resultados_devueltos": float(min(K, por_categoria[cat])),
            }
        )

    campos = [
        "experimento",
        "variante",
        "recall10",
        "fraccion_comparada",
        "microsegundos",
        "megabytes",
        "resultados_devueltos",
    ]
    with SALIDA.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, quoting=csv.QUOTE_ALL, restval="")
        w.writeheader()
        w.writerows(filas)
    print(f"\nGuardado en {SALIDA}")


if __name__ == "__main__":
    main()
