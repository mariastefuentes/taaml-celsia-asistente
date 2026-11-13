"""EVALUACIÓN EN LANGSMITH (Taller 2): la matriz de enrutamiento como dataset y dos configuraciones del agente comparables en la misma pantalla.
GASTA CUOTA de Gemini (una llamada de agente por pregunta, 25 preguntas por configuración, más 2 de preparación) y necesita una clave de LangSmith
con permiso para crear datasets (LANGSMITH_API_KEY en el .env; la de «solo trazas» da 403).

Qué hace:
1. Sube docs/2 - Conjunto de prueba/matriz_enrutamiento.csv como el dataset «celsia-matriz-enrutamiento» (una vez; si ya existe, lo reutiliza).
2. Corre el agente sobre cada ejemplo con `Client.evaluate` y puntúa tres cosas: `ruta_ok` (herramienta esperada), `detalle_ok` (parámetros y texto esperados) y `n_llamadas`.
3. Cada configuración queda como un experimento del dataset. En smith.langchain.com → Datasets → celsia-matriz-enrutamiento → Experiments se marcan dos y se pulsa Compare.

Configuraciones: «con_tope» (el agente entregado: 4 herramientas por pregunta como máximo) y «sin_tope» (el mismo agente sin ese límite).
LangSmith aquí solo observa y puntúa: el agente se orquesta con `create_agent`.
Uso:  uv run python scripts/24_evaluar_en_langsmith.py --seco                 (solo muestra el plan, no llama a nada)
      uv run python scripts/24_evaluar_en_langsmith.py                       (con_tope y sin_tope: 50 preguntas, unos 0,36 USD)
      uv run python scripts/24_evaluar_en_langsmith.py --config con_tope     (una sola configuración: unos 0,18 USD)
"""

import csv
import importlib.util
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location("matriz_enrutamiento", ROOT / "scripts" / "22_matriz_enrutamiento.py")
matriz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(
    matriz
)  # reutiliza las reglas de puntuación de la matriz: lo que se mide aquí es lo mismo que allá

NOMBRE_DATASET = "celsia-matriz-enrutamiento"
CONFIGURACIONES = {"con_tope": 4, "sin_tope": 1000}  # herramientas máximas por pregunta


def cargar_ejemplos() -> list[dict]:
    filas = csv.DictReader(matriz.MATRIZ.open(encoding="utf-8-sig", newline=""))
    return [
        {
            "inputs": {"id": f["id"], "pregunta": f["pregunta"], "previo": matriz.PREPARACION.get(f["id"], "")},
            "outputs": {
                "herramienta_esperada": f["herramienta_esperada"],
                "parametros_esperados": f["parametros_esperados"],
                "categoria": f["categoria"],
            },
        }
        for f in filas
    ]


def ruta_ok(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """1 si el agente usó la herramienta que la matriz esperaba."""
    usadas = {ll["herramienta"] for ll in outputs["llamadas"]}
    return {
        "key": "ruta_ok",
        "score": int(matriz.enrutamiento_ok(inputs["id"], reference_outputs["herramienta_esperada"], usadas)),
    }


def detalle_ok(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """1 si, de los parámetros y textos que la matriz exige para esa pregunta, se cumplen todos (las preguntas que no exigen nada puntúan 1)."""
    params = matriz.parametros_ok(reference_outputs["parametros_esperados"], outputs["llamadas"])
    esperado = matriz.TEXTO_ESPERADO.get(inputs["id"])
    texto = all(t in outputs["respuesta"] for t in esperado) if esperado else None
    return {"key": "detalle_ok", "score": int(params is not False and texto is not False)}


def n_llamadas(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """Cuántas herramientas pidió el agente para esa pregunta (menos es mejor, siempre que la ruta sea correcta)."""
    return {"key": "n_llamadas", "score": len(outputs["llamadas"])}


def fabricar_objetivo(tope: int):
    """La función que LangSmith ejecuta por cada ejemplo: una conversación nueva, con un agente cuyo tope de herramientas es `tope`."""
    from taaml import agente as modulo

    modulo.MAX_LLAMADAS_POR_TURNO = tope  # crear_agente lo lee al construir el agente
    agente = modulo.crear_agente()

    def objetivo(inputs: dict) -> dict:
        hilo = uuid4().hex
        if inputs["previo"]:
            modulo.conversar(inputs["previo"], hilo, agente=agente, usuario=hilo)
        respuesta, llamadas = modulo.conversar(inputs["pregunta"], hilo, agente=agente, usuario=hilo)
        modulo.olvidar_cliente(hilo)
        return {"respuesta": respuesta, "llamadas": llamadas}

    return objetivo


def subir_dataset(cliente, ejemplos: list[dict]) -> None:
    if cliente.has_dataset(dataset_name=NOMBRE_DATASET):
        print(f"El dataset «{NOMBRE_DATASET}» ya existe: se reutiliza.")
        return
    cliente.create_dataset(
        NOMBRE_DATASET,
        description="Matriz de enrutamiento del agente de Celsia: pregunta, herramienta esperada y parámetros (R01 a R25).",
    )
    cliente.create_examples(dataset_name=NOMBRE_DATASET, examples=ejemplos)
    print(f"Dataset «{NOMBRE_DATASET}» creado con {len(ejemplos)} ejemplos.")


def main() -> None:
    args = sys.argv[1:]
    elegidas = [a for a in args if a in CONFIGURACIONES] or list(CONFIGURACIONES)
    if "--config" in args:
        elegidas = [args[args.index("--config") + 1]]
    ejemplos = cargar_ejemplos()
    if "--seco" in args:
        print(f"Dataset «{NOMBRE_DATASET}»: {len(ejemplos)} ejemplos.")
        for c in elegidas:
            print(
                f"  experimento «agente-{c}»: tope de {CONFIGURACIONES[c]} herramientas por pregunta, {len(ejemplos)} preguntas"
            )
        print("No se llamó a LangSmith ni a Gemini.")
        return
    from langsmith import Client

    cliente = Client()
    subir_dataset(cliente, ejemplos)
    for c in elegidas:
        print(f"\n== Configuración {c} (tope {CONFIGURACIONES[c]}) ==")
        resultado = cliente.evaluate(
            fabricar_objetivo(CONFIGURACIONES[c]),
            data=NOMBRE_DATASET,
            evaluators=[ruta_ok, detalle_ok, n_llamadas],
            experiment_prefix=f"agente-{c}",
            metadata={"configuracion": c, "tope_herramientas": CONFIGURACIONES[c]},
            max_concurrency=1,
        )
        print(f"Experimento: {resultado.experiment_name}")
    print(
        "\nPara compararlos: smith.langchain.com → Datasets → celsia-matriz-enrutamiento → Experiments → marcar los dos → Compare."
    )


if __name__ == "__main__":
    main()
