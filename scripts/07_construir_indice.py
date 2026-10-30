"""INDICE: calcula el embedding de cada fragmento de data/4_curaduria/chunks.jsonl con Ollama.

Escribe data/4_curaduria/indice_embeddings.npz (vectores e identificadores de los fragmentos, que sirven de caché) y los carga
en la base vectorial Chroma (data/4_curaduria/chroma), que es donde busca el asistente. Es reanudable: guarda
cada tanda en un archivo temporal, así que si se interrumpe retoma donde quedó. Los fragmentos que no cambiaron
(mismo texto) reutilizan su vector, por lo que reindexar tras un cambio pequeño es rápido.

Requisitos: Ollama encendido y el modelo descargado (`ollama pull nomic-embed-text-v2-moe`).

Uso:  uv run python scripts/07_construir_indice.py
"""
import hashlib
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from taaml.recuperacion import CURADURIA, INDICE, MODELO_EMBEDDINGS, cargar_fragmentos, construir_chroma, embeddings  # noqa: E402
from taaml.sinonimos import etiquetas_fragmento  # noqa: E402

PARCIAL = CURADURIA / "indice_parcial.npz"
TANDA = 8


def huella(texto: str) -> str:
    return hashlib.sha1(f"{MODELO_EMBEDDINGS}|{texto}".encode("utf-8")).hexdigest()


def cargar_vectores_previos() -> dict[str, np.ndarray]:
    previos: dict[str, np.ndarray] = {}
    for archivo in (INDICE, PARCIAL):
        if archivo.exists():
            d = np.load(archivo, allow_pickle=False)
            previos.update(dict(zip(d["huellas"], d["vectores"])))
    return previos


def guardar(ruta: Path, huellas: list[str], ids: list[str], vectores: list[np.ndarray]) -> None:
    np.savez(ruta, huellas=np.array(huellas), ids=np.array(ids), vectores=np.array(vectores, dtype=np.float32))


def main() -> None:
    fragmentos = cargar_fragmentos()
    previos = cargar_vectores_previos()
    # el embedding de cada fragmento lleva sus etiquetas de sinónimos (src/taaml/sinonimos.py); el texto que lee el modelo no cambia
    textos = [f["texto"] + (f"\nTemas relacionados: {e}" if (e := etiquetas_fragmento(f["texto"])) else "") for f in fragmentos]
    huellas = [huella(t) for t in textos]
    pendientes = [i for i, h in enumerate(huellas) if h not in previos]
    print(f"{len(fragmentos)} fragmentos: {len(fragmentos) - len(pendientes)} ya tienen vector, {len(pendientes)} por calcular", flush=True)
    t0 = time.time()
    for n in range(0, len(pendientes), TANDA):
        lote = pendientes[n:n + TANDA]
        vecs = embeddings([textos[i] for i in lote], "document")
        for i, v in zip(lote, vecs):
            previos[huellas[i]] = v
        if (n // TANDA) % 10 == 0 or n + TANDA >= len(pendientes):
            hechos = n + len(lote)
            resto = (time.time() - t0) / hechos * (len(pendientes) - hechos)
            print(f"  {hechos}/{len(pendientes)}  (faltan ~{resto / 60:.0f} min)", flush=True)
            guardar(PARCIAL, list(previos), [""] * len(previos), list(previos.values()))
    guardar(INDICE, huellas, [f["chunk_id"] for f in fragmentos], [previos[h] for h in huellas])
    PARCIAL.unlink(missing_ok=True)
    construir_chroma([f["chunk_id"] for f in fragmentos], np.array([previos[h] for h in huellas], dtype=np.float32),
                     [{"categoria": f["categoria"], "region": f["region"], "fuente": f["fuente"]} for f in fragmentos])
    print(f"Listo: {INDICE.name} con {len(fragmentos)} vectores de {len(previos[huellas[0]])} dimensiones en {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
