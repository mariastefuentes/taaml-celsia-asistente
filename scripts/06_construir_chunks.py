"""CHUNKING: divide los documentos de la base de conocimiento en fragmentos pequenos y coherentes.

Parte de data/4_curaduria/documentos_incluidos.jsonl (los documentos que quedaron tras la curaduria) y escribe
data/4_curaduria/chunks.jsonl: un fragmento por linea, con sus metadatos (documento, categoria, region, fuente).
Es el insumo directo del Modulo 2 (embeddings, base vectorial y RAG).

Estrategia:
  - Texto corrido: RecursiveCharacterTextSplitter (langchain-text-splitters). Corta en este orden de preferencia:
    parrafo, linea, frase y palabra, para no partir una idea por la mitad.
  - Sedes: un fragmento por punto de atencion (cada sede es una unidad de respuesta: direccion + horario).
  - Cada fragmento lleva el titulo del documento al inicio ("contexto") para que se entienda solo, tambien al recuperarlo.

Uso:  uv run python scripts/06_construir_chunks.py            (usa los parametros por defecto)
      uv run python scripts/06_construir_chunks.py --tamano 800 --solape 100
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

ROOT = Path(__file__).resolve().parent.parent
CURADURIA = ROOT / "data" / "4_curaduria"
TAMANO_POR_DEFECTO = 1000   # caracteres (unos 250 tokens): cabe una respuesta completa sin arrastrar temas ajenos
SOLAPE_POR_DEFECTO = 150    # caracteres compartidos entre fragmentos vecinos, para no perder lo que queda en el borde
MINIMO = 200                # un fragmento final mas corto que esto se une al anterior

# datos que siempre deben sobrevivir al fragmentado (verificacion)
DATOS_CLAVE = ["01 8000 112 115", "310 390 3468", "Servicioalcliente@celsia.com", "Tienda Palmira", "Planadas",
               "Cambio de estrato", "Cancelación definitiva", "311 321 0000", "celsiainternet.com"]


def identificador(archivo: str) -> str:
    """Identificador estable y unico del documento: su nombre; si es largo, se corta y se le suma una huella para que no choque."""
    base = re.sub(r"[^a-z0-9]+", "-", archivo.lower()).strip("-")
    return base if len(base) <= 70 else f"{base[:61]}-{hashlib.sha1(archivo.encode('utf-8')).hexdigest()[:8]}"


def fragmentar(doc: dict, splitter: RecursiveCharacterTextSplitter) -> list[dict]:
    texto = doc["text"].strip()
    if doc["categoria"] == "sedes":
        # un fragmento por sede: lineas "- **Nombre** (ciudad)..." bajo su encabezado de pais y departamento
        zona, partes = "", []
        for ln in texto.splitlines():
            if ln.startswith("## "):
                zona = ln[3:].strip()
            elif ln.startswith("- "):
                partes.append(f"{zona}. {ln[2:].strip()}" if zona else ln[2:].strip())
        return [{"texto": p, "seccion": "sedes"} for p in partes]
    piezas = [p for p in splitter.split_text(texto) if p.strip()]
    # un resto muy corto al final no responde nada por si solo: se pega al fragmento anterior
    if len(piezas) > 1 and len(piezas[-1]) < MINIMO:
        resto = piezas.pop()
        piezas[-1] = piezas[-1] + "\n" + resto
    return [{"texto": p, "seccion": ""} for p in piezas]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tamano", type=int, default=TAMANO_POR_DEFECTO)
    ap.add_argument("--solape", type=int, default=SOLAPE_POR_DEFECTO)
    a = ap.parse_args()

    splitter = RecursiveCharacterTextSplitter(chunk_size=a.tamano, chunk_overlap=a.solape,
                                              separators=["\n\n", "\n", ". ", " ", ""], length_function=len)
    docs = [json.loads(ln) for ln in (CURADURIA / "documentos_incluidos.jsonl").read_text(encoding="utf-8").splitlines()]

    chunks = []
    for d in docs:
        piezas = fragmentar(d, splitter)
        for i, p in enumerate(piezas, 1):
            fecha = f", publicado {d['fecha_publicacion']}" if d["categoria"] in ("blog", "noticias") and d.get("fecha_publicacion") else ""
            contexto = f"{d['title']} ({d['categoria']}{fecha})"
            texto = f"{contexto}\n{p['texto']}"
            chunks.append({
                "chunk_id": f"{identificador(d['archivo'])}-{i:03d}",
                "documento": d["title"], "categoria": d["categoria"], "region": d["region"], "fuente": d["url"],
                "orden": i, "de": len(piezas), "texto": texto, "caracteres": len(texto), "tokens_aprox": len(texto) // 4,
            })
    with (CURADURIA / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # ---- verificacion
    tam = sorted(c["caracteres"] for c in chunks)
    por_cat: dict[str, int] = {}
    for c in chunks:
        por_cat[c["categoria"]] = por_cat.get(c["categoria"], 0) + 1
    sin_chunks = [d["title"] for d in docs if not any(c["documento"] == d["title"] for c in chunks)]
    todo = "\n".join(c["texto"] for c in chunks)
    perdidos = [x for x in DATOS_CLAVE if x not in todo]
    # +200 por el titulo que se antepone; las sedes se miden aparte porque cada una es una unidad que no se parte
    excedidos = [c for c in chunks if c["categoria"] != "sedes" and c["caracteres"] > a.tamano + 200 + MINIMO]
    cortos = [c for c in chunks if c["categoria"] != "sedes" and c["orden"] > 1 and c["caracteres"] < MINIMO]
    print(f"{len(docs)} documentos -> {len(chunks)} fragmentos (tamano {a.tamano}, solape {a.solape})")
    print(f"tamano en caracteres: min {tam[0]} | mediana {tam[len(tam) // 2]} | max {tam[-1]} | promedio {sum(tam) // len(tam)}")
    print("por categoria:", ", ".join(f"{k}={v}" for k, v in sorted(por_cat.items(), key=lambda x: -x[1])))
    print("OK   todos los documentos tienen fragmentos" if not sin_chunks else f"FALLA documentos sin fragmentos: {sin_chunks[:5]}")
    print("OK   ningun fragmento se pasa del tamano" if not excedidos else f"FALLA {len(excedidos)} fragmentos se pasan del tamano")
    print("OK   no hay restos cortos sueltos" if not cortos else f"AVISO {len(cortos)} fragmentos muy cortos")
    print("OK   los datos clave sobreviven al fragmentado" if not perdidos else f"FALLA datos clave perdidos: {perdidos}")


if __name__ == "__main__":
    main()
