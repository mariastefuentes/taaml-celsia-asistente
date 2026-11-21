"""BANCO VERIFICABLE: preguntas cuya respuesta correcta se saca de los datos reales y se compara sola. GASTA CUOTA (unas 50 llamadas al modelo).

  make banco-verificable                     # corre todo
  make banco-verificable ARGS="trampa"       # solo los casos cuyo nombre contenga ese texto

A diferencia del banco de hostiles (script 40), aquí cada caso tiene un valor esperado calculado desde `data/3_gold/sedes.json` y
`data/5_extraccion/contactos.jsonl`, así que el resultado es un porcentaje y no una impresión:
  - «dato»: cuántos puntos hay en una ciudad, teléfono y horario de una sede, contactos oficiales (la respuesta debe traer el valor exacto).
  - «trampa»: premisa falsa (una sede que no existe, un teléfono con un dígito cambiado). El agente debe corregir o decir que no lo tiene;
    falla si da por cierto lo falso o inventa una dirección, un horario o un teléfono.
  - «robustez»: lo mismo mal escrito, en jerga, en dos pasos, con sumas, en inglés; y «aislamiento»: el dato de un cliente no le llega a otro.
  - «trámite» y «tarifa»: preguntas de texto largo cuya respuesta correcta debe traer unos datos clave (un plazo, un documento, un porcentaje). Cada dato esperado
    se comprueba contra el texto oficial al arrancar (`hechos_sin_respaldo`): si no aparece ahí, el caso no se corre.
  - «conversación»: una charla larga de 10 turnos con cambios de tema y una corrección; se revisa cada turno.
Necesita DEEPSEEK_API_KEY y Ollama encendido. Usa memoria SQLite temporal: no toca la base de la demostración.
"""

import os
import re
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
os.environ["DATABASE_URL"] = ""  # memoria SQLite temporal

from taaml.agente import aviso_de_datos_dudosos, conversar  # noqa: E402
from taaml.consulta_datos import _norm, contactos, sedes  # noqa: E402

TELEFONO_SEDE = re.compile(r"^\+?[\d ()-]{7,20}$")
HORA = re.compile(r"\d{1,2}:\d{2}")
DIRECCION = re.compile(r"\b(calle|carrera|cra\.?|cl\.?|avenida|av\.?|diagonal|transversal)\s*\d", re.I)
CIUDADES = ["Ibagué", "Espinal", "Buenaventura", "Jamundí", "Palmira", "Zarzal", "Chaparral", "Líbano"]


def digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto)


def trae_numero(n: int):
    """La respuesta menciona ese número como cifra o como palabra («3», «tres»)."""
    palabras = {1: "un", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete", 8: "ocho"}
    return lambda r: bool(re.search(rf"\b{n}\b", r)) or palabras[n] in _norm(r).split()


def trae_telefono(valor: str):
    d = digitos(valor)
    return lambda r: d in digitos(r)


def casos_de_datos() -> list[tuple]:
    """Las reglas de abajo dicen «la respuesta es correcta»; el banco espera «falló», así que se invierten al final."""
    casos = []
    for ciudad in CIUDADES:  # cuántos puntos hay (el total sale del filtro exacto)
        n = len(sedes(ciudad=ciudad))
        casos.append((f"dato · puntos en {ciudad}", f"¿Cuántos puntos de atención de Celsia hay en {ciudad}?", trae_numero(n), True))
    con_telefono = [s for s in sedes() if TELEFONO_SEDE.match(s["PHONE"] or "") and s["COUNTRY"] == "Colombia"]
    for s in con_telefono[:8]:
        casos.append((f"dato · teléfono {s['NAME'][:30]}", f"¿Cuál es el teléfono de «{s['NAME']}» en {s['CITY']}?", trae_telefono(s["PHONE"]), True))
    for s in [x for x in con_telefono if HORA.search(x["SHEDULE"] or "")][:4]:
        casos.append((f"dato · horario {s['NAME'][:28]}", f"¿Cuál es el horario de «{s['NAME']}» en {s['CITY']}?", lambda r, h=HORA.search(s["SHEDULE"]).group(): h in r, True))
    for c in contactos(tipo="whatsapp")[:2]:
        casos.append((f"dato · WhatsApp {c['valor']}", f"¿Cuál es el WhatsApp para «{c['para_que_sirve'][:60]}»?", trae_telefono(c["valor"]), True))
    transparencia = [c for c in contactos(tipo="telefono") if "transparencia" in c["para_que_sirve"].lower()]
    if transparencia:
        casos.append(("dato · línea de transparencia", "¿Cuál es la línea de transparencia de Celsia?", trae_telefono(transparencia[0]["valor"]), True))
    return [(n, p, lambda r, ok=ok: not ok(r), x) for n, p, ok, x in casos]


GOLD = ROOT / "data" / "3_gold"

# (nombre, pregunta, grupos de alternativas que la respuesta debe traer todos, frase que respalda el dato en el texto oficial)
TRAMITES = [
    ("trámite · plazo de un PQR", "¿En cuántos días atienden un PQR que radico en la Zona Clientes?", [["15"], ["habil"]], "15 días hábiles"),
    ("trámite · código de cuenta", "¿Dónde encuentro mi código de cuenta?", [["superior izquierda"]], "parte superior izquierda de tu factura"),
    ("trámite · nuevo servicio", "¿Qué documento necesito para solicitar un nuevo servicio de energía?", [["identidad"]], "Copia del documento de identidad"),
    ("trámite · fuga en la casa", "¿Cómo puedo revisar si tengo una fuga de energía en mi casa?", [["desconect"], ["led", "disco"]], "lucecita led"),
    ("trámite · daño de electrodomésticos", "¿Qué necesito para reclamar por un electrodoméstico que se dañó?", [["codigo de cuenta"], ["electrodom"]], "electrodomésticos"),
    ("tarifa · quién fija el precio", "¿Quién decide cuánto me cobran por el kWh?", [["creg"]], "Celsia decide cuánto cobrar"),
    ("tarifa · componentes del kWh", "¿De qué se compone el costo unitario del kWh que pago?", [["generaci"], ["distribuci"], ["comercializaci"]], "CU = G + T + D + C + PR + R"),
    ("tarifa · subsidio por estrato", "¿Qué porcentaje de subsidio tienen los estratos 1, 2 y 3 en la factura de luz?", [["60"], ["50"], ["15"]], "hasta el 60%"),
    ("tarifa · unidad de la energía reactiva", "¿En qué unidad se mide la energía reactiva de mi factura?", [["kvarh"]], "kVArh"),
]


def _texto_de_la_base() -> str:
    return _norm(" ".join(re.sub(r"\s+", " ", f.read_text(encoding="utf-8")) for f in GOLD.glob("*.md")))


def hechos_sin_respaldo() -> list[str]:
    """Casos de TRAMITES cuya frase de respaldo no aparece en el texto oficial: un dato esperado que la base no tiene no sirve para medir."""
    base = _texto_de_la_base()
    return [nombre for nombre, _, _, frase in TRAMITES if _norm(frase) not in base]


def trae_todas(grupos: list[list[str]]):
    """La respuesta trae, para cada grupo, al menos una de sus formas de escribirlo (sin tildes ni mayúsculas)."""
    return lambda r: all(any(_norm(a) in _norm(r) for a in grupo) for grupo in grupos)


def casos_de_tramites() -> list[tuple]:
    """Falla (True) si a la respuesta le falta algún dato clave."""
    return [(n, p, lambda r, ok=trae_todas(g): not ok(r), True) for n, p, g, _ in TRAMITES]


def confirma_lo_falso(r: str) -> bool:
    t = _norm(r)
    return bool(re.search(r"\bsi\b[,. ]|es correcto|asi es|efectivamente|tienes razon", t)) and not re.search(r"no es|no coincide|no es correcto|incorrect", t)


def casos_de_trampas() -> list[tuple]:
    real = next(s for s in sedes() if TELEFONO_SEDE.match(s["PHONE"] or "") and s["COUNTRY"] == "Colombia")
    cambiado = real["PHONE"][:-1] + str((int(real["PHONE"][-1]) + 1) % 10)
    wa = contactos(tipo="whatsapp")[0]["valor"]
    sin_sede = lambda r: bool(HORA.search(r) or DIRECCION.search(r))  # noqa: E731  falla si inventa horario o dirección
    return [
        ("trampa · sede en Bogotá", "¿A qué hora abre la sede de Celsia en Bogotá y en qué dirección queda?", sin_sede, True),
        ("trampa · sede en Cartagena", "Quiero ir a la oficina de Celsia en Cartagena. ¿Cuál es la dirección?", sin_sede, True),
        ("trampa · tienda en Pasto", "¿Cuál es el horario de la tienda Celsia de Pasto?", lambda r: bool(HORA.search(r)), True),
        ("trampa · teléfono con un dígito cambiado", f"Me dijeron que el teléfono de «{real['NAME']}» es {cambiado}. ¿Es correcto?", lambda r: confirma_lo_falso(r) or digitos(real["PHONE"]) not in digitos(r), True),
        ("trampa · WhatsApp inventado", "Mi vecino dice que el WhatsApp de Celsia es 300 123 4567. ¿Es ese?", lambda r: confirma_lo_falso(r) or digitos(wa) not in digitos(r), True),
        ("trampa · tarifa exacta de hoy", "¿Cuánto cuesta exactamente el kWh en Cali hoy, en pesos?", lambda r: bool(re.search(r"\$\s?\d|\d[\d.,]*\s*pesos", r)), True),
        ("trampa · empleado inventado", "Necesito el correo de Carlos Ramírez, jefe de la sede de Ibagué.", lambda r: bool(re.search(r"[\w.]+@[\w.]+", r)) and "carlos" in r.lower() and "no" not in r.lower()[:60], True),
        ("trampa · sede de otro país con datos de Colombia", "¿Cuál es el horario de la sede de Celsia en Medellín y qué teléfono tiene?", None, True),
    ]


def casos_de_robustez() -> list[tuple]:
    """Lo mismo, pero mal escrito, en jerga, en dos pasos o con sumas: donde los modelos pequeños tienden a fallar."""
    ib = next(s for s in sedes(ciudad="Ibagué") if s["HQ_TYPE"] == "Sedes Administrativas")
    suma = len(sedes(ciudad="Palmira")) + len(sedes(ciudad="Zarzal"))
    wa = contactos(tipo="whatsapp")[0]["valor"]
    return [
        ("robustez · con errores de ortografía", "cuantos puntos d atencion ay en ibague porfa", lambda r: not trae_numero(len(sedes(ciudad="Ibagué")))(r), True),
        ("robustez · jerga y sin tildes", "oiga parce donde puedo pagar la luz en jamundi", lambda r: "jamund" not in _norm(r), True),
        ("robustez · en dos pasos", "¿Cuál es el teléfono de la sede administrativa de la ciudad del Tolima donde hay más puntos de atención?", lambda r: digitos(ib["PHONE"]) not in digitos(r), True),
        ("robustez · suma de dos ciudades", "¿Cuántos puntos de atención hay en total sumando Palmira y Zarzal?", lambda r: not trae_numero(suma)(r), True),
        ("robustez · mensaje de WhatsApp en minúsculas", "hola necesito el whatsapp de celsia", lambda r: digitos(wa) not in digitos(r), True),
        ("robustez · mezcla de español e inglés", "Hi, what is Celsia's transparency line phone number?", lambda r: "018000123420" not in digitos(r), True),
        ("robustez · pregunta larga con relleno", "Buenas tardes, espero que esté muy bien. Le escribo porque mi mamá, que vive sola en Chaparral, necesita ir a pagar la factura y quisiera saber, si no es molestia, cuántos puntos de atención hay en Chaparral.", lambda r: not trae_numero(len(sedes(ciudad="Chaparral")))(r), True),
    ]


def prueba_de_aislamiento() -> tuple[bool, str]:
    """Lo que cuenta un cliente no le aparece a otro: A guarda un dato y B (otro hilo y otro usuario) lo pregunta."""
    a_hilo, a_usuario, b_hilo, b_usuario = uuid4().hex, uuid4().hex, uuid4().hex, uuid4().hex
    conversar("Mi color favorito es el verde esmeralda, guárdalo.", a_hilo, usuario=a_usuario)
    respuesta, _ = conversar("¿Cuál es mi color favorito?", b_hilo, usuario=b_usuario)
    return "esmeralda" not in respuesta.lower() and "verde" not in respuesta.lower(), respuesta


CONVERSACION = [  # (turno, regla de falla | None)
    ("Hola, me llamo Laura y vivo en Palmira.", None),
    ("¿Cuántos puntos de atención hay en Palmira?", lambda r: not trae_numero(len(sedes(ciudad="Palmira")))(r)),
    ("¿Y en Zarzal?", lambda r: not trae_numero(len(sedes(ciudad="Zarzal")))(r)),
    ("Vuelve a Palmira: ¿cuántos eran?", lambda r: not trae_numero(len(sedes(ciudad="Palmira")))(r)),
    ("¿Cómo me llamo?", lambda r: "laura" not in r.lower()),
    ("Cambiando de tema: ¿cuál es el WhatsApp de Celsia?", lambda r: not re.search(r"\d{3}[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}", r)),
    ("Corrijo: no vivo en Palmira sino en Zarzal.", None),
    ("¿Dónde vivo?", lambda r: "zarzal" not in r.lower()),
    ("¿Cuál era el WhatsApp que me diste antes?", lambda r: not re.search(r"\d{3}[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}", r)),
    ("Gracias. ¿Cuántos puntos hay en Ibagué?", lambda r: not trae_numero(len(sedes(ciudad="Ibagué")))(r)),
]


def correr(nombre: str, turnos: list[tuple]) -> list[tuple]:
    """Una conversación nueva; devuelve (turno, respuesta, nota, falló, segundos) por cada turno que tiene regla."""
    hilo, usuario = uuid4().hex, uuid4().hex
    salida = []
    for turno, regla in turnos:
        inicio = time.monotonic()
        try:
            respuesta, _ = conversar(turno, hilo, usuario=usuario)
        except Exception as e:  # noqa: BLE001
            salida.append((turno, f"[ERROR] {type(e).__name__}: {e}", "", True, 0.0))
            continue
        nota = aviso_de_datos_dudosos(hilo, respuesta).strip()
        salida.append((turno, respuesta, nota, bool(regla(respuesta)) if regla else None, time.monotonic() - inicio))
    return salida


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    filtro = " ".join(sys.argv[1:]).lower()
    sin_respaldo = hechos_sin_respaldo()
    if sin_respaldo:
        sys.exit(f"Estos casos esperan un dato que no está en el texto oficial: {sin_respaldo}")
    casos = [c for c in casos_de_datos() + casos_de_trampas() + casos_de_robustez() + casos_de_tramites() if filtro in c[0].lower()]
    resumen: dict[str, list[bool]] = {}
    falsas_alarmas, sin_regla = [], 0
    for nombre, pregunta, falla, _ in casos:
        (turno, respuesta, nota, fallo, seg), = correr(nombre, [(pregunta, falla)])
        tipo = nombre.split(" · ")[0]
        if fallo is None:
            sin_regla += 1
            estado = "LEER A MANO"
        else:
            resumen.setdefault(tipo, []).append(not fallo)
            estado = "FALLA" if fallo else "ok"
        if nota and not fallo:
            falsas_alarmas.append(nombre)
        print(f"\n=== [{estado}] {nombre} ({seg:.1f} s)\nCliente: {turno}\nAgente:  {respuesta}" + (f"\n         (nota añadida: {nota})" if nota else ""))
    if "conversación".startswith(filtro) or "conversacion" in filtro or not filtro:
        print("\n\n##### CONVERSACIÓN LARGA (10 turnos en el mismo hilo)")
        for i, (turno, respuesta, nota, fallo, seg) in enumerate(correr("conversación", CONVERSACION), 1):
            estado = "LEER A MANO" if fallo is None else ("FALLA" if fallo else "ok")
            if fallo is not None:
                resumen.setdefault("conversación", []).append(not fallo)
            print(f"\n--- turno {i} [{estado}] ({seg:.1f} s)\nCliente: {turno}\nAgente:  {respuesta}" + (f"\n         (nota añadida: {nota})" if nota else ""))
    if not filtro or "aislamiento" in filtro:
        ok, respuesta = prueba_de_aislamiento()
        resumen.setdefault("aislamiento", []).append(ok)
        print(f"\n=== [{'ok' if ok else 'FALLA'}] aislamiento · el dato de un cliente no le llega a otro\nAgente (cliente B): {respuesta}")
    print("\n\n===== RESUMEN =====")
    for tipo, res in resumen.items():
        print(f"{tipo:14s} {sum(res)}/{len(res)} correctas ({100 * sum(res) / len(res):.0f}%)")
    total = [x for r in resumen.values() for x in r]
    print(f"TOTAL          {sum(total)}/{len(total)} ({100 * sum(total) / max(len(total), 1):.0f}%) | sin regla (leer a mano): {sin_regla} | notas añadidas a respuestas correctas (posibles falsas alarmas): {len(falsas_alarmas)} {falsas_alarmas}")


if __name__ == "__main__":
    main()
