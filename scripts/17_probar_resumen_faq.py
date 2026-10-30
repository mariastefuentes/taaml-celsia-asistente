"""EVIDENCIA DE RESUMEN Y FAQ: una llamada de cada tarea sobre una página oficial, guardada en un CSV.

Usa la misma ruta de LangChain que la app (`taaml.tareas.resumir` y `generar_faq`). Son 2 llamadas al modelo (gasta cuota).
Cada cifra, correo y enlace de la salida se busca en el texto de la página con `taaml.validacion` (sin gastar).

Uso:  uv run python scripts/17_probar_resumen_faq.py [--modelo gemini-3.5-flash] [--titulo "pagar tu factura"]
Resultado: docs/2 - Conjunto de prueba/resultados/resumen_faq_<modelo>.csv
"""
import argparse
import csv
import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from taaml.base import cargar_documentos  # noqa: E402
from taaml.tareas import MODELO_POR_DEFECTO, generar_faq, resumir  # noqa: E402
from taaml.validacion import datos_sin_respaldo  # noqa: E402

SALIDA = ROOT / "docs" / "2 - Conjunto de prueba" / "resultados"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default=MODELO_POR_DEFECTO)
    ap.add_argument("--titulo", default="pagar tu factura en canales digitales", help="parte del título de la página oficial")
    ap.add_argument("--preguntas", type=int, default=5, help="cantidad de preguntas de la FAQ")
    a = ap.parse_args()
    doc = next(d for d in cargar_documentos() if a.titulo.lower() in d["title"].lower())
    fragmentos = [{"texto": doc["text"], "fuente": doc["url"]}]  # la «fuente» de la validación es la propia página
    publicado = doc.get("fecha_publicacion", "")
    filas = []
    for tarea, llamada in (("resumen", lambda: resumir(doc["text"], publicado, a.modelo)),
                           ("faq", lambda: generar_faq(doc["text"], a.preguntas, publicado, a.modelo))):
        t0, error, salida = time.time(), "", {}
        try:
            salida = llamada().model_dump()
        except Exception as e:  # noqa: BLE001
            error = str(e)[:300]
        texto = json.dumps(salida, ensure_ascii=False)
        filas.append({"tarea": tarea, "documento": doc["title"], "url": doc["url"], "modelo": a.modelo, "fecha": date.today().isoformat(),
                      "segundos": f"{time.time() - t0:.1f}", "sin_respaldo": " | ".join(datos_sin_respaldo(texto, fragmentos)) if salida else "",
                      "salida": texto, "error": error})
        print(f"{tarea}: {'ERROR ' + error[:80] if error else 'listo'} ({filas[-1]['segundos']} s); datos sin respaldo: {filas[-1]['sin_respaldo'] or 'ninguno'}", flush=True)
    ruta = SALIDA / f"resumen_faq_{a.modelo}.csv"
    with ruta.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(filas)
    print(f"Guardado en {ruta.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
