"""LIMPIAR LA MEMORIA DE LARGO PLAZO ANTES DE LA DEMO. No llama a ningún modelo ni gasta nada.

El Store (`data/memoria/largo_plazo.sqlite`, o PostgreSQL si hay `DATABASE_URL`) guarda lo que cada cliente contó de sí mismo. Si quedan datos de ensayos,
la demo de memoria parece que «recuerda» por datos viejos. Sin argumentos solo lista lo guardado; con `--borrar` lo elimina. Las conversaciones (checkpointer) no se tocan.
Uso:  uv run python scripts/30_limpiar_memoria_demo.py             (lista)
      uv run python scripts/30_limpiar_memoria_demo.py --borrar    (borra todo lo guardado de todos los clientes)
"""
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from taaml.agente import almacen_de_largo_plazo, datos_del_cliente, olvidar_cliente  # noqa: E402


def clientes_con_datos(almacen: Any) -> list[str]:
    """Identificadores de los clientes que tienen algo guardado."""
    return sorted({ns[1] for ns in almacen.list_namespaces(prefix=("perfil",)) if len(ns) > 1})


def limpiar(almacen: Any, borrar: bool) -> dict[str, list[str]]:
    """Devuelve lo guardado por cliente; con `borrar` lo elimina (y el resultado es lo que había antes de borrar)."""
    antes = {c: datos_del_cliente(c, almacen) for c in clientes_con_datos(almacen)}
    if borrar:
        for cliente in antes:
            olvidar_cliente(cliente, almacen)
    return antes


def main() -> None:
    borrar = "--borrar" in sys.argv
    antes = limpiar(almacen_de_largo_plazo(), borrar)
    if not antes:
        print("La memoria de largo plazo está vacía: lista para la demo.")
        return
    for cliente, datos in antes.items():
        print(f"{cliente[:8]}…  " + " | ".join(datos))
    total = sum(len(d) for d in antes.values())
    print(f"\n{total} datos de {len(antes)} clientes " + ("BORRADOS." if borrar else "guardados. Para borrarlos: --borrar (o `make demo-limpiar`)."))


if __name__ == "__main__":
    main()
