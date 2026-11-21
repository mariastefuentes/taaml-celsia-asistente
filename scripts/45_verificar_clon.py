"""VERIFICAR CLON LIMPIO: ¿lo que hay en GitHub arranca en una carpeta vacía? No gasta cuota del modelo; tarda unos minutos (instala todo).

  make verificar-clon                       # clona el repositorio de GitHub, instala y corre lint y pruebas allí
  make verificar-clon ARGS="--rapido"       # solo revisa el README contra el Makefile y el .env.example (sin clonar ni instalar)
  make verificar-clon ARGS="--local"        # clona este mismo repositorio local en vez de GitHub (para probar una rama sin subirla)

Qué revisa, en orden:
  1. Clona en una carpeta temporal (no usa nada de este computador: ni `.venv` ni `.env`).
  2. `uv sync --frozen --all-groups`, lo mismo que hace el CI de GitHub.
  3. `make lint` y `make test` dentro del clon.
  4. Cada `make <comando>` que cita el README existe como objetivo del Makefile.
  5. `.env` no está versionado y `.env.example` no trae valores que parezcan claves reales.
Es la comprobación que habría detectado el paquete que faltaba en el CI (D26).
"""

import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = "https://github.com/mariastefuentes/taaml-celsia-asistente.git"
CLAVE_REAL = re.compile(r"(sk-[A-Za-z0-9]{16,}|EAA[A-Za-z0-9]{40,}|AIza[0-9A-Za-z_-]{30,}|ghp_[A-Za-z0-9]{30,})")


def objetivos_del_makefile(makefile: str) -> set[str]:
    """Los nombres de objetivo que define el Makefile («nombre:» al inicio de línea, sin ser una variable)."""
    return {m.group(1) for m in re.finditer(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)\s*:(?!=)", makefile, re.M)}


def comandos_make_del_readme(readme: str) -> set[str]:
    """Los `make <objetivo>` que el README manda escribir (dentro de bloques de código o de comillas invertidas)."""
    bloques = re.findall(r"```.*?```|`[^`\n]+`", readme, re.S)
    return {m.group(1) for b in bloques for m in re.finditer(r"\bmake\s+([a-z][a-z0-9-]*)", b)}


def readme_sin_objetivo(readme: str, makefile: str) -> list[str]:
    """Comandos `make` que cita el README y el Makefile no define."""
    return sorted(comandos_make_del_readme(readme) - objetivos_del_makefile(makefile))


def claves_en_env_example(texto: str) -> list[str]:
    """Líneas de `.env.example` con un valor que parece una clave real (el ejemplo debe ir vacío o con texto de relleno)."""
    return [l.split("=")[0] for l in texto.splitlines() if "=" in l and not l.lstrip().startswith("#") and CLAVE_REAL.search(l)]


def correr(orden: list[str], carpeta: Path, entorno: dict | None = None) -> tuple[bool, str]:
    r = subprocess.run(orden, cwd=carpeta, env={**os.environ, **(entorno or {})}, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode == 0, (r.stdout + r.stderr)[-600:]


def _borrar(funcion, ruta, _):  # en Windows los archivos de .git son de solo lectura
    os.chmod(ruta, stat.S_IWRITE)
    funcion(ruta)


def revisiones_de_texto(carpeta: Path) -> list[tuple[str, bool, str]]:
    readme = (carpeta / "README.md").read_text(encoding="utf-8")
    makefile = (carpeta / "Makefile").read_text(encoding="utf-8")
    faltan = readme_sin_objetivo(readme, makefile)
    ejemplo = carpeta / ".env.example"
    claves = claves_en_env_example(ejemplo.read_text(encoding="utf-8")) if ejemplo.exists() else ["(no existe .env.example)"]
    versionado = subprocess.run(["git", "ls-files", ".env"], cwd=carpeta, capture_output=True, text=True).stdout.strip()
    return [
        ("El README solo cita comandos `make` que existen", not faltan, ", ".join(faltan)),
        (".env.example no trae claves reales", not claves, ", ".join(claves)),
        (".env no está versionado", not versionado, versionado),
    ]


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    resultados: list[tuple[str, bool, str]] = []
    if "--rapido" in args:
        resultados += revisiones_de_texto(ROOT)
    else:
        if not shutil.which("make") or not shutil.which("uv") or not shutil.which("git"):
            sys.exit("Hacen falta git, uv y make en el PATH.")
        origen = str(ROOT) if "--local" in args else URL
        base = Path(tempfile.mkdtemp(prefix="clon_"))
        clon = base / "repo"
        try:
            print(f"Clonando {origen} en {clon} ...")
            ok, salida = correr(["git", "clone", "--depth", "1", origen, str(clon)], base)
            resultados.append(("Clona el repositorio", ok, "" if ok else salida))
            if ok:
                entorno = {"UV_LINK_MODE": "copy"}  # evita el error de enlaces duros de Windows/OneDrive
                for nombre, orden in [
                    ("Instala todo (`uv sync --frozen --all-groups`)", ["uv", "sync", "--frozen", "--all-groups"]),
                    ("`make lint` pasa", ["make", "lint"]),
                    ("`make test` pasa", ["make", "test"]),
                ]:
                    print(f"{nombre} ...")
                    ok, salida = correr(orden, clon, entorno)
                    resultados.append((nombre, ok, "" if ok else salida))
                    if not ok and "Instala" in nombre:
                        break  # sin dependencias no tiene sentido seguir
                resultados += revisiones_de_texto(clon)
        finally:
            shutil.rmtree(base, onerror=_borrar)
    print("\n===== VERIFICACIÓN DEL CLON =====")
    for nombre, ok, detalle in resultados:
        print(f"[{'ok' if ok else 'FALLA'}] {nombre}" + (f"\n        {detalle}" if detalle and not ok else ""))
    sys.exit(0 if all(ok for _, ok, _ in resultados) else 1)


if __name__ == "__main__":
    main()
