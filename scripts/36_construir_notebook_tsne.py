"""Construye y ejecuta `notebooks/analisis_conversaciones.ipynb` (Ruta Transversal A: conversaciones con t-SNE).

  uv sync --group analisis
  uv run python scripts/36_construir_notebook_tsne.py

Necesita Ollama encendido (embeddings) la primera vez; después usa `data/analisis/embeddings.npy`. El texto del análisis vive en
`notebooks/analisis_conversaciones.md` y se pega en la última celda: así se puede reescribir sin tocar el código del notebook.
"""

from pathlib import Path

import nbformat
from nbclient import NotebookClient

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "notebooks" / "analisis_conversaciones.ipynb"
ANALISIS = RAIZ / "notebooks" / "analisis_conversaciones.md"

INTRO = """# Análisis de conversaciones con t-SNE (Ruta Transversal A)

**Qué hace este cuaderno.** Toma las conversaciones completas del asistente de Celsia, convierte cada una en un vector con el mismo
modelo de embeddings que usa el agente para buscar, y las proyecta a 2D y 3D con t-SNE para ver qué tipos de conversación se parecen
entre sí y dónde le va mal al asistente.

**Aviso: los datos son simulados.** No hay clientes reales: escribimos 114 conversaciones de ejemplo (preguntas de producto, facturas,
reclamos, temas fuera de alcance, saludos, datos personales, mensajes hostiles o ambiguos y conversaciones mezcladas) y las pasamos por
el agente real con `scripts/35_simular_conversaciones.py`. Las respuestas, las herramientas y los fallos sí son del agente; las
preguntas no. Con la API en producción el mismo código (`taaml.conversaciones`) lee las conversaciones reales de PostgreSQL.

La categoría «prevista» es la que quisimos probar al escribir cada conversación. Los clústeres se calculan **sin** mirarla; después se
comparan, y esa comparación es la prueba de que los vectores capturan el tema de la conversación."""

CARGA = """import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path.cwd() if (Path.cwd() / "data").exists() else Path.cwd().parent
df = pd.DataFrame([json.loads(l) for l in (RAIZ / "data/analisis/conversaciones.jsonl").read_text(encoding="utf-8").splitlines()])
df["turnos_cliente"] = df["turnos"].map(lambda t: sum(x["rol"] == "cliente" for x in t))
df["primera_pregunta"] = df["turnos"].map(lambda t: t[0]["texto"][:70])
print(len(df), "conversaciones;", int(df["fallida"].sum()), "marcadas como fallidas")
df["categoria_prevista"].value_counts().to_frame("conversaciones")"""

EMBEDDINGS = """from taaml.recuperacion import MODELO_EMBEDDINGS
from taaml.vectorstore import embeddings_celsia

CACHE = RAIZ / "data/analisis/embeddings.npy"
if CACHE.exists() and np.load(CACHE).shape[0] == len(df):
    X = np.load(CACHE)
else:
    X = np.array(embeddings_celsia(MODELO_EMBEDDINGS).incrustar(df["texto"].tolist(), "document"), dtype=np.float32)
    np.save(CACHE, X)
X.shape"""

TSNE2 = """import matplotlib.pyplot as plt
from sklearn.manifold import TSNE

PERPLEJIDAD = 12  # con ~114 puntos, entre 5 y 30; 12 separa los temas sin partir cada uno en pedazos
Y2 = TSNE(n_components=2, perplexity=PERPLEJIDAD, metric="cosine", init="pca", random_state=0).fit_transform(X)
df["x"], df["y"] = Y2[:, 0], Y2[:, 1]

fig, ax = plt.subplots(figsize=(11, 8))
colores = plt.get_cmap("tab10")
for i, (cat, g) in enumerate(df.groupby("categoria_prevista")):
    ok, mal = g[~g["fallida"]], g[g["fallida"]]
    ax.scatter(ok["x"], ok["y"], s=55, color=colores(i), label=cat, alpha=0.85)
    ax.scatter(mal["x"], mal["y"], s=110, facecolors="none", edgecolors="black", linewidths=1.6)
ax.scatter([], [], s=110, facecolors="none", edgecolors="black", linewidths=1.6, label="conversación fallida")
ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), title="Categoría prevista")
ax.set_title("t-SNE 2D de las conversaciones (datos simulados)")
ax.set_xticks([]); ax.set_yticks([])
plt.tight_layout(); plt.show()"""

TSNE3 = """Y3 = TSNE(n_components=3, perplexity=PERPLEJIDAD, metric="cosine", init="pca", random_state=0).fit_transform(X)
fig = plt.figure(figsize=(11, 8))
ax = fig.add_subplot(projection="3d")
for i, (cat, g) in enumerate(df.groupby("categoria_prevista")):
    idx = g.index
    ax.scatter(Y3[idx, 0], Y3[idx, 1], Y3[idx, 2], s=40, color=colores(i), label=cat, alpha=0.85)
mal = df.index[df["fallida"]]
ax.scatter(Y3[mal, 0], Y3[mal, 1], Y3[mal, 2], s=110, facecolors="none", edgecolors="black", linewidths=1.2, label="fallida")
ax.legend(loc="center left", bbox_to_anchor=(1.05, 0.5))
ax.set_title("t-SNE 3D de las conversaciones (datos simulados)")
plt.tight_layout(); plt.show()"""

CLUSTERS = """from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score

K = 9  # una por categoría prevista; el algoritmo no ve las etiquetas
df["cluster"] = KMeans(n_clusters=K, n_init=10, random_state=0).fit_predict(X)
print("Coincidencia entre clústeres y categorías previstas (índice de Rand ajustado, 1 = idéntico):",
      round(adjusted_rand_score(df["categoria_prevista"], df["cluster"]), 2))

resumen = df.groupby("cluster").agg(
    conversaciones=("hilo", "size"),
    fallidas=("fallida", "sum"),
    en_revision=("en_revision", "sum"),
    categoria_dominante=("categoria_prevista", lambda s: s.value_counts().index[0]),
    pureza=("categoria_prevista", lambda s: round(s.value_counts().iloc[0] / len(s), 2)),
    ejemplo=("primera_pregunta", "first"),
)
resumen["tasa_de_fallo"] = (resumen["fallidas"] / resumen["conversaciones"]).round(2)
resumen.sort_values("tasa_de_fallo", ascending=False)"""

KNN = """from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.neighbors import KNeighborsClassifier

etiquetas = df["categoria_prevista"]


def acierto(M, metrica="euclidean", k=5):
    # cada conversación se clasifica con sus k vecinas más cercanas, sin contarse a sí misma (dejar uno fuera)
    pred = cross_val_predict(KNeighborsClassifier(n_neighbors=k, metric=metrica), M, etiquetas, cv=LeaveOneOut())
    return round(float((pred == etiquetas).mean()), 2)


comparacion = pd.DataFrame(
    {
        "espacio": ["vectores originales (768 dimensiones, coseno)", "t-SNE en 3D", "t-SNE en 2D", "azar (siempre la categoría más común)"],
        "acierto_de_KNN": [acierto(X, "cosine"), acierto(Y3), acierto(Y2), round(float(etiquetas.value_counts(normalize=True).iloc[0]), 2)],
    }
)
comparacion"""

VECINAS = """# Las 5 conversaciones más parecidas a un reclamo, en el espacio original (esto sí es una búsqueda, no un dibujo)
S = X @ X.T  # los vectores tienen norma 1: el producto punto es el coseno
i = df.index[df["categoria_prevista"] == "reclamo"][0]
orden = [j for j in np.argsort(-S[i]) if j != i][:5]
print("Conversación de referencia:", df.loc[i, "primera_pregunta"])
df.loc[orden, ["categoria_prevista", "primera_pregunta"]].assign(coseno=S[i, orden].round(2))"""

FALLOS = """pd.set_option("display.max_colwidth", 110)
df[df["fallida"]][["categoria_prevista", "cluster", "primera_pregunta"]].sort_values("categoria_prevista")"""

TASA = """tasa = df.groupby("categoria_prevista")["fallida"].agg(["size", "sum", "mean"]).rename(columns={"size": "conversaciones", "sum": "fallidas", "mean": "tasa"})
tasa["tasa"] = tasa["tasa"].round(2)
tasa.sort_values("tasa", ascending=False)"""


def construir() -> None:
    analisis = ANALISIS.read_text(encoding="utf-8") if ANALISIS.exists() else "_Análisis pendiente._"
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_markdown_cell(INTRO),
        nbformat.v4.new_code_cell(CARGA),
        nbformat.v4.new_markdown_cell("## 1. De conversación a vector\n\nCada conversación completa (turnos del cliente y del asistente) se convierte en un vector de 768 números."),
        nbformat.v4.new_code_cell(EMBEDDINGS),
        nbformat.v4.new_markdown_cell("## 2. t-SNE en 2D\n\nCada punto es una conversación. Cerca = se parecen. Un círculo negro marca las conversaciones en las que el asistente dijo que no sabía o no pudo, o en las que una herramienta falló."),
        nbformat.v4.new_code_cell(TSNE2),
        nbformat.v4.new_markdown_cell("## 3. t-SNE en 3D"),
        nbformat.v4.new_code_cell(TSNE3),
        nbformat.v4.new_markdown_cell("## 4. Clústeres y dónde falla el asistente\n\nK-means agrupa los vectores sin ver la categoría prevista."),
        nbformat.v4.new_code_cell(CLUSTERS),
        nbformat.v4.new_markdown_cell("### Tasa de fallo por categoría prevista"),
        nbformat.v4.new_code_cell(TASA),
        nbformat.v4.new_markdown_cell("### Conversaciones fallidas, una por una"),
        nbformat.v4.new_code_cell(FALLOS),
        nbformat.v4.new_markdown_cell(
            "## 5. KNN frente a t-SNE\n\nt-SNE sirve para **mirar**: acomoda los puntos en 2D o 3D conservando la vecindad local, pero distorsiona las distancias. "
            "KNN sirve para **buscar**: encuentra las conversaciones más parecidas en el espacio original. Para ver cuánta información se pierde "
            "al proyectar, cada conversación se clasifica por la categoría de sus 5 vecinas más cercanas (dejando una fuera) en cada espacio. "
            "Aviso: t-SNE se calculó con todas las conversaciones a la vez, así que esto solo compara qué tan bien separa cada espacio; no es una predicción para conversaciones nuevas."
        ),
        nbformat.v4.new_code_cell(KNN),
        nbformat.v4.new_code_cell(VECINAS),
        nbformat.v4.new_markdown_cell(analisis),
    ]
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    SALIDA.parent.mkdir(exist_ok=True)
    NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(SALIDA.parent)}}).execute()
    nbformat.write(nb, SALIDA)
    print("Notebook ejecutado ->", SALIDA)


if __name__ == "__main__":
    construir()
