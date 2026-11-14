"""HNSW EN UN SERVIDOR QDRANT (clase de bases vectoriales): recall@10 y latencia frente a la búsqueda exacta. No gasta cuota de modelos de pago.

El modo local de Qdrant (el que usa la aplicación) hace búsqueda exacta; el índice aproximado HNSW solo existe en un servidor.
Este script carga los mismos 1.690 vectores en un servidor (por ejemplo `docker run -p 6333:6333 qdrant/qdrant`), construye el grafo con distintos parámetros
y compara cada búsqueda con la exacta del propio servidor (`exact=True`) sobre las preguntas del conjunto de prueba (se vectorizan con Ollama).
  - `m`: vecinos por nodo del grafo.  - `ef_construct`: candidatos al construir.  - `hnsw_ef`: candidatos al consultar (más alto: más recall y más tiempo).
Además mide una búsqueda con filtro por `categoria` (el filtro se aplica durante el recorrido del grafo), frente a la exacta con el mismo filtro.
Uso:  uv run python scripts/29_medir_hnsw_en_servidor.py [url]      (por defecto http://localhost:6333)
Resultado: docs/2 - Conjunto de prueba/resultados/hnsw_servidor.csv. Las colecciones de prueba se borran al terminar.
"""

import csv
import sys
import time
from pathlib import Path

import numpy as np
from qdrant_client import QdrantClient, models

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from taaml.recuperacion import cargar_fragmentos, embeddings  # noqa: E402
from taaml.sinonimos import ampliar_consulta  # noqa: E402

INDICE = ROOT / "data" / "4_curaduria" / "indice_embeddings.npz"
PRUEBA = ROOT / "docs" / "2 - Conjunto de prueba" / "conjunto_de_prueba.csv"
SALIDA = ROOT / "docs" / "2 - Conjunto de prueba" / "resultados" / "hnsw_servidor.csv"
K = 10
CONFIGURACIONES = [
    (4, 16),
    (16, 100),
    (32, 200),
]  # (m, ef_construct): débil, valor por defecto de Qdrant y grande
EFS = (10, 20, 50, 100, 200)
CATEGORIA = "sedes"


def recall(aprox: list[int], exacto: list[int]) -> float:
    return len(set(aprox) & set(exacto)) / len(exacto) if exacto else 1.0


def esperar_indice(cliente: QdrantClient, nombre: str, esperados: int) -> None:
    """Espera a que el optimizador termine y el grafo HNSW cubra los vectores."""
    for _ in range(120):
        info = cliente.get_collection(nombre)
        if (
            str(info.status).lower().endswith("green")
            and (info.indexed_vectors_count or 0) >= esperados
        ):
            return
        time.sleep(1)
    sys.exit(
        f"{nombre}: el índice HNSW no se construyó a tiempo (indexados: {info.indexed_vectors_count})."
    )


def buscar(cliente, nombre, q, ef=None, exacto=False, filtro=None) -> list[int]:
    parametros = (
        models.SearchParams(exact=True) if exacto else models.SearchParams(hnsw_ef=ef)
    )
    r = cliente.query_points(
        nombre,
        query=q.tolist(),
        limit=K,
        search_params=parametros,
        query_filter=filtro,
        with_payload=False,
    )
    return [int(p.id) for p in r.points]


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:6333"
    cliente = QdrantClient(url=url, timeout=120)
    corpus = cargar_fragmentos()
    z = np.load(INDICE, allow_pickle=False)
    if list(z["ids"]) != [f["chunk_id"] for f in corpus]:
        sys.exit(
            "El índice de vectores no corresponde a chunks.jsonl: regenéralo con `make indice`."
        )
    V = z["vectores"].astype(np.float32)
    preguntas = [
        p["pregunta"]
        for p in csv.DictReader(PRUEBA.open(encoding="utf-8-sig", newline=""))
        if p["tipo_prueba"] == "respuesta"
    ]
    Q = np.array(
        embeddings([ampliar_consulta(p) for p in preguntas], "query"), dtype=np.float32
    )
    filas = []
    print(
        f"Servidor {url}: {len(V)} vectores de {V.shape[1]} dimensiones, {len(Q)} preguntas, K={K}\n"
    )
    print(
        f"{'m':>3} {'ef_construct':>12} | {'hnsw_ef':>7} | recall@10 | ms por pregunta | recall@10 con filtro categoria={CATEGORIA}"
    )
    for m, ef_c in CONFIGURACIONES:
        nombre = f"celsia_hnsw_m{m}_efc{ef_c}"
        if cliente.collection_exists(nombre):
            cliente.delete_collection(nombre)
        cliente.create_collection(
            nombre,
            vectors_config=models.VectorParams(
                size=int(V.shape[1]), distance=models.Distance.COSINE
            ),
            hnsw_config=models.HnswConfigDiff(
                m=m, ef_construct=ef_c, full_scan_threshold=10
            ),  # 10 KB (el mínimo): casi nunca cae a búsqueda por fuerza bruta
            optimizers_config=models.OptimizersConfigDiff(
                indexing_threshold=0
            ),  # sin indexar mientras se carga: todos los puntos quedan juntos
        )
        cliente.create_payload_index(
            nombre,
            field_name="categoria",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        puntos = [
            models.PointStruct(
                id=i,
                vector=V[i].tolist(),
                payload={"categoria": corpus[i]["categoria"]},
            )
            for i in range(len(V))
        ]
        for n in range(0, len(puntos), 200):
            cliente.upsert(nombre, points=puntos[n : n + 200], wait=True)
        cliente.update_collection(
            nombre,
            optimizers_config=models.OptimizersConfigDiff(indexing_threshold=1000),
        )  # 1.000 KB < 5,2 MB: ahora sí se construye el grafo
        esperar_indice(cliente, nombre, len(V))
        filtro = models.Filter(
            must=[
                models.FieldCondition(
                    key="categoria", match=models.MatchValue(value=CATEGORIA)
                )
            ]
        )
        exactos = [buscar(cliente, nombre, q, exacto=True) for q in Q]
        exactos_f = [buscar(cliente, nombre, q, exacto=True, filtro=filtro) for q in Q]
        for ef in EFS:
            t0 = time.perf_counter()
            res = [buscar(cliente, nombre, q, ef=ef) for q in Q]
            ms = (time.perf_counter() - t0) / len(Q) * 1000
            r = float(np.mean([recall(a, e) for a, e in zip(res, exactos)]))
            res_f = [buscar(cliente, nombre, q, ef=ef, filtro=filtro) for q in Q]
            r_f = float(np.mean([recall(a, e) for a, e in zip(res_f, exactos_f)]))
            print(f"{m:>3} {ef_c:>12} | {ef:>7} | {r:>9.3f} | {ms:>15.1f} | {r_f:>.3f}")
            filas.append(
                {
                    "m": m,
                    "ef_construct": ef_c,
                    "hnsw_ef": ef,
                    "recall10": round(r, 3),
                    "ms_por_pregunta": round(ms, 1),
                    "recall10_con_filtro": round(r_f, 3),
                }
            )
        t0 = time.perf_counter()
        for q in Q:
            buscar(cliente, nombre, q, exacto=True)
        print(
            f"    búsqueda exacta del servidor: {(time.perf_counter() - t0) / len(Q) * 1000:.1f} ms por pregunta\n"
        )
        cliente.delete_collection(nombre)
    campos = [
        "m",
        "ef_construct",
        "hnsw_ef",
        "recall10",
        "ms_por_pregunta",
        "recall10_con_filtro",
    ]
    with SALIDA.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(filas)
    print(f"Guardado en {SALIDA}")


if __name__ == "__main__":
    main()
