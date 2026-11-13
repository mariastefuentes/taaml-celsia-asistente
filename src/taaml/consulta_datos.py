"""Consulta de datos estructurados de Celsia (sedes, contactos y catálogo del corpus) con filtros exactos.

No usa embeddings ni modelos: filtra los archivos versionados en data/. La herramienta del agente (`consultar_datos`) solo envuelve
estas funciones, así se prueban sin Gemini ni Ollama.
"""
import csv
import json
import unicodedata
from pathlib import Path

DATOS = Path(__file__).resolve().parents[2] / "data"
SEDES = DATOS / "3_gold" / "sedes.json"
CONTACTOS = DATOS / "5_extraccion" / "contactos.jsonl"
CATALOGO = DATOS / "3_gold" / "_catalogo.csv"

TABLAS = ("sedes", "contactos", "catalogo")
SIN_RESULTADOS = "Sin resultados en los datos estructurados."
LIMITE = 10  # el modelo es pequeño o de pago por token: se devuelven pocas filas


def _norm(texto) -> str:
    """Minúsculas y sin tildes, para que «Líbano» y «libano» coincidan."""
    sin_tildes = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return sin_tildes.lower().strip()


def _contiene(valor, buscado) -> bool:
    return not buscado or _norm(buscado) in _norm(valor)


def sedes(ciudad: str = "", departamento: str = "", tipo: str = "") -> list[dict]:
    filas = json.loads(SEDES.read_text(encoding="utf-8"))
    return [f for f in filas
            if _contiene(f["CITY"], ciudad) and _contiene(f["DEPARTMENT"], departamento) and _contiene(f["HQ_TYPE"], tipo)]


def contactos(tipo: str = "", tema: str = "") -> list[dict]:
    """Un contacto por fila (teléfono, correo, WhatsApp o enlace), con para qué sirve."""
    salida = []
    for linea in CONTACTOS.read_text(encoding="utf-8").splitlines():
        for c in json.loads(linea)["contactos"]:
            if _contiene(c["tipo"], tipo) and _contiene(c["para_que_sirve"], tema):
                salida.append(c)
    return salida


def catalogo(seccion: str = "", categoria: str = "", texto: str = "") -> list[dict]:
    with CATALOGO.open(encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f))
    return [r for r in filas
            if _contiene(r["section"], seccion) and _contiene(r["categoria"], categoria) and _contiene(r["title"], texto)]


def _linea(tabla: str, fila: dict) -> str:
    if tabla == "sedes":
        return f"- {fila['NAME']} ({fila['HQ_TYPE']}, {fila['CITY']}, {fila['DEPARTMENT']}). Dirección: {fila['ADDRESS']}. Teléfono: {fila['PHONE'] or 'sin dato'}. Horario: {fila['SHEDULE'] or 'sin dato'}"
    if tabla == "contactos":
        return f"- {fila['tipo']}: {fila['valor']}. {fila['para_que_sirve']}"
    return f"- {fila['title']} ({fila['section']}, {fila['categoria']}): {fila['url']}"


def consultar(tabla: str, filtros: dict | None = None) -> str:
    """Filtra una tabla y devuelve las filas como texto. Los filtros que no existan en esa tabla se ignoran."""
    funciones = {"sedes": sedes, "contactos": contactos, "catalogo": catalogo}
    nombre = _norm(tabla)
    if nombre not in funciones:
        return f"Tabla desconocida: {tabla}. Las disponibles son: {', '.join(TABLAS)}."
    permitidos = funciones[nombre].__code__.co_varnames[:funciones[nombre].__code__.co_argcount]
    filas = funciones[nombre](**{k: v for k, v in (filtros or {}).items() if k in permitidos and v})
    if not filas:
        return SIN_RESULTADOS
    lineas = [_linea(nombre, f) for f in filas[:LIMITE]]
    if len(filas) > LIMITE:
        lineas.append(f"(Hay {len(filas)} resultados; se muestran {LIMITE}. Afina el filtro.)")
    return "\n".join(lineas)
