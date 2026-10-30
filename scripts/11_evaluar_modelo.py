"""Evalua un modelo con el conjunto de prueba.

Para cada pregunta de `2 - Conjunto de prueba/conjunto_de_prueba.csv` le pasa al modelo el prompt de sistema
(src/taaml/prompts.py) con la base de conocimiento como contexto, guarda su respuesta, y un modelo «juez» la califica
contra la respuesta esperada. Deja un CSV por corrida en `2 - Conjunto de prueba/resultados/`.

Modelos:  gemini:<id>   (API de Google; sirve tambien para Gemma)      ollama:<nombre>   (local)
Base:     completa (toda la curaduria)  |  compacta (primeros N caracteres de cada documento, para modelos locales)

Ejemplos:
    uv run python scripts/11_evaluar_modelo.py --modelo gemini:gemini-3.8-flash --solo P01,P02,N01
    uv run python scripts/11_evaluar_modelo.py --modelo gemini:gemma-4-31b-it
    uv run python scripts/11_evaluar_modelo.py --modelo ollama:llama3.2 --base compacta
    uv run python scripts/11_evaluar_modelo.py --resumen
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from taaml.base import cargar_base  # noqa: E402
from taaml.recuperacion import buscar, formatear_contexto  # noqa: E402
from taaml.reordenar import buscar_reordenado, modelo_reordenador  # noqa: E402
from taaml.prompts import PARAMETROS_MODELO, VERSION_VIGENTE, construir_mensaje_usuario, construir_prompt_sistema  # noqa: E402

load_dotenv(ROOT / ".env")
PRUEBA = ROOT / "docs" / "2 - Conjunto de prueba"
RESULTADOS = PRUEBA / "resultados"
GEMINI = "https://generativelanguage.googleapis.com/v1beta/models"
OLLAMA = "http://localhost:11434/api/chat"
DEEPSEEK = "https://api.deepseek.com/chat/completions"
JUEZ_POR_DEFECTO = "gemini-3.8-flash"  # distinto del modelo que responde (3.5); el juez no responde a clientes, así que no aplica la regla de top_p
CALIFICACIONES = ["correcta", "parcial", "incorrecta", "reconoce_no_sabe", "inventa"]

# El prompt del juez no se cambia (ni se le añaden etiquetas): sus datos no son entrada de un cliente y así las corridas siguen siendo comparables.
JUEZ_PROMPT = """Eres un evaluador estricto de un asistente de atención al cliente.
Fecha de hoy: {hoy}. La base de conocimiento tiene noticias y datos de 2026: no los trates como futuros ni como inventados.
Tipo de pregunta: {tipo}
PREGUNTA: {pregunta}
RESPUESTA ESPERADA (lo que debería decir, o qué debe hacer): {esperada}
RESPUESTA DEL ASISTENTE: {respuesta}

Califica con UNA de estas etiquetas:
- correcta: dice lo esencial de la respuesta esperada y no agrega datos falsos.
- parcial: acierta pero omite algo importante.
- incorrecta: da un dato equivocado o no responde lo preguntado.
- reconoce_no_sabe: (solo si el tipo es «negativa») dice que no tiene la información y remite a un canal, sin inventar.
- inventa: (solo si el tipo es «negativa») da un dato, cifra, plazo o precio concreto que no debería saber.
Si el tipo es «respuesta» usa solo correcta, parcial o incorrecta. Si es «negativa» usa solo reconoce_no_sabe o inventa.
Responde SOLO un JSON: {{"calificacion": "<etiqueta>", "motivo": "<una frase>"}}"""


def http_json(url: str, cuerpo: dict, cabeceras: dict, intentos: int = 5, timeout: int = 600) -> dict:
    """POST con reintentos ante límites de uso (429) y fallas temporales (500/503)."""
    for n in range(intentos):
        req = urllib.request.Request(url, data=json.dumps(cuerpo).encode("utf-8"), headers={"Content-Type": "application/json", **cabeceras})
        try:
            return json.load(urllib.request.urlopen(req, timeout=timeout))
        except urllib.error.HTTPError as e:
            texto = e.read().decode("utf-8", "replace")
            if e.code in (429, 500, 503) and n < intentos - 1:
                espera = 20 * (2 ** n)
                m = re.search(r"retry in ([\d\.]+)s", texto)
                if m:
                    espera = max(espera, float(m.group(1)) + 2)
                print(f"    (HTTP {e.code}; espero {espera:.0f} s)", flush=True)
                time.sleep(espera)
                continue
            raise RuntimeError(f"HTTP {e.code}: {texto[:300]}") from None
    raise RuntimeError("sin respuesta tras reintentos")


def llamar_gemini(modelo: str, sistema: str, pregunta: str, json_salida: bool = False) -> tuple[str, int, int]:
    clave = os.environ["GOOGLE_API_KEY"]
    cfg = {"temperature": PARAMETROS_MODELO["temperature"], "topP": PARAMETROS_MODELO["top_p"], "maxOutputTokens": 2048}
    if json_salida:
        cfg["responseMimeType"] = "application/json"
    cuerpo = {"systemInstruction": {"parts": [{"text": sistema}]}, "contents": [{"role": "user", "parts": [{"text": pregunta}]}], "generationConfig": cfg}
    url = f"{GEMINI}/{modelo}:generateContent"
    try:
        r = http_json(url, cuerpo, {"x-goog-api-key": clave})
    except RuntimeError as e:
        if "instruction" in str(e).lower():  # algunos modelos (p. ej. Gemma) no aceptan instrucción de sistema
            cuerpo.pop("systemInstruction")
            cuerpo["contents"][0]["parts"][0]["text"] = sistema + "\n\nPREGUNTA DEL CLIENTE:\n" + pregunta
            r = http_json(url, cuerpo, {"x-goog-api-key": clave})
        else:
            raise
    partes = (r.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
    texto = "".join(p.get("text", "") for p in partes if not p.get("thought")).strip()
    uso = r.get("usageMetadata", {})
    return texto, uso.get("promptTokenCount", 0), uso.get("candidatesTokenCount", 0)


def llamar_deepseek(modelo: str, sistema: str, pregunta: str, json_salida: bool = False) -> tuple[str, int, int]:
    """DeepSeek (formato OpenAI). Se apaga el modo de razonamiento; su ficha dice que top_p queda fijo en 1.0 y no garantiza temperature."""
    cuerpo = {"model": modelo, "temperature": PARAMETROS_MODELO["temperature"], "top_p": PARAMETROS_MODELO["top_p"], "max_tokens": 2048,
              "thinking": {"type": "disabled"},
              "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": pregunta}]}
    if json_salida:
        cuerpo["response_format"] = {"type": "json_object"}
    r = http_json(DEEPSEEK, cuerpo, {"Authorization": "Bearer " + os.environ["DEEPSEEK_API_KEY"]})
    uso = r.get("usage", {})
    return r["choices"][0]["message"]["content"].strip(), uso.get("prompt_tokens", 0), uso.get("completion_tokens", 0)


def llamar_ollama(modelo: str, sistema: str, pregunta: str, num_ctx: int) -> tuple[str, int, int]:
    cuerpo = {"model": modelo, "stream": False, "keep_alive": "30m",
              "options": {"temperature": PARAMETROS_MODELO["temperature"], "top_p": PARAMETROS_MODELO["top_p"], "num_ctx": num_ctx, "num_predict": 600},
              "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": pregunta}]}
    r = http_json(OLLAMA, cuerpo, {}, timeout=3600)
    return r["message"]["content"].strip(), r.get("prompt_eval_count", 0), r.get("eval_count", 0)


def juzgar(juez: str, p: dict, respuesta: str) -> tuple[str, str]:
    prompt = JUEZ_PROMPT.format(hoy=date.today().isoformat(), tipo=p["tipo_prueba"], pregunta=p["pregunta"], esperada=p["respuesta_esperada"] +
                                (f" (debe remitir a: {p['debe_remitir_a']})" if p["debe_remitir_a"] else ""), respuesta=respuesta or "(sin respuesta)")
    try:
        proveedor, _, nombre = juez.rpartition(":")  # «deepseek:<id>»; sin prefijo es un modelo de Gemini
        llamar = llamar_deepseek if proveedor == "deepseek" else llamar_gemini
        texto, _, _ = llamar(nombre, "Eres un evaluador. Respondes solo JSON.", prompt, json_salida=True)
        j = json.loads(re.search(r"\{.*\}", texto, re.S).group(0))
        cal = j.get("calificacion", "").strip()
        return (cal if cal in CALIFICACIONES else "sin_calificar"), j.get("motivo", "")
    except Exception as e:  # noqa: BLE001
        return "sin_calificar", f"error del juez: {e}"[:200]


def resumir() -> None:
    filas = []
    for f in sorted(RESULTADOS.glob("resultados_*.csv")):
        filas += list(csv.DictReader(f.open(encoding="utf-8-sig", newline="")))
    corridas: dict[tuple, list] = {}
    for r in filas:
        corridas.setdefault((r["modelo"], r["base"], r.get("prompt") or "v1"), []).append(r)
    md = ["# Comparación de modelos con el conjunto de prueba", "",
          "Generado automáticamente por `scripts/11_evaluar_modelo.py --resumen`. Cada fila es una corrida; la calificación la da un modelo juez "
          "comparando con la respuesta esperada, así que es una **ayuda para revisar**, no un veredicto: conviene que una persona revise las respuestas.", "",
          "| Modelo | Base | Prompt | Preguntas | Correctas | Parciales | Incorrectas | Reconoce que no sabe | Inventa | Sin calificar | Tiempo mediano (s) | Tokens de entrada (media) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for (modelo, base, prompt), rs in sorted(corridas.items()):
        c = lambda k: sum(r["calificacion"] == k for r in rs)  # noqa: E731
        # solo respuestas sin error; mediana (no media) porque las esperas por el límite de uso de la API inflan algunos tiempos
        t = sorted(float(r["segundos"]) for r in rs if r["segundos"] and not r["error"])
        ti = [int(r["tokens_entrada"]) for r in rs if r["tokens_entrada"] and not r["error"]]
        mediana = (t[len(t) // 2] if len(t) % 2 else (t[len(t) // 2 - 1] + t[len(t) // 2]) / 2) if t else 0
        md.append(f"| {modelo} | {base} | {prompt} | {len(rs)} | {c('correcta')} | {c('parcial')} | {c('incorrecta')} | {c('reconoce_no_sabe')} | {c('inventa')} | "
                  f"{c('sin_calificar')} | {mediana:.0f} | {sum(ti) // len(ti) if ti else 0:,} |")
    md += ["", "«Correctas», «parciales» e «incorrectas» se cuentan sobre las preguntas de respuesta; «reconoce que no sabe» e «inventa», sobre las negativas. "
               "«Sin calificar» incluye las preguntas que fallaron por errores de conexión o por el límite de uso de la API (se pueden repetir). "
               "El tiempo es la **mediana** de las respuestas sin error: en las corridas por API todavía puede incluir esperas por el límite de uso.", ""]
    (PRUEBA / "comparacion_modelos.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


def recalificar(juez: str, pausa: float, solo: str = "") -> None:
    """Vuelve a calificar las respuestas ya guardadas con el juez actual, sin llamar al modelo que responde."""
    preguntas = {p["id"]: p for p in csv.DictReader((PRUEBA / "conjunto_de_prueba.csv").open(encoding="utf-8-sig", newline=""))}
    for archivo in sorted(RESULTADOS.glob("resultados_*.csv")):
        filas = list(csv.DictReader(archivo.open(encoding="utf-8-sig", newline="")))
        campos = list(filas[0].keys()) + [c for c in ("juez", "fecha") if c not in filas[0]]  # quién calificó y cuándo
        print(archivo.name, flush=True)
        for r in filas:
            if r["error"] or r["id"] not in preguntas or (solo and r["id"] not in solo.split(",")):
                continue
            antes = r["calificacion"]
            r["calificacion"], r["motivo_juez"] = juzgar(juez, preguntas[r["id"]], r["respuesta"])
            r["juez"], r["fecha"] = juez, date.today().isoformat()
            print(f"  {r['id']}: {antes} -> {r['calificacion']}", flush=True)
            time.sleep(pausa)
            with archivo.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=campos, quoting=csv.QUOTE_ALL); w.writeheader(); w.writerows(filas)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", help="gemini:<id>, deepseek:<id> u ollama:<nombre>")
    ap.add_argument("--base", choices=["rag", "completa", "compacta"], default="rag", help="rag: fragmentos relevantes por pregunta")
    ap.add_argument("--max-por-doc", type=int, default=600, help="caracteres por documento en la base compacta")
    ap.add_argument("--num-ctx", type=int, default=24576, help="ventana de contexto para Ollama")
    ap.add_argument("--prompt", default=VERSION_VIGENTE, help="version del prompt del asistente en prompts/ (por defecto la vigente)")
    ap.add_argument("--reordenar", action="store_true", help="rag con reordenamiento: una llamada más por pregunta (src/taaml/reordenar.py)")
    ap.add_argument("--repetir", action="store_true", help="repite el mensaje del usuario dos veces (prueba de repetición del prompt)")
    ap.add_argument("--solo", default="", help="ids separados por coma (ej. P01,N02)")
    ap.add_argument("--pausa", type=float, default=3.0, help="segundos entre preguntas")
    ap.add_argument("--juez", default=JUEZ_POR_DEFECTO, help="modelo juez: <id de Gemini> o deepseek:<id>")
    ap.add_argument("--sin-juez", action="store_true")
    ap.add_argument("--resumen", action="store_true", help="solo regenera la comparación de todas las corridas")
    ap.add_argument("--recalificar", action="store_true", help="vuelve a juzgar las respuestas ya guardadas (no llama al modelo que responde)")
    a = ap.parse_args()
    if a.resumen:
        return resumir()
    if a.recalificar:
        return recalificar(a.juez, a.pausa, a.solo)
    if not a.modelo:
        ap.error("falta --modelo")

    preguntas = list(csv.DictReader((PRUEBA / "conjunto_de_prueba.csv").open(encoding="utf-8-sig", newline="")))
    if a.solo:
        pedidas = {x.strip() for x in a.solo.split(",")}
        preguntas = [p for p in preguntas if p["id"] in pedidas]
    contexto = "" if a.base == "rag" else cargar_base(a.base, a.max_por_doc)
    sistema = construir_prompt_sistema(contexto, a.prompt)
    proveedor, _, nombre = a.modelo.partition(":")
    tamano = "fragmentos relevantes por pregunta" if a.base == "rag" else f"{len(contexto):,} caracteres, ~{len(contexto) // 4:,} tokens"
    print(f"Modelo {a.modelo} | base {a.base} ({tamano}) | {len(preguntas)} preguntas", flush=True)

    RESULTADOS.mkdir(exist_ok=True)
    etiqueta_base = a.base + ("-reordenado" if a.reordenar and a.base == "rag" else "") + ("-repetido" if a.repetir else "")  # estas corridas van aparte
    destino = RESULTADOS / f"resultados_{re.sub(r'[^A-Za-z0-9._-]+', '-', a.modelo)}_{etiqueta_base}{'' if a.prompt == 'v1' else '_' + a.prompt}.csv"
    campos = ["modelo", "base", "prompt", "id", "tipo_prueba", "pregunta", "respuesta", "calificacion", "motivo_juez", "segundos", "tokens_entrada", "tokens_salida", "fragmentos", "error", "juez", "fecha"]
    previas = {}
    if destino.exists():  # reanudable: no repite lo ya contestado sin error
        previas = {r["id"]: r for r in csv.DictReader(destino.open(encoding="utf-8-sig", newline="")) if not r["error"]}
    filas = []
    for p in preguntas:
        if p["id"] in previas:
            filas.append(previas[p["id"]]); print(f"  {p['id']}: ya estaba", flush=True); continue
        t0, err, texto, ti, to, ids_fragmentos = time.time(), "", "", 0, 0, ""
        mensaje = construir_mensaje_usuario(p["pregunta"], a.prompt)
        if a.repetir:  # Leviathan et al.: <CONSULTA><CONSULTA>
            mensaje = f"{mensaje}\n\n{mensaje}"
        try:
            sistema_p = sistema
            if a.base == "rag":  # cada pregunta lleva sus propios fragmentos
                recuperados = buscar_reordenado(p["pregunta"], modelo=modelo_reordenador(nombre)) if a.reordenar else buscar(p["pregunta"])
                ids_fragmentos = " ".join(r["chunk_id"] for r in recuperados)
                sistema_p = construir_prompt_sistema(formatear_contexto(recuperados), a.prompt)
            if proveedor == "gemini":
                texto, ti, to = llamar_gemini(nombre, sistema_p, mensaje)
            elif proveedor == "deepseek":
                texto, ti, to = llamar_deepseek(nombre, sistema_p, mensaje)
            else:
                texto, ti, to = llamar_ollama(nombre, sistema_p, mensaje, a.num_ctx)
        except Exception as e:  # noqa: BLE001
            err = str(e)[:300]
        seg = time.time() - t0
        cal, motivo = ("sin_calificar", "") if (a.sin_juez or err) else juzgar(a.juez, p, texto)
        filas.append({"modelo": a.modelo, "base": etiqueta_base, "prompt": a.prompt, "id": p["id"], "tipo_prueba": p["tipo_prueba"], "pregunta": p["pregunta"], "respuesta": texto,
                      "calificacion": cal, "motivo_juez": motivo, "segundos": f"{seg:.1f}", "tokens_entrada": ti, "tokens_salida": to, "fragmentos": ids_fragmentos, "error": err,
                      "juez": "" if (a.sin_juez or err) else a.juez, "fecha": date.today().isoformat()})
        print(f"  {p['id']}: {cal if not err else 'ERROR ' + err[:80]} ({seg:.0f} s)", flush=True)
        with destino.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=campos, quoting=csv.QUOTE_ALL); w.writeheader(); w.writerows(filas)
        time.sleep(a.pausa)
    with destino.open("w", encoding="utf-8-sig", newline="") as f:  # guarda también las preguntas que ya estaban hechas y quedaron al final
        w = csv.DictWriter(f, fieldnames=campos, quoting=csv.QUOTE_ALL); w.writeheader(); w.writerows(filas)
    print("Guardado en", destino)


if __name__ == "__main__":
    main()
