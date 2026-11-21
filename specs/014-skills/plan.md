# Plan 014: skills dentro del repositorio

1. `src/taaml/skills.py`: `RUTA_SKILLS`, `MAX_LINEAS`, `verificar_skills(raiz)`. Sin dependencias nuevas: el frontmatter se lee con un parser mínimo de `clave: valor`.
2. `scripts/verificar_skills.py`: entrada de línea de comandos; imprime los errores y sale con código 1.
3. `tests/test_skills.py`: pruebas con carpetas temporales y una prueba de integración con las skills reales.
4. `Makefile`: objetivo `skills-check`, incluido en `check`, y su línea en el menú.
5. `.github/workflows/ci.yml`: paso «Validar skills» entre `make lint` y `make test`.
6. `.opencode/skills/corpus-medallion/SKILL.md` y `.opencode/skills/agente-rag-router/SKILL.md`: contenido migrado desde `mariastefuentes/taaml-skills`, sin scripts.
7. Gobernanza: D24 en `docs/decisiones.md` (y D17 actualizada), constitución (estructura, regla y bitácora), `AGENTS.md`, README y plantilla de PR.
8. Verificación: `make skills-check`, `make test`, `make lint` y revisión de que `.env` no aparece en el diff.
