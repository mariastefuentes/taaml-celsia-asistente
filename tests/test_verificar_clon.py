"""El verificador del clon limpio (script 45): detecta comandos `make` inexistentes y claves en el ejemplo de `.env`."""

import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _cargar_verificador():
    espec = importlib.util.spec_from_file_location("verificar_clon", RAIZ / "scripts" / "45_verificar_clon.py")
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    return modulo


def test_el_verificador_detecta_comandos_make_que_no_existen_y_claves_en_el_ejemplo():
    v = _cargar_verificador()
    makefile = "test:\n\tuv run pytest\n\nlint:\n\truff\nVARIABLE := 1\n"
    assert v.objetivos_del_makefile(makefile) == {"test", "lint"}
    readme = "Corre `make test` y luego:\n```\nmake api\nmake lint\n```\nEscribir make algo en texto suelto no cuenta."
    assert v.comandos_make_del_readme(readme) == {"test", "api", "lint"}
    assert v.readme_sin_objetivo(readme, makefile) == ["api"]
    assert v.claves_en_env_example("DEEPSEEK_API_KEY=sk-abcdefghijklmnopqrstuv\n# GOOGLE=AIzaABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\nCHAT_TOKEN=\n") == ["DEEPSEEK_API_KEY"]


def test_el_readme_y_el_makefile_del_repositorio_estan_de_acuerdo():
    v = _cargar_verificador()
    revisiones = v.revisiones_de_texto(RAIZ)
    assert all(ok for _, ok, _ in revisiones), [r for r in revisiones if not r[1]]
