# Guía de contribución

Gracias por tu interés en contribuir al **Asistente virtual de Celsia**.

La documentación central del proyecto está en [`CONSTITUTION.md`](./CONSTITUTION.md).
Antes de tu primera contribución, léela junto con el [Código de conducta](./CODE_OF_CONDUCT.md).

## Requisitos previos

| Herramienta | Versión | Notas |
|-------------|---------|-------|
| [Python](https://www.python.org/downloads/) | 3.12 | Fijada en `.python-version` |
| [`uv`](https://docs.astral.sh/uv/getting-started/installation/) | Última estable | Gestor de paquetes y entornos |
| [Git](https://git-scm.com/) | Última estable | Control de versiones |
| [Ollama](https://ollama.com/) | Última estable | Embeddings y modelo local de respaldo |
| [GitHub CLI](https://cli.github.com/) | Opcional | Facilita los PR |

> **Regla del proyecto:** está prohibido usar `pip` o `requirements.txt`. Toda la gestión
> de dependencias pasa por `uv`.

## Configuración del entorno

```bash
git clone https://github.com/mariastefuentes/taaml-celsia-asistente.git
cd taaml-celsia-asistente
make setup
make check
```

`make setup` instala las dependencias, crea el `.env` y descarga los modelos de Ollama.
`make` sin argumentos muestra todos los atajos.

## Flujo de trabajo con Git

La rama `main` es la rama estable: **no se trabaja directamente sobre ella**.

1. Actualiza `main`: `git checkout main && git pull`.
2. Crea una rama descriptiva: `git checkout -b feat/nombre-corto`.

   | Prefijo | Uso |
   |---------|-----|
   | `feat/` | Nueva funcionalidad |
   | `fix/` | Corrección de un error |
   | `docs/` | Documentación |
   | `refactor/` | Refactorización sin cambio de comportamiento |
   | `test/` | Pruebas |
   | `chore/` | Mantenimiento o configuración |

3. Trabaja en commits pequeños.
4. Abre un Pull Request hacia `main`.

Nunca hagas `push` a `main` "para ver si funciona": verifica antes con `make check`.

## Estándares de código

- Estilo: PEP 8 y PEP 257, con Ruff.
- Nombres: `snake_case` para funciones y variables, `PascalCase` para clases y
  `UPPER_CASE` para constantes.
- Pruebas con `pytest`, sin Gemini ni Ollama (solo componentes).
- Nunca subas secretos (`.env`, claves), datos pesados ni entornos virtuales.

```bash
make lint      # errores de código con ruff y lock vigente
make test      # pruebas automáticas
make check     # lint + pruebas: lo mismo que corre el CI
make format    # da formato con ruff (revisa el diff antes del commit)
make clean     # borra cachés
```

## Mensajes de commit

Se usa [Conventional Commits](https://www.conventionalcommits.org/), en español y con la
descripción en imperativo:

```text
<tipo>(<ámbito opcional>): <descripción breve>
```

Tipos: `feat`, `fix`, `docs`, `refactor`, `style`, `test` y `chore`.

El hook de commit (GGA) revisa el código antes de cada commit. No se salta: si falla, se
corrige y se repite el commit.

## Pull Requests

1. Verifica que tu rama esté al día con `main`.
2. Abre el PR y completa la plantilla.
3. Usa un título con prefijo convencional y un solo propósito por PR.
4. Espera a que el CI esté en verde.
5. Se integra con **Create a merge commit**, para conservar cada commit de la rama.

## Reportar problemas

Usa las plantillas de `.github/ISSUE_TEMPLATE/` (error, funcionalidad o investigación)
e incluye contexto, pasos para reproducir y evidencia.

## Mantener la constitución

Cualquier cambio arquitectónico, tecnológico o de proceso se escribe en
[`.specify/memory/constitution.md`](.specify/memory/constitution.md), en el mismo commit
del cambio. El checklist del PR lo verifica.

## Contribuidores

El archivo [`.mailmap`](./.mailmap) une los nombres y correos de cada persona. Si tu
identidad aparece repetida en `git shortlog -sne`, agrega una línea ahí.

## Licencia

Al contribuir, aceptas que tus aportes se distribuyan bajo la [Licencia MIT](./LICENSE).
