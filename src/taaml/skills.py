"""Validación de las skills de `.opencode/skills` (frontmatter, tamaño y seguridad).

No ejecuta las skills: revisa que cada carpeta tenga un `SKILL.md` con `name` y `description`,
que el nombre coincida con la carpeta, que el archivo no pase de 500 líneas y que no traiga
claves, rutas absolutas ni instrucciones para leer el `.env`.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUTA_SKILLS = ROOT / ".opencode" / "skills"
MAX_LINEAS = 500
NOMBRE = re.compile(r"^[a-z0-9-]{1,64}$")
SECRETOS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{10,}"),
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_-]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)
RUTA_ABSOLUTA = re.compile(r"(?<![\w/])(?:[A-Za-z]:\\|/(?:home|Users)/)")
LECTURA_ENV = re.compile(r"(?i)\b(cat|type|get-content|more|less)\s+\.env\b")


def _frontmatter(texto: str) -> dict[str, str]:
    """Campos `clave: valor` del bloque YAML inicial; vacío si no hay bloque."""
    lineas = texto.splitlines()
    if not lineas or lineas[0].strip() != "---":
        return {}
    cierre = next((i for i, linea in enumerate(lineas[1:], start=1) if linea.strip() == "---"), None)
    if cierre is None:
        return {}
    campos = {}
    for linea in lineas[1:cierre]:
        if ":" not in linea or linea.lstrip().startswith("#"):
            continue
        clave, _, valor = linea.partition(":")
        campos[clave.strip()] = valor.strip().strip("'\"")
    return campos


def verificar_skills(raiz: Path | None = None) -> list[str]:
    """Lista de errores de las skills; lista vacía si todo está bien (o si no hay skills)."""
    raiz = raiz or RUTA_SKILLS
    if not raiz.is_dir():
        return []
    errores = []
    if (raiz / "SKILLS.md").exists():
        errores.append("usa SKILL.md (singular) dentro de cada carpeta, no SKILLS.md")
    nombres = set()
    for carpeta in sorted(p for p in raiz.iterdir() if p.is_dir() and not p.name.startswith(".")):
        archivo = carpeta / "SKILL.md"
        if not archivo.is_file():
            errores.append(f"{carpeta.name}: falta SKILL.md")
            continue
        if (carpeta / "SKILLS.md").exists():
            errores.append(f"{carpeta.name}: el archivo se llama SKILL.md, no SKILLS.md")
        texto = archivo.read_text(encoding="utf-8")
        campos = _frontmatter(texto)
        nombre = campos.get("name", "")
        descripcion = campos.get("description", "")
        if not nombre:
            errores.append(f"{carpeta.name}: falta name en el frontmatter")
        else:
            if not NOMBRE.fullmatch(nombre):
                errores.append(f"{carpeta.name}: name debe ser minúsculas, números o guiones (1-64)")
            if nombre != carpeta.name:
                errores.append(f"{carpeta.name}: name «{nombre}» no coincide con la carpeta")
            if nombre in nombres:
                errores.append(f"{carpeta.name}: name repetido «{nombre}»")
            nombres.add(nombre)
        if not descripcion:
            errores.append(f"{carpeta.name}: falta description")
        elif len(descripcion) > 1024:
            errores.append(f"{carpeta.name}: description pasa de 1024 caracteres")
        lineas = texto.splitlines()
        if len(lineas) > MAX_LINEAS:
            errores.append(f"{carpeta.name}: {len(lineas)} líneas (máximo {MAX_LINEAS})")
        if any(patron.search(texto) for patron in SECRETOS):
            errores.append(f"{carpeta.name}: posible secreto en SKILL.md")
        if RUTA_ABSOLUTA.search(texto):
            errores.append(f"{carpeta.name}: ruta absoluta en SKILL.md")
        if LECTURA_ENV.search(texto):
            errores.append(f"{carpeta.name}: instrucción para leer .env")
    return errores
