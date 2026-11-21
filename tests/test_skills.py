"""Pruebas del validador de skills (sin modelos ni red)."""

from pathlib import Path

from taaml.skills import MAX_LINEAS, verificar_skills


def _crear(raiz: Path, carpeta: str, frontmatter: str, cuerpo: str = "# Titulo\n") -> None:
    destino = raiz / carpeta
    destino.mkdir()
    (destino / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n{cuerpo}", encoding="utf-8")


def test_una_skill_valida_pasa(tmp_path):
    _crear(tmp_path, "mi-skill", "name: mi-skill\ndescription: Hace algo útil y repetible.")
    assert verificar_skills(tmp_path) == []


def test_sin_carpeta_de_skills_no_falla(tmp_path):
    assert verificar_skills(tmp_path / "no-existe") == []
    assert verificar_skills(tmp_path) == []


def test_nombre_que_no_coincide_con_la_carpeta(tmp_path):
    _crear(tmp_path, "mi-skill", "name: otra-cosa\ndescription: Hace algo.")
    assert any("no coincide" in error for error in verificar_skills(tmp_path))


def test_falta_name_o_description(tmp_path):
    _crear(tmp_path, "sin-name", "description: Hace algo.")
    _crear(tmp_path, "sin-description", "name: sin-description")
    errores = verificar_skills(tmp_path)
    assert any("falta name" in error for error in errores)
    assert any("falta description" in error for error in errores)


def test_name_invalido_por_mayusculas_o_espacios(tmp_path):
    _crear(tmp_path, "Mi Skill", "name: Mi Skill\ndescription: Hace algo.")
    assert any("minúsculas" in error for error in verificar_skills(tmp_path))


def test_falta_el_archivo_skill_md(tmp_path):
    (tmp_path / "vacia").mkdir()
    assert any("falta SKILL.md" in error for error in verificar_skills(tmp_path))


def test_archivo_con_el_nombre_plural(tmp_path):
    (tmp_path / "SKILLS.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    assert any("SKILL.md (singular)" in error for error in verificar_skills(tmp_path))


def test_posible_secreto(tmp_path):
    _crear(tmp_path, "mi-skill", "name: mi-skill\ndescription: Hace algo.", "clave sk-1234567890abcdef")
    assert any("secreto" in error for error in verificar_skills(tmp_path))


def test_ruta_absoluta(tmp_path):
    _crear(tmp_path, "mi-skill", "name: mi-skill\ndescription: Hace algo.", "Abre C:\\Users\\alguien")
    assert any("ruta absoluta" in error for error in verificar_skills(tmp_path))


def test_ruta_absoluta_dentro_de_un_bloque_de_codigo_no_falla(tmp_path):
    _crear(tmp_path, "mi-skill", "name: mi-skill\ndescription: Hace algo.", "```bash\ncd C:/Users/alguien\n```\n")
    assert verificar_skills(tmp_path) == []


def test_instruccion_para_leer_el_env(tmp_path):
    _crear(tmp_path, "mi-skill", "name: mi-skill\ndescription: Hace algo.", "Primero ejecuta `cat .env`.")
    assert any(".env" in error for error in verificar_skills(tmp_path))


def test_mas_de_500_lineas(tmp_path):
    _crear(tmp_path, "mi-skill", "name: mi-skill\ndescription: Hace algo.", "linea\n" * MAX_LINEAS)
    assert any("líneas" in error for error in verificar_skills(tmp_path))


def test_las_skills_del_repositorio_pasan():
    from taaml.skills import RUTA_SKILLS

    assert verificar_skills(RUTA_SKILLS) == []
