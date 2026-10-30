import importlib.util
import json

from conftest import RAIZ

CURADURIA = RAIZ / "data" / "4_curaduria"


def _cargar_script(nombre):
    spec = importlib.util.spec_from_file_location(nombre, RAIZ / "scripts" / f"{nombre}.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_fragmentos_sin_vacios_ni_duplicados_y_de_tamano_acotado():
    chunks = [json.loads(ln) for ln in (CURADURIA / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(chunks) == len({c["chunk_id"] for c in chunks})
    assert all(c["texto"].strip() for c in chunks)
    assert max(len(c["texto"]) for c in chunks) < 1500  # 1.000 de tamaño + el resto corto que se pega al último


def test_los_datos_clave_sobreviven_al_fragmentado():
    texto = " ".join(json.loads(ln)["texto"] for ln in (CURADURIA / "chunks.jsonl").read_text(encoding="utf-8").splitlines())
    for dato in _cargar_script("06_construir_chunks").DATOS_CLAVE:
        assert dato in texto, dato


def test_fragmentar_una_sede_da_un_fragmento_por_linea():
    m = _cargar_script("06_construir_chunks")
    doc = {"text": "## Valle del Cauca\n- **Tienda A** (Cali) horario 8-5\n- **Tienda B** (Tuluá) horario 9-6", "categoria": "sedes"}
    partes = m.fragmentar(doc, splitter=None)
    assert len(partes) == 2 and partes[0]["texto"].startswith("Valle del Cauca. ")
