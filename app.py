"""Aplicación Streamlit del asistente de Celsia: Q&A, Resumen y FAQ.

Uso:  uv run streamlit run app.py
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from taaml.base import cargar_documentos  # noqa: E402
from taaml.corpus import MOTIVOS, RAG, SCRAPING, metricas  # noqa: E402
from taaml.errores import mensaje_error  # noqa: E402
from taaml.recuperacion import almacen_vectorial  # noqa: E402
from taaml.respaldo import con_respaldo, es_falla_del_proveedor, preguntas_guardadas, respuesta_guardada  # noqa: E402
from taaml.tareas import MODELO_POR_DEFECTO, clave_faltante, generar_faq, responder_con_fuentes, resumir  # noqa: E402
from taaml.validacion import datos_sin_respaldo  # noqa: E402

st.set_page_config(page_title="Asistente Celsia", page_icon="⚡", layout="wide")
st.title("⚡ Asistente virtual de Celsia")
st.caption("Responde solo con información oficial de celsia.com. Prototipo del Taller 1 (UAO).")
st.info("**Empresa.** Celsia es una empresa de energía del Valle del Cauca y el Tolima.\n\n"
        "**Problema de información.** Su información pública está repartida en más de mil páginas de celsia.com, "
        "y no hay un lugar donde preguntar y recibir la respuesta con su fuente.\n\n"
        "**Alcance del corpus.** Las páginas oficiales de celsia.com en español: servicios, atención, sedes, blog, noticias e inversionistas.")


@st.cache_data
def metricas_corpus() -> dict:
    return metricas()


@st.cache_data
def documentos() -> dict[str, dict]:
    """Documentos por nombre visible; si dos comparten título y categoría, se distinguen por el final de su dirección."""
    opciones: dict[str, dict] = {}
    for d in sorted(cargar_documentos(), key=lambda d: d["title"]):
        nombre = f"{d['title']} ({d['categoria']})"
        if nombre in opciones:
            nombre = f"{nombre} · {d['url'].rstrip('/').rsplit('/', 1)[-1][:40]}"
        while nombre in opciones:  # mismo título, categoría y final de dirección
            nombre += " (otro)"
        opciones[nombre] = d
    return opciones


def mostrar_error(e: Exception) -> None:
    st.error(mensaje_error(e))


def con_modelos_de_respaldo(tarea, modelo: str):
    """Ejecuta `tarea(modelo)`; si el modelo falla por cuota o conexión prueba el siguiente y avisa cuál respondió (spec 003). None si ninguno respondió."""
    try:
        resultado, _, avisos = con_respaldo(tarea, modelo)
    except Exception as e:  # noqa: BLE001
        mostrar_error(e)
        return None
    if avisos:
        st.info("Cambio de modelo: " + "; ".join(avisos) + ".")
    return resultado


def responder_o_mostrar_guardada(pregunta: str, base: str, modelo: str):
    """Q&A con respaldo de modelo y, si ninguno responde, la respuesta ya evaluada de esa pregunta (marcada como guardada)."""
    try:
        resultado, _, avisos = con_respaldo(lambda m: responder_con_fuentes(pregunta, base, m), modelo)
    except Exception as e:  # noqa: BLE001
        guardada = respuesta_guardada(pregunta) if es_falla_del_proveedor(e) else None
        if guardada is None:
            mostrar_error(e)
            if es_falla_del_proveedor(e) and (disponibles := preguntas_guardadas()):
                with st.expander("Preguntas con respuesta guardada (se muestran aunque no haya modelo)"):
                    st.markdown(chr(10).join(f"- {p}" for p in disponibles))
            return None
        st.warning("Ningún modelo respondió. Esta es la **respuesta guardada** de la evaluación (prompt v3) a esta misma pregunta, no una respuesta nueva.")
        respuesta, fragmentos = guardada
        return respuesta, fragmentos, {"encontrados": len(fragmentos), "metodo": "guardada", "tiempo_ms": 0}
    if avisos:
        st.info("Cambio de modelo: " + "; ".join(avisos) + ".")
    return resultado


with st.sidebar:
    st.header("Ajustes")
    modelo = st.text_input("Modelo (Gemini o «deepseek-flash»)", MODELO_POR_DEFECTO)
    base = st.radio("Contexto del asistente", ["rag", "compacta", "completa"],
                    help="«rag»: busca en toda la base los fragmentos relevantes a cada pregunta (recomendado).\n\n"
                         "«compacta»: solo el inicio de cada documento, sin buscar.\n\n"
                         "«completa»: toda la base en el prompt, como pide el enunciado (~340.000 tokens por pregunta, unas 80 veces más cara que rag; úsala solo para demostrar la diferencia).")

tab_qa, tab_resumen, tab_faq, tab_corpus = st.tabs(["Preguntas y respuestas", "Resumen", "Preguntas frecuentes", "Corpus y scraping"])

with tab_qa:
    with st.form("form_pregunta", border=False):
        pregunta = st.text_area("¿Qué quieres saber sobre Celsia?", placeholder="¿Cuál es el teléfono de atención al cliente?", max_chars=500)
        enviar = st.form_submit_button("Preguntar", type="primary")
    if enviar and pregunta.strip():
        if (faltante := clave_faltante(modelo)):
            st.info(f"Falta la clave de la API {faltante} en la configuración: se intentará con el modelo de respaldo.")
        with st.spinner("Buscando en la información oficial..."):
            resultado = responder_o_mostrar_guardada(pregunta, base, modelo)
        if resultado:
            respuesta, fragmentos, metricas = resultado
            st.markdown(respuesta)
            if base == "rag":
                if not fragmentos:
                    st.info("No se encontraron fragmentos relevantes para tu pregunta; no se inventó información.")
                else:
                    st.caption(f"Recuperación: {len(fragmentos)} fragmentos en {metricas.get('tiempo_ms', 0)} ms (búsqueda: {metricas.get('metodo', 'auto')}).")
                    if metricas.get("metodo") == "palabras":
                        if almacen_vectorial() == "ninguno":
                            st.info("No hay un índice de búsqueda listo (falta el archivo de vectores o la base en Chroma); se usó la búsqueda por palabras, que es menos precisa. Se regenera con `make indice`.")
                        else:
                            st.warning("La búsqueda se hizo por palabras porque Ollama no respondió: es menos precisa (54 % frente a 89 % con embeddings en la evaluación). Enciende Ollama y vuelve a preguntar.")
                    if (dudosos := datos_sin_respaldo(respuesta, fragmentos)):
                        st.warning("Estos datos de la respuesta no aparecen en las fuentes consultadas; verifícalos antes de usarlos: " + ", ".join(dudosos))
                    fuentes = list(dict.fromkeys((f["documento"], f["fuente"]) for f in fragmentos))
                    with st.expander(f"Fuentes consultadas ({len(fuentes)})", expanded=True):
                        # los documentos escritos a mano no tienen enlace: se muestran como texto, no como un enlace roto
                        st.markdown("\n".join(f"- [{titulo}]({url})" if url.startswith("http") else f"- {titulo} ({url})" for titulo, url in fuentes))

with tab_resumen:
    elegido = st.selectbox("Página oficial", list(documentos()), key="doc_resumen")
    if st.button("Resumir"):
        with st.spinner("Resumiendo..."):
            r = con_modelos_de_respaldo(lambda m: resumir(documentos()[elegido]["text"], documentos()[elegido].get("fecha_publicacion", ""), m), modelo)
        if r:
            st.markdown(r.resumen)
            st.markdown("**Puntos clave**\n" + "\n".join(f"- {p}" for p in r.puntos_clave))
            if r.canales:
                st.markdown("**Canales**\n" + "\n".join(f"- {c}" for c in r.canales))
            st.caption(f"Fuente: {documentos()[elegido]['url']}")

with tab_faq:
    elegido_faq = st.selectbox("Página oficial", list(documentos()), key="doc_faq")
    n = st.slider("Cantidad de preguntas", 3, 8, 5)
    if st.button("Generar FAQ"):
        with st.spinner("Generando preguntas frecuentes..."):
            faq = con_modelos_de_respaldo(lambda m: generar_faq(documentos()[elegido_faq]["text"], n, documentos()[elegido_faq].get("fecha_publicacion", ""), m), modelo)
        if faq:
            for q in faq.preguntas:
                with st.expander(q.pregunta):
                    st.markdown(q.respuesta)
            st.caption(f"Fuente: {documentos()[elegido_faq]['url']}")

with tab_corpus:
    c = metricas_corpus()
    st.caption("De dónde sale la información: el proceso de scraping por etapas, de celsia.com a los fragmentos que consulta el asistente. Las cifras se leen de los archivos de `data/`.")
    col0, col1, col2, col3, col4 = st.columns(5)
    col0.metric("URLs descubiertas", f"{c['paginas_descubiertas']:,}".replace(",", "."))
    col1.metric("URLs descargadas", f"{c['paginas_descargadas']:,}".replace(",", "."))
    col2.metric("Páginas con texto útil", f"{c['paginas_en_silver']:,}".replace(",", "."))
    col3.metric("Documentos curados", c["documentos"])
    col4.metric("Fragmentos", f"{c['fragmentos']:,}".replace(",", "."))
    st.metric("Tokens del corpus curado" + ("" if c["tokens_con_o200k"] else " (estimado como caracteres/4)"), f"{c['tokens']:,}".replace(",", "."))
    for bloque in (SCRAPING, RAG):
        st.subheader(bloque)
        st.dataframe([{"Etapa": e["etapa"], "Qué hace": e["que_hace"], "Entra": e["entra"], "Sale": e["sale"],
                       "Descartes": ", ".join(f"{MOTIVOS[k]}: {v}" for k, v in e["descartes"].items()) or "–"} for e in c["etapas"] if e["bloque"] == bloque],
                     hide_index=True, use_container_width=True)
    izquierda, derecha = st.columns(2)
    with izquierda:
        st.subheader("Descartes por motivo")
        st.bar_chart(c["descartes"], horizontal=True)
    with derecha:
        st.subheader("Documentos por categoría")
        st.bar_chart(c["por_categoria"], horizontal=True)
    with st.expander(f"Documentos descartados en la curaduría (primeros {len(c['descartados_ejemplos'])})"):
        st.dataframe([{"Regla": f["regla"], "Título": f["title"], "Motivo": f["motivo"], "Fuente": f["url"]} for f in c["descartados_ejemplos"]],
                     hide_index=True, use_container_width=True)
