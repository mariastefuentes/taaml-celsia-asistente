"""Construye y ejecuta `notebooks/analisis_conversaciones.ipynb` (Ruta Transversal A: conversaciones con t-SNE).

  uv sync --group analisis
  uv run python scripts/36_construir_notebook_tsne.py            # notebook con las 114 conversaciones simuladas
  uv run python scripts/36_construir_notebook_tsne.py --reales   # notebook con las conversaciones reales (antes: make exportar-chats)

Necesita Ollama encendido (embeddings) la primera vez; después usa `data/analisis/embeddings.npy`. El texto del análisis vive en
`notebooks/analisis_conversaciones.md` y se pega en la última celda: así se puede reescribir sin tocar el código del notebook.
"""

import argparse
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "notebooks" / "analisis_conversaciones.ipynb"
ANALISIS = RAIZ / "notebooks" / "analisis_conversaciones.md"
SALIDA_REALES = RAIZ / "notebooks" / "analisis_conversaciones_reales.ipynb"
ANALISIS_REALES = RAIZ / "notebooks" / "analisis_conversaciones_reales.md"
DATOS_REALES = RAIZ / "data" / "analisis" / "reales" / "conversaciones.jsonl"
MINIMO_REALES = 30  # con menos, los grupos del t-SNE no son confiables

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

COMPARACION = """# Las tres proyecciones a 2D sobre los MISMOS vectores, y una medida objetiva de cuál conserva mejor los vecinos
import umap
from sklearn.decomposition import PCA
from sklearn.manifold import trustworthiness

K = max(1, min(5, len(X) // 2 - 1))
Yp = PCA(n_components=2, random_state=0).fit_transform(X)
Yu = umap.UMAP(n_components=2, n_neighbors=max(2, min(15, len(X) - 1)), min_dist=0.1, metric="cosine", init="random" if len(X) < 30 else "spectral", random_state=0).fit_transform(X)
proyecciones = [("PCA (lineal)", Yp), ("t-SNE", Y2), ("UMAP", Yu)]

fig, ejes = plt.subplots(1, 3, figsize=(21, 6))
paleta = plt.get_cmap("tab10")
for ax, (nombre, Y) in zip(ejes, proyecciones):
    for i, (valor, g) in enumerate(df.groupby("@COLOR@")):
        ax.scatter(Y[g.index, 0], Y[g.index, 1], s=45, color=paleta(i % 10), alpha=0.85, label=str(valor))
    mal = df.index[df["fallida"]]
    ax.scatter(Y[mal, 0], Y[mal, 1], s=100, facecolors="none", edgecolors="black", linewidths=1.4)
    ax.set_title(nombre); ax.set_xticks([]); ax.set_yticks([])
ejes[0].legend(loc="best", fontsize=8, title="@COLOR@")
plt.tight_layout(); plt.show()

tabla = pd.DataFrame(
    {"Proyección": [n for n, _ in proyecciones], f"Confiabilidad de los vecinos (k={K}, 0 a 1)": [round(trustworthiness(X, Y, n_neighbors=K, metric="cosine"), 3) for _, Y in proyecciones]}
)
tabla"""

TEXTO_COMPARACION = """## PCA, t-SNE y UMAP sobre los mismos vectores

- **PCA** es lineal: dibuja las dos direcciones donde los vectores más varían. Es rápido y fiel a las distancias grandes, pero aplasta los grupos que no se separan en línea recta.
- **t-SNE** cuida a los vecinos cercanos: junta lo parecido, pero las distancias entre grupos lejanos no significan nada.
- **UMAP** también cuida a los vecinos y conserva algo más de la estructura global; suele dar grupos más compactos y es más rápido.

La tabla mide qué tan bien cada dibujo mantiene los mismos vecinos que había en los 768 números (confiabilidad: 1 es perfecto). Los tres gráficos usan los mismos puntos, así que las diferencias son de método, no de datos."""

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


# --- Versión con conversaciones REALES (las de los ensayos con celulares): no hay categoría prevista, así que los grupos se descubren ---
INTRO_REALES = """# Análisis de conversaciones reales con t-SNE (Ruta Transversal A)

**Qué hace este cuaderno.** Toma las conversaciones completas que la API guardó en PostgreSQL durante los ensayos por WhatsApp, convierte cada
una en un vector con el mismo modelo de embeddings que usa el agente para buscar y las proyecta a 2D y 3D con t-SNE para ver qué tipos de
conversación se parecen y dónde le va mal al asistente.

**Quiénes escribieron.** Compañeros y conocidos del grupo, no clientes de Celsia: las proporciones describen estos ensayos, no a los clientes.
El teléfono nunca se guardó (solo su hash) y las pruebas técnicas del equipo se excluyeron al exportar.

A diferencia del cuaderno de datos simulados, aquí **nadie etiquetó las conversaciones**: los grupos se descubren con K-means (el número de
grupos se elige con el coeficiente de silueta) y se interpretan leyendo sus ejemplos."""

CARGA_REALES = """import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path.cwd() if (Path.cwd() / "data").exists() else Path.cwd().parent
lineas = (RAIZ / "data/analisis/reales/conversaciones.jsonl").read_text(encoding="utf-8").splitlines()
df = pd.DataFrame([json.loads(l) for l in lineas if l.strip()]).reset_index(drop=True)
df["turnos_cliente"] = df["turnos"].map(lambda t: sum(x["rol"] == "cliente" for x in t))
df["primera_pregunta"] = df["turnos"].map(lambda t: t[0]["texto"][:70])
print(len(df), "conversaciones;", int(df["fallida"].sum()), "marcadas como fallidas")
if len(df) < 30:
    print("AVISO: menos de 30 conversaciones; los grupos del t-SNE no son confiables. Úsese solo para ver el método.")
df[["turnos_cliente", "fallida"]].describe().loc[["count", "mean", "max"]]"""

EMBEDDINGS_REALES = """from taaml.recuperacion import MODELO_EMBEDDINGS
from taaml.vectorstore import embeddings_celsia

# Son pocas conversaciones: se calculan siempre (no hay caché que pueda quedar desactualizada).
X = np.array(embeddings_celsia(MODELO_EMBEDDINGS).incrustar(df["texto"].tolist(), "document"), dtype=np.float32)
X.shape"""

CLUSTERS_REALES = """from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

mejor = (-1.0, 2)
for k in range(2, min(8, len(df) - 1) + 1):
    puntaje = silhouette_score(X, KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(X))
    mejor = max(mejor, (puntaje, k))
K = mejor[1]
print(f"K elegido por silueta: {K} (silueta {mejor[0]:.2f}; cerca de 0 = grupos poco definidos)")
df["cluster"] = KMeans(n_clusters=K, n_init=10, random_state=0).fit_predict(X)


def mas_usada(listas):
    c = Counter(h for l in listas for h in l)
    return c.most_common(1)[0][0] if c else "(ninguna)"


resumen = df.groupby("cluster").agg(
    conversaciones=("hilo", "size"),
    fallidas=("fallida", "sum"),
    en_revision=("en_revision", "sum"),
    herramienta_mas_usada=("herramientas", mas_usada),
    ejemplo=("primera_pregunta", "first"),
)
resumen["tasa_de_fallo"] = (resumen["fallidas"] / resumen["conversaciones"]).round(2)
resumen.sort_values("tasa_de_fallo", ascending=False)"""

TSNE2_REALES = """import matplotlib.pyplot as plt
from sklearn.manifold import TSNE

PERPLEJIDAD = max(2, min(12, (len(df) - 1) // 3))  # debe ser menor que el número de conversaciones
Y2 = TSNE(n_components=2, perplexity=PERPLEJIDAD, metric="cosine", init="pca", random_state=0).fit_transform(X)
df["x"], df["y"] = Y2[:, 0], Y2[:, 1]

fig, ax = plt.subplots(figsize=(11, 8))
colores = plt.get_cmap("tab10")
for c, g in df.groupby("cluster"):
    ax.scatter(g["x"], g["y"], s=70, color=colores(c), label=f"grupo {c}", alpha=0.85)
mal = df[df["fallida"]]
ax.scatter(mal["x"], mal["y"], s=150, facecolors="none", edgecolors="black", linewidths=1.6, label="conversación fallida")
ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), title="Grupo (K-means)")
ax.set_title(f"t-SNE 2D de las conversaciones reales (n={len(df)})")
ax.set_xticks([]); ax.set_yticks([])
plt.tight_layout(); plt.show()"""

TSNE3_REALES = """Y3 = TSNE(n_components=3, perplexity=PERPLEJIDAD, metric="cosine", init="pca", random_state=0).fit_transform(X)
fig = plt.figure(figsize=(11, 8))
ax = fig.add_subplot(projection="3d")
for c, g in df.groupby("cluster"):
    ax.scatter(Y3[g.index, 0], Y3[g.index, 1], Y3[g.index, 2], s=45, color=colores(c), label=f"grupo {c}", alpha=0.85)
mal = df.index[df["fallida"]]
ax.scatter(Y3[mal, 0], Y3[mal, 1], Y3[mal, 2], s=120, facecolors="none", edgecolors="black", linewidths=1.2, label="fallida")
ax.legend(loc="center left", bbox_to_anchor=(1.05, 0.5))
ax.set_title(f"t-SNE 3D de las conversaciones reales (n={len(df)})")
plt.tight_layout(); plt.show()"""

LEER_REALES = """# Para interpretar cada grupo hay que LEER sus conversaciones: aquí, la primera pregunta de cada una
pd.set_option("display.max_colwidth", 110)
df.sort_values("cluster")[["cluster", "fallida", "primera_pregunta"]]"""

FALLOS_REALES = """df[df["fallida"]][["cluster", "primera_pregunta"]].sort_values("cluster")"""

VECINAS_REALES = """# Las 5 conversaciones más parecidas a la primera marcada como fallida (o a la primera, si no hay fallidas), en el espacio original
S = X @ X.T  # los vectores tienen norma 1: el producto punto es el coseno
i = int(df.index[df["fallida"]][0]) if df["fallida"].any() else 0
orden = [j for j in np.argsort(-S[i]) if j != i][:5]
print("Conversación de referencia:", df.loc[i, "primera_pregunta"])
df.loc[orden, ["cluster", "primera_pregunta"]].assign(coseno=S[i, orden].round(2))"""


def celdas_reales() -> list:
    analisis = ANALISIS_REALES.read_text(encoding="utf-8") if ANALISIS_REALES.exists() else (
        "## 6. Qué encontramos\n\n_Análisis pendiente: léanse algunas conversaciones de cada grupo (tabla de arriba) antes de concluir qué "
        "revela cada clúster. Describan qué tienen en común, cuáles fallaron y por qué, y digan con claridad que quienes escribieron son compañeros, no clientes._"
    )
    md, code = nbformat.v4.new_markdown_cell, nbformat.v4.new_code_cell
    return [
        md(INTRO_REALES),
        code(CARGA_REALES),
        md("## 1. De conversación a vector\n\nCada conversación completa (turnos del cliente y del asistente) se convierte en un vector de 768 números."),
        code(EMBEDDINGS_REALES),
        md("## 2. Grupos (K-means) y dónde falla el asistente\n\nK-means agrupa los vectores sin etiquetas previas; el número de grupos lo elige el coeficiente de silueta."),
        code(CLUSTERS_REALES),
        md("## 3. t-SNE en 2D\n\nCada punto es una conversación; el color es su grupo. Un círculo negro marca las conversaciones en las que el asistente dijo que no sabía o no pudo, o en las que una herramienta falló."),
        code(TSNE2_REALES),
        md("## 4. t-SNE en 3D"),
        code(TSNE3_REALES),
        md(TEXTO_COMPARACION),
        code(COMPARACION.replace("@COLOR@", "cluster")),
        md("## 5. Qué hay dentro de cada grupo\n\nLas conversaciones por grupo y las marcadas como fallidas, para leerlas una por una."),
        code(LEER_REALES),
        code(FALLOS_REALES),
        code(VECINAS_REALES),
        md(analisis),
    ]


def construir_reales() -> None:
    if not DATOS_REALES.exists():
        sys.exit("Falta data/analisis/reales/conversaciones.jsonl: corre primero `make exportar-chats`.")
    cantidad = sum(1 for l in DATOS_REALES.read_text(encoding="utf-8").splitlines() if l.strip())
    if cantidad < 3:
        sys.exit(f"Hay {cantidad} conversaciones reales: no alcanzan ni para probar el notebook (mínimo 3; para concluir algo, {MINIMO_REALES} o más).")
    if cantidad < MINIMO_REALES:
        print(f"Aviso: {cantidad} conversaciones reales (< {MINIMO_REALES}). El notebook se genera, pero sus grupos no son confiables.")
    nb = nbformat.v4.new_notebook()
    nb.cells = celdas_reales()
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(SALIDA_REALES.parent)}}).execute()
    nbformat.write(nb, SALIDA_REALES)
    print("Notebook ejecutado ->", SALIDA_REALES)


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
        nbformat.v4.new_markdown_cell(TEXTO_COMPARACION),
        nbformat.v4.new_code_cell(COMPARACION.replace("@COLOR@", "categoria_prevista")),
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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reales", action="store_true", help="usa las conversaciones reales exportadas con `make exportar-chats`")
    construir_reales() if ap.parse_args().reales else construir()
