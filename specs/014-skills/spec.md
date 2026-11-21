---
estado: implementada
escrita: 2026-11-21
---
# Spec 014: skills del proyecto dentro del repositorio

Hasta ahora las skills propias (`corpus-medallion` y `agente-rag-router`) vivían en el repositorio público `mariastefuentes/taaml-skills` y este proyecto solo las enlazaba (D17). Después se sumaron `frontend-design`, de `anthropics/skills` (Apache 2.0), y `jan-project-standard`, de `hamsomp3/jan_skills_repository` (MIT), con sus licencias en la carpeta. La segunda trae `references/`, `assets/` y `scripts/`. Esta spec las trae al repositorio, **solo para OpenCode**, y deja el repositorio externo como espejo.

## Qué se necesita
1. **Las skills en el repositorio.** Una carpeta por skill en `.opencode/skills/<nombre>/SKILL.md`, con frontmatter `name` y `description`, y sin claves. El nombre de la carpeta debe coincidir con `name`. Las de terceros conservan su licencia en la carpeta y pueden traer `references/`, `assets/` y scripts de apoyo revisados; hoy son `corpus-medallion` y `agente-rag-router` (propias), `frontend-design` (de `anthropics/skills`, Apache 2.0) y `jan-project-standard` (de `hamsomp3/jan_skills_repository`, MIT).
2. **Validador propio.** `src/taaml/skills.py` con `verificar_skills()`: frontmatter presente, `name` válido (minúsculas, números y guiones; 1 a 64), coincidencia con la carpeta, `description` de 1 a 1024 caracteres, máximo 500 líneas y ausencia de secretos, rutas absolutas (fuera de bloques de código) e instrucciones para leer el `.env`.
3. **Comando y CI.** `make skills-check` ejecuta `scripts/verificar_skills.py`; el CI corre la misma comprobación antes de las pruebas y `make check` la incluye.
4. **Pruebas.** `tests/test_skills.py` cubre una skill válida, carpeta sin `SKILL.md`, nombre inválido o que no coincide, falta de `description`, más de 500 líneas, secreto, ruta absoluta, lectura del `.env`, `SKILLS.md` mal nombrado y las skills reales del repositorio.
5. **Gobernanza.** Decisión D24 en `docs/decisiones.md`, estructura y bitácora de la constitución, `AGENTS.md`, README y casilla de skills en la plantilla de PR.
6. **Seguridad.** Se conserva el reporte de SkillSpector de `corpus-medallion`; los de `agente-rag-router`, `frontend-design` y `jan-project-standard` quedan pendientes. Los scripts de apoyo no se ejecutan en el CI y se revisan a mano.

## Cómo se comprueba
- `make skills-check` debe pasar con las skills del repositorio.
- `uv run python -m pytest tests/test_skills.py` debe pasar (gratis, sin modelos ni red).
- `make test` y `make lint` deben seguir verdes.
- El CI del PR ejecuta `make lint`, `make skills-check` y `make test`.

## Lo que se aprendió
- OpenCode busca `.opencode/skills/<nombre>/SKILL.md` (singular, mayúsculas); si el archivo se llama distinto, la skill no se carga.
- Una skill es un procedimiento reutilizable, no una copia de `AGENTS.md`: las reglas duras siguen en `AGENTS.md` y la constitución.
- Validar el frontmatter y los secretos en el CI evita skills que no cargan o que filtran claves.

## Fuera de alcance y pendiente
- `.claude/skills/` y `.agents/skills/`: el equipo usa solo OpenCode; no se duplican.
- Sincronización automática con `mariastefuentes/taaml-skills`: el repositorio externo queda como espejo manual.
- SkillSpector de `agente-rag-router`, `frontend-design` y `jan-project-standard`: pendientes de una revisión de seguridad dedicada.
