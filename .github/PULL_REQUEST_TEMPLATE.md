### 📝 Convención del título de la PR

Aplica un [prefijo convencional](https://www.conventionalcommits.org/) en el título, igual que en los commits:

| Prefijo | Cuándo usar | Ejemplo |
|---------|-------------|---------|
| `feat:` | Nueva funcionalidad o etapa del pipeline | `feat: pestaña Corpus con las etapas del scraping` |
| `fix:` | Corrección de errores | `fix: evitar que un fragmento cierre el bloque <contexto>` |
| `test:` | Pruebas nuevas o refactorizadas | `test: cubrir el scraper con robots.txt simulado` |
| `docs:` | Informe, README, specs, constitución | `docs: constitución del proyecto y plantilla de PR` |
| `chore:` | Mantenimiento, dependencias, Makefile, CI | `chore: menú de atajos en el Makefile` |

---

### 🧱 Módulo o componente afectado

Marca las áreas que toca esta PR:

- [ ] **Pipeline de datos** (`scripts/01`–`06`: Bronze → Silver → Gold → curaduría → chunks)
- [ ] **Recuperación e índice** (`src/taaml/recuperacion.py`, `sinonimos.py`, `reordenar.py`, `scripts/07`–`10`)
- [ ] **Respaldo y continuidad** (`src/taaml/respaldo.py`, `scripts/16_ensayo_demo.py`)
- [ ] **Prompts y tareas** (`prompts/`, `src/taaml/prompts.py`, `tareas.py`)
- [ ] **Evaluación y conjunto de prueba** (`scripts/09`–`14`, `docs/2 - Conjunto de prueba/`)
- [ ] **Aplicación** (`app.py`, `app_modulo1.py`)
- [ ] **Pruebas** (`tests/`)
- [ ] **Gobernanza** (`.specify/memory/constitution.md`, `specs/`, `.github/`, `.opencode/skills/`)
- [ ] **Documentación** (`README.md`, `AGENTS.md`, `docs/`)
- [ ] **Infraestructura** (`pyproject.toml`, `uv.lock`, `Makefile`, `.gitignore`, CI)

---

### 📚 Descripción de los cambios

<!--- Qué logra esta PR, la motivación y los detalles técnicos relevantes. -->

**Spec asociada:** <!-- Ej. specs/007-pestana-corpus -->

#### Resumen de cambios
-

#### Decisiones de diseño
<!--- Explica lo no obvio. Si te desviaste del plan o de tasks.md, di por qué. -->
-

#### Cómo probarlo
```bash
uv sync
make modulo1        # o make app
```

---

### ⚖️ Cumplimiento de la constitución

Verifica que la PR respeta [`.specify/memory/constitution.md`](../.specify/memory/constitution.md):

- [ ] **Solo `uv`:** no se agregó `requirements.txt` ni se usó `pip`/`conda`.
- [ ] **Datos de fuentes oficiales:** toda cifra, teléfono o enlace nuevo existe en el corpus con su fuente; no se inventó nada.
- [ ] **Scraping respetuoso:** `robots.txt`, `User-Agent` propio, `timeout` y pausa entre peticiones intactos.
- [ ] **Muestreo:** `temperature = 0.0` y `top_p = 0.1` en RAG y agentes; un cambio de prompt es una versión nueva.
- [ ] **Sin secretos ni datos personales:** no hay claves, `.env` ni datos de clientes en el diff.
- [ ] **Capas generadas:** no se editó a mano `data/1_bronze`, `2_silver` ni `3_gold`; los cambios salen de los scripts.
- [ ] **Trazabilidad:** si cambiaron datos, prompts o alcance, se volvieron a correr `08`, `09` y la evaluación correspondiente.
- [ ] La constitución o la spec se actualizaron en este mismo PR si el cambio lo amerita.

---

### ✅ Lista de chequeo pre-PR

- [ ] **Entorno:** el código corre con `uv` y Python **3.12**.
- [ ] **Pruebas:** `make test` pasa completo (indica abajo si hay pruebas omitidas y por qué).
- [ ] **Lint y lock:** `make lint` pasa (Ruff `F`,`E9` + `uv lock --check`).
- [ ] **Datos fuera de Git:** `data/1_bronze/`, `chroma/`, `indice_embeddings.npz`, `.env` y PDF no están rastreados.
- [ ] **Reproducibilidad:** los comandos del README funcionan desde cero (`make setup` → `make modulo1`).
- [ ] **Documentación:** README, informe o spec actualizados si cambió el comportamiento.
- [ ] **Cifras verificadas:** cualquier número del README o del informe sale de un archivo de resultados.

---

### 🧪 Evidencia de pruebas ejecutadas

<!--- Pega la salida real de los comandos o adjunta una captura de la app. -->

```bash
make test
```

```text
# Pega aquí la salida
```

#### Resultado de la demo (si aplica)

| Comando | Resultado |
|---------|-----------|
| `make modulo1` | |
| `make app` | |
| `make scraping-demo` | |
