"""Métricas del corpus por etapa del pipeline (Bronze → Silver → Gold → curaduría → fragmentos), para mostrarlas en la app.

Lee solo archivos versionados en data/ (no necesita el HTML de Bronze) y no llama a ningún modelo.
"""
import csv
import json
from collections import Counter
from pathlib import Path

DATOS = Path(__file__).resolve().parents[2] / "data"
DESCUBRIMIENTO = DATOS / "2_silver" / "_descubrimiento.json"
REGISTRO_SILVER = DATOS / "2_silver" / "_registro.csv"
CATALOGO_GOLD = DATOS / "3_gold" / "_catalogo.csv"
REGISTRO_CURADURIA = DATOS / "4_curaduria" / "registro_curaduria.csv"
INCLUIDOS = DATOS / "4_curaduria" / "documentos_incluidos.jsonl"
FRAGMENTOS = DATOS / "4_curaduria" / "chunks.jsonl"
BASE = DATOS / "4_curaduria" / "base_conocimiento.txt"

SCRAPING = "Pipeline de scraping (5 etapas)"  # lo que pide la rúbrica: descubrir → extraer → limpiar → deduplicar → enriquecer
RAG = "Preparación para el RAG (2 etapas)"  # lo que sigue al scraping: elegir qué entra y partirlo en fragmentos

MOTIVOS = {
    "bloqueada": "Bloqueada por robots.txt",
    "error_http": "Error al descargar (HTTP 4xx/5xx)",
    "descartada_muy_corta": "Página casi sin texto (menos de 200 caracteres)",
    "duplicado_exacto": "Duplicado exacto (mismo texto en otra dirección)",
    "R1": "Contenido en inglés",
    "R6": "Casi duplicado de otro documento",
    "R7": "Noticia con más de 12 meses (vencida)",
    "R8": "Casi sin texto",
}


def _filas(ruta: Path) -> list[dict]:
    return list(csv.DictReader(ruta.open(encoding="utf-8-sig", newline="")))


def _tokens(incluidos: list[dict]) -> tuple[int, bool]:
    """Tokens de la base curada completa (base_conocimiento.txt) con el tokenizador o200k; si no está disponible sin red, suma los del catálogo Gold (sin los documentos manuales)."""
    texto = BASE.read_text(encoding="utf-8")
    try:
        import tiktoken

        return len(tiktoken.get_encoding("o200k_base").encode(texto, disallowed_special=())), True
    except Exception:  # noqa: BLE001  sin red o sin caché del tokenizador
        return len(texto) // 4, False  # estimado, como el que imprime scripts/05_curar_base.py


def metricas() -> dict:
    """Etapas con entrada, salida y descartes, y las cifras globales del corpus."""
    silver = _filas(REGISTRO_SILVER)
    por_resultado = Counter(f["resultado"] for f in silver)
    gold = _filas(CATALOGO_GOLD)
    curaduria = _filas(REGISTRO_CURADURIA)
    descartes_curaduria = Counter(f["regla"] for f in curaduria if f["decision"] == "excluido")
    incluidos = [json.loads(ln) for ln in INCLUIDOS.read_text(encoding="utf-8").splitlines()]
    fragmentos = sum(1 for _ in FRAGMENTOS.open(encoding="utf-8"))
    descargadas = len(silver)
    sin_vacias = descargadas - por_resultado["descartada_muy_corta"]
    conservadas = por_resultado["conservada"]
    tokens, exacto = _tokens(incluidos)
    d = json.loads(DESCUBRIMIENTO.read_text(encoding="utf-8")) if DESCUBRIMIENTO.exists() else None
    descubiertas = d["descubiertas"] if d else descargadas
    descartes_descubrir = {k: d[campo] for k, campo in (("bloqueada", "bloqueadas"), ("error_http", "con_error")) if d and d[campo]}
    etapas = [
        {"bloque": SCRAPING, "etapa": "1. Descubrir", "que_hace": "Lee los sitemaps de celsia.com y lista las URLs que existen",
         "entra": descubiertas, "sale": descubiertas, "descartes": {}},
        {"bloque": SCRAPING, "etapa": "2. Extraer", "que_hace": "Descarga el HTML de cada URL respetando robots.txt, con pausa de 1 s",
         "entra": descubiertas, "sale": descargadas, "descartes": descartes_descubrir},
        {"bloque": SCRAPING, "etapa": "3. Limpiar", "que_hace": "Quita menús, scripts y pie de página y deja el texto útil de cada página",
         "entra": descargadas, "sale": sin_vacias, "descartes": {"descartada_muy_corta": por_resultado["descartada_muy_corta"]}},
        {"bloque": SCRAPING, "etapa": "4. Deduplicar", "que_hace": "Descarta páginas con exactamente el mismo texto, prefiriendo la URL en español",
         "entra": sin_vacias, "sale": conservadas, "descartes": {"duplicado_exacto": por_resultado["duplicado_exacto"]}},
        {"bloque": SCRAPING, "etapa": "5. Enriquecer (Gold)", "que_hace": "Agrega sección, categoría, región, idioma, fecha de publicación, tokens y hash a cada documento",
         "entra": conservadas, "sale": len(gold), "descartes": {}, "nota": "incluye el documento de sedes"},
        {"bloque": RAG, "etapa": "6. Curar", "que_hace": "Aplica reglas: sin inglés (R1), sin casi duplicados (R6), sin noticias vencidas (R7)",
         "entra": len(curaduria), "sale": len(incluidos), "descartes": dict(descartes_curaduria),
         "nota": "entran los documentos de Gold más 2 escritos a mano con fuente"},
        {"bloque": RAG, "etapa": "7. Fragmentar", "que_hace": "Divide cada documento en fragmentos de 1.000 caracteres con 150 de solape",
         "entra": len(incluidos), "sale": fragmentos, "descartes": {}},
    ]
    return {
        "etapas": etapas,
        "paginas_descubiertas": descubiertas, "paginas_descargadas": descargadas,
        "paginas_en_silver": conservadas,
        "documentos": len(incluidos),
        "fragmentos": fragmentos,
        "tokens": tokens,
        "tokens_con_o200k": exacto,
        "por_categoria": dict(Counter(d["categoria"] for d in incluidos).most_common()),
        "descartes": {MOTIVOS[k]: v for k, v in (Counter({k: v for e in etapas for k, v in e["descartes"].items()})).items() if v},
        "descartados_ejemplos": [f for f in curaduria if f["decision"] == "excluido"][:200],
    }
