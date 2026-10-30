"""El conjunto de prueba cumple lo que pide el enunciado."""
import csv
from collections import Counter

from conftest import RAIZ


def test_conjunto_de_prueba_cumple_el_minimo_del_enunciado():
    ruta = RAIZ / "docs" / "2 - Conjunto de prueba" / "conjunto_de_prueba.csv"
    filas = list(csv.DictReader(ruta.open(encoding="utf-8-sig", newline="")))
    ids = [f["id"] for f in filas]
    assert len(ids) == len(set(ids)) and len(filas) >= 20
    assert Counter(f["tipo_prueba"] for f in filas) == {"respuesta": 35, "negativa": 24}
    assert sum(f["forma"] == "inyeccion" for f in filas) >= 4
    assert all(f["respuesta_esperada"].strip() for f in filas)
