"""CAPA GOLD: texto limpio (silver) + metadatos utiles. Es el insumo del Modulo 2 (RAG).

Agrega a cada documento: categoria, region, idioma, fecha de extraccion, tamano, hash y una
RELEVANCIA PROPUESTA para el asistente (alta / media / baja).
La relevancia es una PROPUESTA basada en reglas simples: la decision final es del equipo.
Ningun documento se elimina aqui; la curaduria final filtra por estos metadatos.

Salida:
  data/3_gold/*.md           un archivo por documento, con metadatos en el encabezado
  data/3_gold/corpus.jsonl   los mismos documentos, uno por linea
  data/3_gold/sedes.json     sedes estructuradas (util para consultas tipo SQL/CSV)
  data/3_gold/_catalogo.csv  tabla resumen (se puede abrir en Excel)

Uso:  uv run python scripts/04_construir_gold.py
"""
import csv
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

import tiktoken

ROOT = Path(__file__).resolve().parent.parent
CODIFICADOR = tiktoken.get_encoding("o200k_base")  # el mismo con que se midió la base (~316.800 tokens)
DATA = ROOT / "data"
BRONZE, SILVER, GOLD = DATA / "1_bronze", DATA / "2_silver", DATA / "3_gold"

# categoria segun el primer segmento de la URL (despues de /es/)
CATEGORIAS = [
    (r"^(inversionistas|investors)", "inversionistas"),
    (r"^(sostenibilidad|nuestros-de-temas-de-materialidad|test-sostenibilidad|esg|reports|responsabilidad-social|bonos-verdes|"
     r"anexos-reporte|historico_esgdatabook|dimensions|protocolos)", "sostenibilidad"),
    (r"^noticias$", "noticias"),
    (r"^(noticias|sala-de-prensa|revista|libros|podcast|mapa-del-sitio|jorge-mario)", "prensa_y_medios"),
    (r"(salvajina|calima|pacifico|centrales|granjas|generacion|embalse|fauna|franja|reverdec|licenciamiento|avanza|"
     r"laboratorio-de-medidores|transferencias)", "activos_y_proyectos"),
    (r"^(productos-hechos|portafolio|formulario-soluciones|energiasolarparaempresas|homes)", "servicios"),
    (r"^(mitos-y-verdades|mas-personal|celsia-formulario)", "atencion"),
    (r"^(tolima|inicio)", "empresa"),
    (r"^(quienes-somos|about-us|la-nueva-era|se-parte-de-nuestro-equipo|nuestra-historia)", "empresa"),
    (r"^(informacion-regulatoria|ley-de-transparencia|linea-de-transparencia|notificaciones-judiciales)", "regulatorio"),
    (r"^(panama|honduras|costa-rica|peru|centroamerica)", "internacional"),
    (r"^(zona-clientes|encuentranos|pqr|mantenimientos|hogares-)", "atencion"),
    (r"^(soluciones|celsiapymes|companies|internet|energia-solar|hogares|pymes|empresas|tienda|cargador)", "servicios"),
]
BLOG_UTIL = re.compile(
    r"factura|pqr|tr[aá]mite|solicitud|requisito|cambio de|estrato|siniestro|ahorr|cargador|panel|solar|reporta|servicio de energ|"
    r"hogar|pymes|tarifa|medidor|seguridad|consumo|internet|recibo|cobros?|canal de atenci|whatsapp|conecta con celsia|luz i\.?a|"
    r"asistente virtual|accidente|riesgo|electrodom|etiqueta de eficiencia|puntos digitales|filas|acceso seguro|zona clientes|"
    r"desviaci|costo de la energ|precio de la energ|precio de la luz|tienda celsia|financiad|subsidio|emcali|respaldo", re.I)
PALABRAS_ES = set("de la el los las que para con una por del su al se es un como más muy sus tu tus nuestro nuestra nuestros desde sobre".split())
PALABRAS_EN = set("the and of for with your our you to is are that from this on by as at be it can we their which will".split())


def leer_md(path: Path) -> tuple[dict, str]:
    texto = path.read_text(encoding="utf-8")
    _, cabecera, cuerpo = texto.split("---", 2)
    meta = dict(ln.split(": ", 1) for ln in cabecera.strip().splitlines() if ": " in ln)
    return meta, cuerpo.strip()


def categoria_de(meta: dict) -> str:
    if meta["section"] == "sedes":
        return "sedes"
    if meta["section"] == "blog-celsia":
        return "blog"
    partes = [p for p in urlparse(meta["url"]).path.strip("/").split("/") if p]
    primer = partes[1] if len(partes) > 1 and partes[0] in ("es", "en") else (partes[0] if partes else "")
    for patron, nombre in CATEGORIAS:
        if re.search(patron, primer):
            return nombre
    return "otros"


def region_de(meta: dict, texto: str, categoria: str) -> str:
    if categoria == "internacional":
        return "Internacional"
    t = texto.lower()
    valle, tolima = t.count("valle del cauca") + t.count("epsa"), t.count("tolima") + t.count("cetsa")
    if valle and tolima:
        return "Valle y Tolima"
    if tolima:
        return "Tolima"
    if valle:
        return "Valle del Cauca"
    return "General"


def idioma_de(texto: str) -> str:
    """Inglés si al menos el 25 % de las palabras funcionales (the, and, of...) son inglesas.
    Verificado sobre el corpus: las páginas en inglés quedan sobre 30 % y las demás bajo 13 %."""
    palabras = re.findall(r"[a-záéíóúñ]+", texto.lower())
    en = sum(p in PALABRAS_EN for p in palabras)
    es = sum(p in PALABRAS_ES for p in palabras)
    return "en" if en + es and en / (en + es) >= 0.25 else "es"


def relevancia_de(categoria: str, meta: dict, idioma: str) -> tuple[str, str]:
    if idioma == "en":
        return "baja", "contenido en inglés"
    if categoria in ("sedes", "atencion", "servicios", "empresa"):
        return "alta", f"categoría {categoria}: responde preguntas de primer contacto"
    if categoria == "blog":
        if BLOG_UTIL.search(meta["title"]) or BLOG_UTIL.search(meta["url"]):
            return "alta", "blog sobre trámites, factura, servicios o ahorro"
        return "media", "blog general; revisar si aporta al alcance"
    if categoria == "sostenibilidad":
        return "media", "sostenibilidad: dejar visión y metas, revisar lo muy técnico"
    if categoria == "noticias":
        return "media", "noticia: depende del tema y de la vigencia (se decide en la curaduría, regla R7)"
    if categoria == "internacional":
        return "media", "depende de si el asistente atiende fuera de Colombia"
    if categoria in ("inversionistas", "regulatorio", "prensa_y_medios"):
        return "baja", f"{categoria}: técnico o noticioso, poco útil para un cliente nuevo"
    if categoria == "activos_y_proyectos":
        return "media", "centrales y proyectos: informativo; útil solo si el alcance incluye infraestructura"
    return "media", "sin clasificar; revisar"


def main() -> None:
    fechas = {}
    indice = BRONZE / "_indice.jsonl"
    if indice.exists():
        for ln in indice.read_text(encoding="utf-8").splitlines():
            r = json.loads(ln)
            fechas[r["url"]] = r["fetched_at"]
    sedes_json = SILVER / "_sedes.json"

    if GOLD.exists():
        shutil.rmtree(GOLD)
    GOLD.mkdir(parents=True)

    filas, corpus = [], []
    for md in sorted(SILVER.glob("*.md")):
        meta, cuerpo = leer_md(md)
        texto = cuerpo.split("\n", 2)[2] if cuerpo.startswith("# ") else cuerpo
        cat = categoria_de(meta)
        idioma = idioma_de(texto)
        region = region_de(meta, texto, cat)
        rel, motivo = relevancia_de(cat, meta, idioma)
        fecha = fechas.get(meta["url"], "")
        enc = {
            "url": meta["url"], "title": meta["title"], "fuente": "celsia.com (sitio oficial)",
            "fecha_extraccion": fecha, "fecha_publicacion": meta.get("fecha_publicacion", ""), "section": meta["section"], "categoria": cat, "region": region, "idioma": idioma,
            "caracteres": len(texto), "tokens": len(CODIFICADOR.encode(texto)), "hash": meta["hash"], "relevancia_propuesta": rel, "motivo": motivo,
        }
        cabecera = "\n".join(f"{k}: {v}" for k, v in enc.items())
        (GOLD / md.name).write_text(f"---\n{cabecera}\n---\n\n# {meta['title']}\n\n{texto}\n", encoding="utf-8")
        corpus.append({**enc, "archivo": md.name, "text": texto})
        filas.append({**enc, "archivo": md.name})

    with (GOLD / "corpus.jsonl").open("w", encoding="utf-8") as f:
        for d in corpus:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    with (GOLD / "_catalogo.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["archivo", "title", "section", "categoria", "region", "idioma", "caracteres", "tokens",
                                          "relevancia_propuesta", "motivo", "url", "fecha_publicacion", "fecha_extraccion",
                                          "hash", "fuente"])
        w.writeheader()
        w.writerows(filas)
    if sedes_json.exists():
        shutil.copy(sedes_json, GOLD / "sedes.json")

    print(f"Gold: {len(corpus)} documentos, {sum(d['caracteres'] for d in corpus):,} caracteres")
    for clave in ("categoria", "relevancia_propuesta", "region", "idioma"):
        cuenta: dict[str, list] = {}
        for d in corpus:
            c = cuenta.setdefault(d[clave], [0, 0])
            c[0] += 1
            c[1] += d["caracteres"]
        print(f"  por {clave}: " + "; ".join(f"{k}={v[0]} ({v[1]:,} car.)" for k, v in sorted(cuenta.items(), key=lambda x: -x[1][1])))


if __name__ == "__main__":
    main()
