"""EXPORTA LAS CONVERSACIONES REALES de los ensayos con celulares, para analizarlas con t-SNE en lugar de las simuladas.

  make exportar-chats                                       # usa la misma base que `make api`
  DATABASE_URL=postgresql://... uv run python scripts/38_exportar_conversaciones_reales.py

Lee los hilos que la API guardó en PostgreSQL (el teléfono nunca se guarda: solo su hash) y los deja en
`data/analisis/reales/conversaciones.jsonl`, con el mismo formato que las simuladas (`data/analisis/conversaciones.jsonl`) pero con
`simulada: false`. La carpeta está en `.gitignore`: son mensajes de personas y no se suben a Git.

Antes de ensayar, avisa a quienes escriban que sus mensajes se guardan para el análisis. Estas conversaciones son de compañeros y
conocidos, no de clientes de Celsia: el informe tiene que decirlo así. Con pocas conversaciones el t-SNE no dice nada (usa 30 o más).
"""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
SALIDA = RAIZ / "data" / "analisis" / "reales"
MINIMO_RECOMENDADO = 30


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--minimo-turnos", type=int, default=1, help="omite las conversaciones con menos turnos del cliente que estos")
    args = ap.parse_args()
    if not os.environ.get("DATABASE_URL"):
        sys.exit("Falta DATABASE_URL: usa `make exportar-chats` (levanta o reutiliza el PostgreSQL local de la demostración).")

    from taaml.agente import almacen_de_memoria
    from taaml.conversaciones import leer_conversaciones

    conversaciones = [
        c for c in leer_conversaciones(almacen_de_memoria()) if sum(t["rol"] == "cliente" for t in c["turnos"]) >= args.minimo_turnos
    ]
    for c in conversaciones:
        c["simulada"] = False
    SALIDA.mkdir(parents=True, exist_ok=True)
    destino = SALIDA / "conversaciones.jsonl"
    destino.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in conversaciones) + ("\n" if conversaciones else ""), encoding="utf-8")

    herramientas = Counter(h for c in conversaciones for h in c["herramientas"])
    print(f"{len(conversaciones)} conversaciones, {sum(c['fallida'] for c in conversaciones)} fallidas, herramientas: {dict(herramientas)}")
    print(f"Guardado en {destino}")
    if len(conversaciones) < MINIMO_RECOMENDADO:
        print(f"Aviso: son menos de {MINIMO_RECOMENDADO}; con tan pocas, los grupos del t-SNE no son confiables. Ensayen más.")


if __name__ == "__main__":
    main()
