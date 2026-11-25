"""BORRADOR DEL INFORME FINAL: arma el esqueleto con lo que ya está en el repo, para que el equipo escriba encima en vez de empezar de cero.

  make informe-borrador      # escribe docs/3 - Informe/borrador_informe_final.md (no se sube a Git: se regenera cuando haga falta)

Es gratis: no llama a modelos ni a la red. Saca del repo lo que se puede sacar sin juicio humano (decisiones D1..Dn con su título, scripts con
su primera línea, especificaciones, diagramas, número de pruebas, resultados guardados) y deja marcado con «COMPLETAR» lo que solo el equipo
puede escribir (resumen, resultados de la demostración real, autoría, conclusiones). Nada de lo que escribe es una cifra inventada: si una cifra
no se puede leer del repo, queda como «COMPLETAR».
"""

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SALIDA = ROOT / "docs" / "3 - Informe" / "borrador_informe_final.md"


def decisiones() -> list[str]:
    texto = (ROOT / "docs" / "decisiones.md").read_text(encoding="utf-8")
    return [f"- **{m.group(1)}.** {m.group(2).strip()}" for m in re.finditer(r"^## (D\d+)\. (.+)$", texto, re.M)]


def scripts() -> list[str]:
    filas = []
    for ruta in sorted((ROOT / "scripts").glob("[0-9][0-9]_*.py")):
        doc = re.search(r'"""(.+?)(?:\n|""")', ruta.read_text(encoding="utf-8"), re.S)
        resumen = doc.group(1).strip().rstrip(".") if doc else "(sin descripción)"
        filas.append(f"| `{ruta.name}` | {resumen[:140]} |")
    return filas


def especificaciones() -> list[str]:
    return [f"- `{d.name}`" for d in sorted((ROOT / "specs").iterdir()) if d.is_dir()]


def diagramas() -> list[str]:
    return [f"![{p.stem}](../capturas/{p.name})" for p in sorted((ROOT / "docs" / "capturas").glob("*.png"))]


def numero_de_pruebas() -> str:
    try:
        salida = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, capture_output=True, text=True, timeout=120).stdout
        coincidencia = re.search(r"(\d+) tests? collected", salida)
        if coincidencia:
            return coincidencia.group(1)
        por_archivo = re.findall(r"^tests/\S+: (\d+)$", salida, re.M)  # la configuración del proyecto imprime un conteo por archivo
        return str(sum(map(int, por_archivo))) if por_archivo else "COMPLETAR"
    except Exception:  # noqa: BLE001
        return "COMPLETAR"


def resultados_guardados() -> list[str]:
    carpeta = ROOT / "docs" / "2 - Conjunto de prueba" / "resultados"
    return [f"- `{p.name}`" for p in sorted(carpeta.glob("*.csv"))] if carpeta.exists() else []


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    partes = [
        f"# Informe técnico final: agente de Celsia por WhatsApp (borrador generado el {date.today().isoformat()})",
        "> Borrador armado por `make informe-borrador`. Lo marcado **COMPLETAR** lo escribe el equipo; lo demás sale del repositorio y hay que revisarlo, no copiarlo sin leer.",
        "**Autores:** COMPLETAR (María Stella Fuentes Díaz, Juan José Mosquera, Nicolás Bolaños, Jensen Tamayo: confirmar quién firma y en qué orden). **Grupo 4.**",
        "## Resumen\nCOMPLETAR en 150 palabras: problema (clientes que no encuentran respuesta con fuente), qué se construyó (agente con memoria, 5 herramientas, aprobación humana, WhatsApp), cómo se midió y qué resultó. Tomar las cifras de `docs/3 - Informe/informe_taller2.md`, sección 5.",
        "## 1. Problema y objetivo\nBase: `docs/3 - Informe/informe_taller1.md` y `informe_taller2.md` (sección 1). COMPLETAR con un párrafo propio.",
        "## 2. Arquitectura\n" + "\n".join(diagramas()) + "\n\nTexto base: `informe_taller2.md`, sección 2. Ojo: los SVG de esa carpeta son los antiguos; los diagramas vigentes son los PNG de arriba (fuente JSON en `docs/`).",
        "## 3. Decisiones de diseño\nCada una está explicada con contexto, alternativas, decisión y evidencia en `docs/decisiones.md`:\n" + "\n".join(decisiones()),
        f"## 4. Pruebas y resultados\n- Pruebas automáticas: **{numero_de_pruebas()}** (`make test`, gratis).\n- Resultados guardados (conjunto de prueba, ataques, inyección indirecta):\n" + ("\n".join(resultados_guardados()) or "  COMPLETAR"),
        "Tablas con cifras: `informe_taller2.md`, secciones 5.1 a 5.6. **COMPLETAR** aquí solo lo que cambió después de ese informe (por ejemplo, el ensayo con celulares reales).",
        "## 5. Demostración por WhatsApp\n- Guion y plan B: `docs/guion_demo_whatsapp.md`.\n- Resultado del ensayo con Meta real: **COMPLETAR** (a la fecha no se ha probado con Meta; no afirmar lo contrario).\n- Chats reales: `make exportar-chats`; indicar cuántos fueron (mínimo recomendado 30) y que son de compañeros, no de clientes de Celsia.",
        "## 6. Limitaciones\nBase: `informe_taller2.md` sección 7 y los «Límites» de cada decisión. COMPLETAR con lo que se descubra en los ensayos.",
        "## 7. Conclusiones\nCOMPLETAR.",
        "## Anexo A. Especificaciones\n" + "\n".join(especificaciones()),
        "## Anexo B. Scripts\n| Script | Qué hace |\n|---|---|\n" + "\n".join(scripts()),
        "## Anexo C. Declaración de uso de IA\nTexto vigente: `docs/3 - Informe/informe_final.md`, Anexo C.",
    ]
    SALIDA.write_text("\n\n".join(partes) + "\n", encoding="utf-8")
    print(f"Listo: {SALIDA} ({SALIDA.stat().st_size // 1024} KB). Busca «COMPLETAR» para ver lo que falta.")


if __name__ == "__main__":
    main()
