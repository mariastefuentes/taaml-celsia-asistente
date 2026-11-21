"""Valida las skills de `.opencode/skills`: frontmatter, nombre, tamaño y seguridad.

No ejecuta las skills ni llama a ningún modelo. El CI corre este script con `make skills-check`.

Uso: uv run python scripts/verificar_skills.py [ruta-de-skills]
"""

import sys
from pathlib import Path

from taaml.skills import RUTA_SKILLS, verificar_skills


def main() -> int:
    raiz = Path(sys.argv[1]) if len(sys.argv) > 1 else RUTA_SKILLS
    errores = verificar_skills(raiz)
    if not errores:
        print(f"Skills OK en {raiz}: frontmatter, tamaño y seguridad.")
        return 0
    print("Skills con errores:")
    for error in errores:
        print(f"  - {error}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
