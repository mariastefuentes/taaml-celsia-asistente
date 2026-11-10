"""UMBRAL DE SIMILITUD (clase 5): ¿conviene dejar pasar al modelo solo los fragmentos con coseno >= τ? No usa la API del modelo; necesita Ollama (embeddings).

Para cada τ mide dos cosas con el conjunto de prueba:
  - preguntas con respuesta (35): en cuántas la respuesta sigue entre los fragmentos que pasan el umbral (lo que se pierde si el umbral es alto);
  - preguntas negativas (24, sin respuesta en el corpus): en cuántas NINGÚN fragmento pasa el umbral (lo que se gana: el modelo ni ve contexto y se abstiene).
Uso:  uv run python scripts/20_umbral_similitud.py
Resultado: docs/2 - Conjunto de prueba/resultados/umbral_similitud.csv
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from taaml.recuperacion import buscar  # noqa: E402

TALLER = ROOT / "docs"
INVENTARIO = TALLER / "1 - Analisis de la empresa" / "inventario_intenciones.csv"
PRUEBA = TALLER / "2 - Conjunto de prueba" / "conjunto_de_prueba.csv"
SALIDA = TALLER / "2 - Conjunto de prueba" / "resultados" / "umbral_similitud.csv"
K = 12
UMBRALES = [0.0, 0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.78]


def main() -> None:
    inventario = {f["id"]: f for f in csv.DictReader(INVENTARIO.open(encoding="utf-8-sig", newline=""))}
    preguntas = list(csv.DictReader(PRUEBA.open(encoding="utf-8-sig", newline="")))
    con_respuesta, negativas = [], []
    for p in preguntas:
        recuperados = buscar(p["pregunta"], K, "embeddings")
        if recuperados[0]["metodo"] != "embeddings":
            sys.exit("Ollama no respondió: sin embeddings no hay coseno que medir.")
        if p["tipo_prueba"] == "respuesta":
            patron = re.compile(inventario[p["intencion_id"]]["regex_cobertura"], re.I)
            puntaje = next((r["puntaje"] for r in recuperados if patron.search(r["texto"])), None)  # el del primer fragmento que sí responde
            con_respuesta.append((puntaje, recuperados[0]["puntaje"]))
        else:
            negativas.append(recuperados[0]["puntaje"])
    filas = []
    print(f"{'τ':>5} | respuesta conservada | negativas sin contexto")
    for tau in UMBRALES:
        conservadas = sum(1 for p, _ in con_respuesta if p is not None and p >= tau)
        sin_contexto = sum(1 for m in negativas if m < tau)
        filas.append({"tau": tau, "respuesta_conservada": conservadas, "de_respuesta": len(con_respuesta), "negativas_sin_contexto": sin_contexto, "de_negativas": len(negativas)})
        print(f"{tau:>5} | {conservadas:>2} de {len(con_respuesta)} ({conservadas / len(con_respuesta):.0%})     | {sin_contexto:>2} de {len(negativas)} ({sin_contexto / len(negativas):.0%})       ")
    with SALIDA.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(filas)
    print(f"Guardado en {SALIDA.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
