"""CATÁLOGO DE LAS 20 HERRAMIENTAS DEL AGENTE: qué hace cada una, qué argumentos recibe y si pide aprobación humana.

Uso:
    make herramientas
    uv run python scripts/49_listar_herramientas.py --json   # para pegarlo en una lámina o revisarlo con un script

No llama al modelo ni gasta cuota: lee el mismo catálogo (`HERRAMIENTAS`) que ve el agente en cada turno. Sirve para la
sustentación (mostrar el catálogo) y para revisar que siga habiendo 20, con nombres únicos y esquema Pydantic.
"""

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from taaml.agente import APROBACION_HUMANA, HERRAMIENTAS  # noqa: E402

# Las diez que también expone el servidor MCP `celsia` (src/taaml/servidor_mcp.py): consultan sin cambiar nada.
SOLO_LECTURA = {
    "buscar_en_base",
    "consultar_sedes",
    "consultar_contactos",
    "consultar_catalogo",
    "consultar_canales_de_atencion",
    "consultar_cobertura",
    "consultar_tramite_en_linea",
    "consultar_politica_de_datos",
    "verificar_canal_oficial",
    "calcular_factura_estimada",
}

# Leen lo que el cliente contó o sus reclamos: no cambian nada, pero necesitan su identidad.
LECTURA_DEL_CLIENTE = {
    "recordar_datos_del_cliente",
    "listar_datos_del_cliente",
    "consultar_mis_reclamos",
    "consultar_estado_reclamo",
}


def tipo(nombre: str) -> str:
    """Lectura, lectura del cliente, escritura o aprobación humana: lo que hay que explicar en la sustentación."""
    if nombre in APROBACION_HUMANA:
        return "aprobación humana"
    if nombre in SOLO_LECTURA:
        return "lectura"
    if nombre in LECTURA_DEL_CLIENTE:
        return "lectura del cliente"
    return "escritura"


def catalogo() -> list[dict]:
    """Las 20 herramientas como datos: nombre, para qué sirve, tipo y argumentos que ve el modelo."""
    filas = []
    for herramienta in HERRAMIENTAS:
        esquema = herramienta.tool_call_schema.model_json_schema()
        filas.append(
            {
                "nombre": herramienta.name,
                "descripcion": (herramienta.description or "").strip().splitlines()[0],
                "tipo": tipo(herramienta.name),
                "argumentos": list((esquema.get("properties") or {}).keys()),
                "obligatorios": esquema.get("required") or [],
            }
        )
    return filas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="imprime el catálogo como JSON en vez de texto")
    args = ap.parse_args()
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    filas = catalogo()
    if args.json:
        print(json.dumps(filas, ensure_ascii=False, indent=2))
        return 0

    print(f"Herramientas del agente de Celsia: {len(filas)}")
    for i, fila in enumerate(filas, 1):
        print(f"{i:02d}. {fila['nombre']} [{fila['tipo']}]")
        print(f"    {fila['descripcion'][:150]}")
        print(f"    argumentos: {', '.join(fila['argumentos']) or 'ninguno'}")
    print(f"\nLectura: {sum(f['tipo'] == 'lectura' for f in filas)}"
          f" · Lectura del cliente: {sum(f['tipo'] == 'lectura del cliente' for f in filas)}"
          f" · Escritura: {sum(f['tipo'] == 'escritura' for f in filas)}"
          f" · Aprobación humana: {sum(f['tipo'] == 'aprobación humana' for f in filas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
