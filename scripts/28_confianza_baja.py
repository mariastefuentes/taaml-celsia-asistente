"""SEÑAL DE CONFIANZA BAJA (Taller 2, enrutador): mide el umbral y prueba cómo responde el agente cuando la recuperación es poco segura.

Parte 1 (sin costo, necesita Ollama): puntaje del mejor fragmento (coseno) en las 35 preguntas con respuesta y las 24 sin respuesta del conjunto de prueba, y cuántas quedarían marcadas con cada umbral.
Parte 2 (GASTA CUOTA de Gemini, solo con --agente): 3 preguntas, cada una en una conversación nueva (unas 2 llamadas al modelo por pregunta):
  una sin respuesta en el corpus y marcada, una con respuesta y marcada (falsa alarma), una con respuesta y no marcada (control).
Uso:  uv run python scripts/28_confianza_baja.py            (solo parte 1)
      uv run python scripts/28_confianza_baja.py --agente   (también parte 2)
Resultado: docs/2 - Conjunto de prueba/resultados/confianza_baja.csv
"""
import csv
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from taaml.agente import FRAGMENTOS_AGENTE, UMBRAL_CONFIANZA, conversar, crear_agente  # noqa: E402
from taaml.recuperacion import buscar  # noqa: E402

PRUEBA = ROOT / "docs" / "2 - Conjunto de prueba" / "conjunto_de_prueba.csv"
SALIDA = ROOT / "docs" / "2 - Conjunto de prueba" / "resultados" / "confianza_baja.csv"
UMBRALES = (0.40, 0.45, 0.50, 0.55)


def main() -> None:
    preguntas = list(csv.DictReader(PRUEBA.open(encoding="utf-8-sig", newline="")))
    medidas = []
    for p in preguntas:
        mejor = buscar(p["pregunta"], FRAGMENTOS_AGENTE)[0]
        if mejor["metodo"] != "embeddings":
            sys.exit("Ollama no respondió: sin embeddings no hay coseno que medir.")
        medidas.append((p["tipo_prueba"], p["pregunta"], mejor["puntaje"]))
    con = [m for m in medidas if m[0] == "respuesta"]
    sin = [m for m in medidas if m[0] != "respuesta"]
    filas = []
    print(f"{'umbral':>6} | preguntas con respuesta marcadas | preguntas sin respuesta marcadas")
    for t in UMBRALES:
        a, b = sum(m[2] < t for m in con), sum(m[2] < t for m in sin)
        print(f"{t:>6} | {a:>2} de {len(con)} ({a / len(con):.0%})              | {b:>2} de {len(sin)} ({b / len(sin):.0%})")
        filas.append({"umbral": t, "con_respuesta_marcadas": a, "con_respuesta": len(con), "sin_respuesta_marcadas": b, "sin_respuesta": len(sin)})
    with SALIDA.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]), quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(filas)
    print(f"Guardado en {SALIDA.relative_to(ROOT)} (umbral en uso: {UMBRAL_CONFIANZA})")
    if "--agente" not in sys.argv:
        return
    elegidas = [("sin respuesta, marcada", min((m for m in sin if m[2] < UMBRAL_CONFIANZA), key=lambda m: m[2])),
                ("con respuesta, marcada (falsa alarma)", min((m for m in con if m[2] < UMBRAL_CONFIANZA), key=lambda m: m[2])),
                ("con respuesta, no marcada (control)", max((m for m in con if m[2] >= UMBRAL_CONFIANZA), key=lambda m: m[2]))]
    agente = crear_agente()
    for rotulo, (_, pregunta, puntaje) in elegidas:
        respuesta, _ = conversar(pregunta, f"confianza-{uuid4().hex[:8]}", agente=agente)
        print(f"\n[{rotulo}] coseno {puntaje:.3f}\n  Pregunta: {pregunta}\n  Respuesta: {respuesta}")


if __name__ == "__main__":
    main()
