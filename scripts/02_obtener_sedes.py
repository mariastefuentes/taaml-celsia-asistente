"""CAPA BRONZE (sedes): guarda tal cual la lista publica de sedes de Celsia.

La pagina celsia.com/es/encuentranos/ no tiene texto: incrusta un visor de ArcGIS (gis.celsia.com).
Ese visor lee una capa publica ("Headquaters - Sedes"); aqui se consulta esa misma capa con UNA peticion
y la respuesta se guarda sin modificar en data/1_bronze/sedes_raw.json.
El formato legible se genera en Silver (03_construir_silver.py).

Uso:  uv run python scripts/02_obtener_sedes.py
"""
import json
from pathlib import Path

import requests

CAPA = "https://gis.celsia.com/host/rest/services/AppCustomerExperience/Headquaters/FeatureServer/0/query"
UA = "UAO-TAAML-StudentProject/1.0 (proyecto academico, Maestria IA UAO)"
BRONZE = Path(__file__).resolve().parent.parent / "data" / "1_bronze"


def main() -> None:
    resp = requests.get(
        CAPA,
        params={"where": "1=1", "outFields": "*", "returnGeometry": "false", "f": "json"},
        headers={"User-Agent": UA},
        timeout=40,
    )
    resp.raise_for_status()
    datos = resp.json()
    BRONZE.mkdir(parents=True, exist_ok=True)
    (BRONZE / "sedes_raw.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(datos['features'])} sedes guardadas en data/1_bronze/sedes_raw.json")


if __name__ == "__main__":
    main()
