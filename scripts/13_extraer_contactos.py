"""EXTRACCIÓN A JSONL: saca los datos de contacto de unas páginas del corpus a un JSONL validado.

Usa salida estructurada con Pydantic y temperature 0.0. Para cuidar que no invente, cada valor extraído se comprueba contra el
texto de la página: si no aparece escrito allí, queda marcado en `no_verificados`.
Cada página es una llamada al modelo (gasta cuota o saldo): por defecto son 3.
Uso:  uv run python scripts/13_extraer_contactos.py [--archivos a.md,b.md]
Resultado: data/5_extraccion/contactos.jsonl
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from langchain_core.messages import HumanMessage  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from taaml.prompts import leer_prompt  # noqa: E402
from taaml.tareas import MODELO_POR_DEFECTO, obtener_modelo  # noqa: E402

DOCUMENTOS = ROOT / "data" / "4_curaduria" / "documentos_incluidos.jsonl"
SALIDA = ROOT / "data" / "5_extraccion" / "contactos.jsonl"
PAGINAS_POR_DEFECTO = ["canales_atencion.md", "datos_complementarios.md", "es-internet-home-internet-contactenos-internet-celsia.md"]


class Contacto(BaseModel):
    tipo: Literal["telefono", "whatsapp", "correo", "enlace"]
    valor: str = Field(description="El valor tal como está escrito en el documento")
    para_que_sirve: str = Field(description="Para qué sirve, en pocas palabras, según el documento")


class FichaContactos(BaseModel):
    contactos: list[Contacto]


def normalizar(texto: str) -> str:
    """Compara sin espacios, guiones ni paréntesis: «01 8000 112 115» y «018000112115» son el mismo número."""
    return re.sub(r"[\s\-().]", "", texto).lower()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archivos", default=",".join(PAGINAS_POR_DEFECTO), help="archivos del corpus, separados por coma")
    ap.add_argument("--modelo", default=MODELO_POR_DEFECTO)
    a = ap.parse_args()

    corpus = {d["archivo"]: d for d in map(json.loads, DOCUMENTOS.read_text(encoding="utf-8").splitlines())}
    modelo = obtener_modelo(a.modelo).with_structured_output(FichaContactos)
    SALIDA.parent.mkdir(exist_ok=True)
    total = verificados = 0
    with SALIDA.open("w", encoding="utf-8") as salida:
        for nombre in a.archivos.split(","):
            doc = corpus[nombre.strip()]
            ficha = modelo.invoke([HumanMessage(leer_prompt("v1_extraccion.md").replace("{documento}", doc["text"]))],
                                  config={"run_name": "extraer_contactos", "tags": ["extraccion"]})
            texto = normalizar(doc["text"])
            no_verificados = [c.valor for c in ficha.contactos if normalizar(c.valor) not in texto]
            total, verificados = total + len(ficha.contactos), verificados + len(ficha.contactos) - len(no_verificados)
            salida.write(json.dumps({"archivo": nombre, "url": doc.get("url", ""), "contactos": [c.model_dump() for c in ficha.contactos],
                                     "no_verificados": no_verificados}, ensure_ascii=False) + "\n")
            print(f"{nombre}: {len(ficha.contactos)} contactos, {len(no_verificados)} sin verificar")
    print(f"{verificados} de {total} valores aparecen escritos en su página. Guardado en {SALIDA.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
