"""MATRIZ DE ENRUTAMIENTO (Taller 2): ¿el agente elige la herramienta correcta? GASTA CUOTA de Gemini (una llamada de agente por pregunta, más 2 de preparación).

Lee docs/2 - Conjunto de prueba/matriz_enrutamiento.csv, hace cada pregunta en una conversación nueva (las de memoria llevan antes un turno de preparación)
y compara las herramientas usadas con las esperadas. Mide además tokens, costo y segundos por turno. Necesita GOOGLE_API_KEY con facturación y Ollama encendido.
Uso:  uv run python scripts/22_matriz_enrutamiento.py          (corre todo)
      uv run python scripts/22_matriz_enrutamiento.py --seco   (solo muestra el plan, no llama a Gemini)
      uv run python scripts/22_matriz_enrutamiento.py R01 R15  (solo esas)
Resultado: docs/2 - Conjunto de prueba/resultados/matriz_enrutamiento_resultados.csv
"""

import csv
import sys
import time
import unicodedata
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from taaml.agente import MODELO_AGENTE, conversar, costo_usd, crear_agente, olvidar_cliente, uso_del_turno  # noqa: E402

CARPETA = ROOT / "docs" / "2 - Conjunto de prueba"
MATRIZ = CARPETA / "matriz_enrutamiento.csv"
SALIDA = CARPETA / "resultados" / "matriz_enrutamiento_resultados.csv"
PREPARACION = {  # turno previo que sustituye al «contexto_previo» escrito en la matriz
    "R18": "¿Qué sedes hay en Ibagué?",
    "R19": "Mi nombre es Ana y vivo en Cali.",
}
ALTERNAS = {
    "R09": {"buscar_en_base"}
}  # un enlace de pago puede estar en las tablas o en el texto: cualquiera de las dos vale
TEXTO_ESPERADO = {
    "R19": ["Ana", "Cali"],
    "R20": ["No tengo esa información"],
    "R21": ["604 326 66 00"],
    "R22": ["No tengo esa información"],
    "R26": ["6"],
    "R27": ["8"],
    "R28": ["15"],
}
CAMPOS = [
    "id",
    "categoria",
    "herramienta_esperada",
    "herramientas_usadas",
    "n_llamadas",
    "enrutamiento_ok",
    "parametros_ok",
    "texto_ok",
    "tokens_entrada",
    "tokens_salida",
    "costo_usd",
    "segundos",
    "respuesta",
]


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def enrutamiento_ok(id_: str, esperada: str, usadas: set[str]) -> bool:
    if usadas == ALTERNAS.get(id_):
        return True
    if esperada == "ninguna":
        return not usadas
    if esperada == "ninguna_o_consultar_datos":
        return usadas <= {"consultar_datos"}
    if esperada == "ambas":
        return usadas >= {"consultar_datos", "buscar_en_base"}
    return esperada in usadas  # herramienta extra (p. ej. buscar tras «Sin resultados») no se penaliza


def parametros_ok(esperados: str, llamadas: list[dict]) -> bool | None:
    """Revisa tabla y ciudad en alguna llamada a consultar_datos. None si la matriz no pide parámetros."""
    pedidos = dict(
        p.strip().split("=", 1)
        for p in esperados.replace(" + ", ";").split(";")
        if p.strip().startswith(("tabla=", "ciudad=", "tipo="))
    )
    if not pedidos:
        return None
    for ll in llamadas:
        if ll["herramienta"] == "consultar_datos" and all(
            sin_tildes(v.strip()) in sin_tildes(str(ll["args"].get(k, ""))) for k, v in pedidos.items()
        ):
            return True
    return False


def main() -> None:
    args = sys.argv[1:]
    seco = "--seco" in args
    filtro = {a for a in args if a != "--seco"}
    filas = [
        f for f in csv.DictReader(MATRIZ.open(encoding="utf-8-sig", newline="")) if not filtro or f["id"] in filtro
    ]
    if seco:
        for f in filas:
            previo = f" (antes: «{PREPARACION[f['id']]}»)" if f["id"] in PREPARACION else ""
            print(f"{f['id']} [{f['categoria']}] espera {f['herramienta_esperada']}: {f['pregunta']}{previo}")
        print(
            f"\n{len(filas)} preguntas, {sum(f['id'] in PREPARACION for f in filas)} turnos de preparación. No se llamó a Gemini."
        )
        return
    agente, resultados, total = crear_agente(), [], 0.0
    for f in filas:
        hilo, costo, entrada, salida = uuid4().hex, 0.0, 0, 0
        try:
            if f["id"] in PREPARACION:
                conversar(PREPARACION[f["id"]], hilo, agente=agente, usuario=hilo)
                e0, s0 = uso_del_turno(agente, hilo)
                costo += costo_usd(e0, s0, MODELO_AGENTE) or 0.0
            inicio = time.perf_counter()
            respuesta, llamadas = conversar(
                f["pregunta"], hilo, agente=agente, usuario=hilo
            )  # un cliente por pregunta: su memoria de largo plazo no se mezcla con la de otra
            segundos = time.perf_counter() - inicio
            entrada, salida = uso_del_turno(agente, hilo)  # tokens acumulados de este turno (el último mensaje humano)
            costo += costo_usd(entrada, salida, MODELO_AGENTE) or 0.0
        except Exception as e:  # una falla no debe tirar las demás ni perder lo ya pagado
            print(f"{f['id']}: ERROR {type(e).__name__}: {e}")
            resultados.append(
                {
                    "id": f["id"],
                    "categoria": f["categoria"],
                    "herramienta_esperada": f["herramienta_esperada"],
                    "respuesta": f"ERROR {type(e).__name__}",
                }
            )
            continue
        olvidar_cliente(hilo)  # no deja datos de prueba en el Store
        usadas = {ll["herramienta"] for ll in llamadas}
        ok_ruta = enrutamiento_ok(f["id"], f["herramienta_esperada"], usadas)
        ok_params = parametros_ok(f["parametros_esperados"], llamadas)
        ok_texto = all(t in respuesta for t in TEXTO_ESPERADO.get(f["id"], [])) if f["id"] in TEXTO_ESPERADO else None
        total += costo
        resultados.append(
            {
                "id": f["id"],
                "categoria": f["categoria"],
                "herramienta_esperada": f["herramienta_esperada"],
                "herramientas_usadas": "+".join(sorted(usadas)) or "ninguna",
                "n_llamadas": len(llamadas),
                "enrutamiento_ok": ok_ruta,
                "parametros_ok": ok_params,
                "texto_ok": ok_texto,
                "tokens_entrada": entrada,
                "tokens_salida": salida,
                "costo_usd": f"{costo:.5f}",
                "segundos": f"{segundos:.1f}",
                "respuesta": respuesta,
            }
        )
        print(
            f"{f['id']} [{f['categoria']}] esperada {f['herramienta_esperada']} | usó {'+'.join(sorted(usadas)) or 'ninguna'} ({len(llamadas)} llamadas) | ruta {'OK' if ok_ruta else 'NO'} | "
            f"params {ok_params} | texto {ok_texto} | {entrada}/{salida} tokens | ${costo:.5f} | {segundos:.1f} s"
        )
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    if filtro and SALIDA.exists():  # una corrida parcial no borra lo ya medido: reemplaza solo esas filas
        previos = {
            r["id"]: r
            for r in csv.DictReader(SALIDA.open(encoding="utf-8-sig", newline=""))
            if r["id"] not in {x["id"] for x in resultados}
        }
        resultados = sorted([*previos.values(), *resultados], key=lambda r: r["id"])
    with SALIDA.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS, quoting=csv.QUOTE_ALL, extrasaction="ignore")
        w.writeheader()
        w.writerows(resultados)
    buenas = sum(str(r.get("enrutamiento_ok")) == "True" for r in resultados)
    print(
        f"\nEnrutamiento correcto: {buenas} de {len(resultados)}  |  costo total: ${total:.5f} USD  |  guardado en {SALIDA}"
    )


if __name__ == "__main__":
    main()
