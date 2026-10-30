"""Aplicación Streamlit del Módulo 1: el corpus y el scraping por etapas.

Es la versión que se sustenta en la sesión 8 y muestra solo lo que evalúa el
criterio 1 de la rúbrica sobre los datos: el proceso de scraping por etapas
(descubrir → extraer → limpiar → deduplicar → enriquecer), las métricas del corpus
(URLs, páginas, tokens, descartes) y los descartes por motivo.

La app completa (Q&A con fuentes, Resumen y FAQ) está en `app.py` y se abre con
`make app`. El scraping en vivo se ejecuta aparte con `make scraping-demo`.

Uso:  uv run streamlit run app_modulo1.py
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from taaml.corpus import MOTIVOS, RAG, SCRAPING, metricas  # noqa: E402

st.set_page_config(page_title="Corpus Celsia · Módulo 1", page_icon="⚡", layout="wide")
st.title("⚡ Corpus de Celsia: del sitio a la base de conocimiento")
st.caption("Proceso de scraping por etapas y métricas del corpus. Demostración del Módulo 1 (UAO).")
st.info("**Empresa.** Celsia es una empresa de energía del Valle del Cauca y el Tolima.\n\n"
        "**Problema de información.** Su información pública está repartida en más de mil páginas de celsia.com, "
        "y no hay un lugar donde consultarla con su fuente.\n\n"
        "**Alcance del corpus.** Las páginas oficiales de celsia.com en español: servicios, atención, sedes, blog, noticias e inversionistas.\n\n"
        "**Cómo se ve en vivo.** Las cifras de esta pantalla salen de la corrida real y se leen de `data/`. "
        "El scraping se ejecuta en la terminal con `make scraping-demo` (5 páginas, sin tocar la capa Bronze).")


@st.cache_data
def metricas_corpus() -> dict:
    return metricas()


c = metricas_corpus()

st.subheader("Métricas del corpus")
col0, col1, col2, col3, col4 = st.columns(5)
col0.metric("URLs descubiertas", f"{c['paginas_descubiertas']:,}".replace(",", "."))
col1.metric("URLs descargadas", f"{c['paginas_descargadas']:,}".replace(",", "."))
col2.metric("Páginas con texto útil", f"{c['paginas_en_silver']:,}".replace(",", "."))
col3.metric("Documentos curados", c["documentos"])
col4.metric("Fragmentos", f"{c['fragmentos']:,}".replace(",", "."))
st.metric("Tokens del corpus curado" + ("" if c["tokens_con_o200k"] else " (estimado como caracteres/4)"), f"{c['tokens']:,}".replace(",", "."))

st.caption("De dónde sale la información: el proceso de scraping por etapas, de celsia.com a los fragmentos que consulta el asistente.")
for bloque in (SCRAPING, RAG):
    st.subheader(bloque)
    st.dataframe([{"Etapa": e["etapa"], "Qué hace": e["que_hace"], "Entra": e["entra"], "Sale": e["sale"],
                   "Descartes": ", ".join(f"{MOTIVOS[k]}: {v}" for k, v in e["descartes"].items()) or "–"} for e in c["etapas"] if e["bloque"] == bloque],
                 hide_index=True, width="stretch")

izquierda, derecha = st.columns(2)
with izquierda:
    st.subheader("Descartes por motivo")
    st.bar_chart(c["descartes"], horizontal=True)
with derecha:
    st.subheader("Documentos por categoría")
    st.bar_chart(c["por_categoria"], horizontal=True)

with st.expander(f"Documentos descartados en la curaduría (primeros {len(c['descartados_ejemplos'])})"):
    st.dataframe([{"Regla": f["regla"], "Título": f["title"], "Motivo": f["motivo"], "Fuente": f["url"]} for f in c["descartados_ejemplos"]],
                 hide_index=True, width="stretch")
