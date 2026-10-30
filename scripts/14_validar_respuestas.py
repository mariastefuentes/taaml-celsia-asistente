"""POST-VALIDACIÓN: revisa, sin llamar a ningún modelo, si las cifras, correos y enlaces de las respuestas ya guardadas
aparecen escritos en los fragmentos que el asistente recibió (columna `fragmentos` de los CSV de resultados).
Uso:  uv run python scripts/14_validar_respuestas.py [archivo.csv ...]   (por defecto, las corridas rag con prompt v3)
Resultado: docs/2 - Conjunto de prueba/resultados/validacion_datos.csv
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from taaml.recuperacion import cargar_fragmentos  # noqa: E402
from taaml.validacion import datos_sin_respaldo  # noqa: E402

RESULTADOS = ROOT / "docs" / "2 - Conjunto de prueba" / "resultados"


def main() -> None:
    archivos = [Path(a) for a in sys.argv[1:]] or sorted(RESULTADOS.glob("resultados_*_rag*_v3.csv"))
    por_id = {f["chunk_id"]: f for f in cargar_fragmentos()}
    filas = []
    for archivo in archivos:
        respuestas = [r for r in csv.DictReader(archivo.open(encoding="utf-8-sig", newline="")) if r["respuesta"] and not r["error"]]
        con_datos = 0
        for r in respuestas:
            fragmentos = [por_id[i] for i in r["fragmentos"].split() if i in por_id]
            dudosos = datos_sin_respaldo(r["respuesta"], fragmentos)
            con_datos += bool(dudosos)
            if dudosos:
                filas.append({"corrida": archivo.stem, "id": r["id"], "calificacion": r["calificacion"], "sin_respaldo": " | ".join(dudosos)})
        print(f"{archivo.stem}: {con_datos} de {len(respuestas)} respuestas con datos sin respaldo")
    destino = RESULTADOS / "validacion_datos.csv"
    with destino.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["corrida", "id", "calificacion", "sin_respaldo"], quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(filas)
    print(f"Guardado en {destino.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
