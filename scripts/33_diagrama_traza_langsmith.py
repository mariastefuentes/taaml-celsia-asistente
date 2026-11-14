"""DIAGRAMA DE UNA TRAZA REAL DE LANGSMITH (informe, criterio 4.1): lo dibuja a partir de la traza, no a mano. No llama a ningún modelo ni gasta cuota.

Lee del proyecto de LangSmith (solo lectura) la ejecución `agente_celsia` más reciente cuya pregunta contiene el texto pedido, recorre sus pasos
(las llamadas al modelo y a las herramientas, con su inicio y fin reales) y escribe un diagrama de tiempos en SVG con los argumentos de cada herramienta,
los tokens y el identificador de la traza, para que cualquiera la encuentre en smith.langchain.com. Necesita LANGSMITH_API_KEY en .env.
Uso:  uv run python scripts/33_diagrama_traza_langsmith.py                      (la última de «proyectos solares»)
      uv run python scripts/33_diagrama_traza_langsmith.py --pregunta "Ibagué"  (la última cuya pregunta contenga ese texto)
Resultado: docs/3 - Informe/diagrama_traza_langsmith.svg
"""

import json
import os
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

SALIDA = ROOT / "docs" / "3 - Informe" / "diagrama_traza_langsmith.svg"
COLORES = {"llm": "#2563eb", "tool": "#d9650f"}
ETIQUETA = {"llm": "Modelo (Gemini)", "tool": "Herramienta"}


def pregunta_de(run) -> str:
    mensajes = (run.inputs or {}).get("messages") or []
    for m in reversed(mensajes):
        if isinstance(m, dict) and m.get("role", m.get("type")) in ("user", "human"):
            return str(m.get("content", ""))
    return ""


def buscar_traza(cliente, proyecto: str, texto: str):
    for r in cliente.list_runs(project_name=proyecto, is_root=True, limit=100):
        if r.name == "agente_celsia" and r.end_time and texto.lower() in pregunta_de(r).lower():
            return r
    raise SystemExit(f"No hay una traza reciente cuya pregunta contenga «{texto}» en el proyecto {proyecto}.")


def pasos_de(cliente, proyecto: str, raiz) -> list[dict]:
    """Las llamadas al modelo y a herramientas de la traza, en orden de inicio."""
    hijos = [
        h
        for h in cliente.list_runs(project_name=proyecto, trace_id=raiz.trace_id)
        if h.run_type in ("llm", "tool") and h.end_time
    ]
    pasos = []
    for h in sorted(hijos, key=lambda h: h.start_time):
        inicio = (h.start_time - raiz.start_time).total_seconds()
        pasos.append(
            {
                "tipo": h.run_type,
                "nombre": h.name,
                "inicio": inicio,
                "fin": (h.end_time - raiz.start_time).total_seconds(),
                "tokens": h.total_tokens or 0,
                "args": {k: v for k, v in (h.inputs or {}).items() if h.run_type == "tool" and v not in (None, "")},
            }
        )
    return pasos


def dibujar(raiz, pasos: list[dict]) -> str:
    total = (raiz.end_time - raiz.start_time).total_seconds()
    ancho, x0, x1, alto_fila, y0 = 980, 250, 940, 52, 118
    escala = (x1 - x0) / total
    alto = y0 + alto_fila * len(pasos) + 56
    pregunta = pregunta_de(raiz)
    pregunta = pregunta if len(pregunta) <= 100 else pregunta[:97] + "…"
    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" font-family="Segoe UI, Arial, sans-serif" role="img" aria-label="Traza de LangSmith de una pregunta al agente">',
        f'<rect width="{ancho}" height="{alto}" fill="#ffffff"/>',
        '<text x="24" y="34" font-size="20" font-weight="700" fill="#1f2937">Traza real de LangSmith: agente_celsia</text>',
        f'<text x="24" y="58" font-size="13" fill="#4b5563">«{escape(pregunta)}»</text>',
        f'<text x="24" y="80" font-size="12" fill="#6b7280">Proyecto taaml-celsia · traza {raiz.trace_id} · total {total:.1f} s · {raiz.total_tokens or 0:,} tokens · generada por scripts/33_diagrama_traza_langsmith.py</text>',
    ]
    for t in range(0, int(total) + 1, 2 if total > 8 else 1):  # marcas de tiempo cada 1 o 2 segundos
        x = x0 + t * escala
        s.append(f'<line x1="{x:.1f}" y1="{y0 - 14}" x2="{x:.1f}" y2="{alto - 40}" stroke="#e5e7eb"/>')
        s.append(f'<text x="{x:.1f}" y="{y0 - 20}" font-size="11" fill="#6b7280" text-anchor="middle">{t} s</text>')
    for i, p in enumerate(pasos):
        y = y0 + i * alto_fila
        x = x0 + p["inicio"] * escala
        w = max((p["fin"] - p["inicio"]) * escala, 2)
        args = ", ".join(f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in p["args"].items())
        corto = f"{p['fin'] - p['inicio']:.2f} s" + ("" if p["tipo"] == "tool" else f" · {p['tokens']:,} tokens")
        s.append(f'<text x="24" y="{y + 16}" font-size="13" font-weight="600" fill="#1f2937">{i + 1}. {ETIQUETA[p["tipo"]]}</text>')
        s.append(f'<text x="24" y="{y + 33}" font-size="11" fill="#6b7280">{escape(p["nombre"] if p["tipo"] == "tool" else "ChatGoogleGenerativeAI")}</text>')
        s.append(f'<rect x="{x:.1f}" y="{y + 4}" width="{w:.1f}" height="22" rx="5" fill="{COLORES[p["tipo"]]}"/>')
        if x + w + 6 + 6.4 * len(corto) < ancho - 12:  # el tiempo va a la derecha de la barra; si no cabe, a su izquierda
            s.append(f'<text x="{x + w + 6:.1f}" y="{y + 20}" font-size="12" fill="#1f2937">{corto}</text>')
        else:
            s.append(f'<text x="{x - 6:.1f}" y="{y + 20}" font-size="12" fill="#1f2937" text-anchor="end">{corto}</text>')
        if args:  # los argumentos de la herramienta, debajo de su barra
            texto = args if len(args) <= 95 else args[:92] + "…"
            ancla = ("start", x) if x + 6.2 * len(texto) < ancho - 12 else ("end", min(x + w, ancho - 12))
            s.append(f'<text x="{ancla[1]:.1f}" y="{y + 40}" font-size="11" fill="#9a3f08" text-anchor="{ancla[0]}">{escape(texto)}</text>')
    s.append(f'<text x="24" y="{alto - 16}" font-size="11" fill="#6b7280">Azul: el modelo decide o redacta. Naranja: la herramienta que eligió. Tiempos medidos por LangSmith, no estimados.</text>')
    s.append("</svg>")
    return "\n".join(s)


def main() -> None:
    from langsmith import Client

    if not os.getenv("LANGSMITH_API_KEY"):
        raise SystemExit("Falta LANGSMITH_API_KEY en .env.")
    texto = "proyectos solares"
    if "--pregunta" in sys.argv:
        texto = sys.argv[sys.argv.index("--pregunta") + 1]
    proyecto = os.getenv("LANGSMITH_PROJECT", "taaml-celsia")
    cliente = Client()
    raiz = buscar_traza(cliente, proyecto, texto)
    pasos = pasos_de(cliente, proyecto, raiz)
    SALIDA.write_text(dibujar(raiz, pasos), encoding="utf-8")
    print(f"Traza {raiz.trace_id}: {len(pasos)} pasos, {(raiz.end_time - raiz.start_time).total_seconds():.1f} s. Guardado en {SALIDA}")


if __name__ == "__main__":
    main()
