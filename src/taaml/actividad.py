"""Registro de lo que hace el agente, para el panel en vivo de la demostración.

Cada turno deja una fila: cuándo, por qué canal llegó, quién (solo un trozo del hash del teléfono, nunca el número), qué escribió
(mensaje entrante), qué se le respondió (respuesta saliente) y con qué fuentes, qué herramientas usó, cuánto tardó y cómo terminó.

Los canales se muestran como `web` (asistente web) o `whatsapp`. Cada conversación se identifica por `conversacion` =
`canal:quien`, separando canal, día y usuario sin guardar el teléfono. `fecha` (AAAA-MM-DD) + `hora` (HH:MM:SS) ordena
cronológicamente.

**Persistencia:** además de la copia en memoria (`MAXIMO` filas), cada fila se guarda en SQLite (`ACTIVIDAD_DB`, por defecto
`data/memoria/actividad.sqlite`). No se borra nada al reiniciar FastAPI: al arrancar, `cargar()` repuebla la memoria desde la base.
No se usa la base de memoria de `taaml.agente` ni HITL. SQLite es local; no hay credenciales en los mensajes.
"""

import hashlib
import json
import os
import sqlite3
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

MAXIMO = 200
MAX_TEXTO = 140  # lo que se ve del mensaje en pantalla
MAX_RESPUESTA = 1500  # lo que se guarda de la respuesta del asistente
MAX_FUENTES = 6
MAX_EXTRACTO = 300
ESTADOS = ("respondido", "pendiente de aprobación", "límite", "no soportado", "error", "aprobación", "voz")

CAMPOS = (
    "n", "hora", "fecha", "canal", "quien", "conversacion", "mensaje", "respuesta", "estado",
    "herramientas", "segundos", "nota", "costo", "fuentes",
)

_FILAS: deque[dict[str, Any]] = deque(maxlen=MAXIMO)
_USADAS: set[str] = set()  # herramientas distintas usadas desde que arrancó el servidor, aunque sus filas ya hayan salido
_CERROJO = threading.RLock()
_SIGUIENTE = 1


def quien(telefono: str) -> str:
    """Un identificador corto y estable para ver quién escribe sin mostrar el número."""
    digitos = "".join(c for c in telefono if c.isdigit()) or telefono
    return hashlib.sha256(f"panel:{digitos}".encode()).hexdigest()[:6]


def _ruta_db() -> Path:
    """Ruta del SQLite de actividad. `ACTIVIDAD_DB` lo cambia (las pruebas usan uno temporal); nunca `.env`."""
    crudo = os.environ.get("ACTIVIDAD_DB") or str(Path(__file__).resolve().parents[2] / "data" / "memoria" / "actividad.sqlite")
    ruta = Path(crudo)
    if ruta.parent != Path(""):
        ruta.parent.mkdir(parents=True, exist_ok=True)
    return ruta


def _conectar() -> sqlite3.Connection:
    con = sqlite3.connect(str(_ruta_db()), check_same_thread=False)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS actividad (
            n INTEGER PRIMARY KEY,
            hora TEXT NOT NULL,
            fecha TEXT NOT NULL,
            canal TEXT NOT NULL,
            quien TEXT NOT NULL,
            conversacion TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            respuesta TEXT NOT NULL,
            estado TEXT NOT NULL,
            herramientas TEXT NOT NULL,
            segundos REAL,
            nota INTEGER NOT NULL,
            costo REAL,
            fuentes TEXT NOT NULL,
            turno_id TEXT
        )
        """
    )
    columnas = {fila[1] for fila in con.execute("PRAGMA table_info(actividad)").fetchall()}
    if columnas and "turno_id" not in columnas:
        con.execute("ALTER TABLE actividad ADD COLUMN turno_id TEXT")
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_actividad_turno_id ON actividad(turno_id) WHERE turno_id IS NOT NULL")
    return con


def _persistir(fila: dict[str, Any]) -> None:
    """Guarda la fila en SQLite. Un fallo de disco no puede tumbar el turno del agente."""
    try:
        con = _conectar()
        try:
            con.execute(
                """INSERT OR REPLACE INTO actividad
                (n, hora, fecha, canal, quien, conversacion, mensaje, respuesta, estado, herramientas, segundos, nota, costo, fuentes, turno_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    fila["n"], fila["hora"], fila["fecha"], fila["canal"], fila["quien"], fila["conversacion"],
                    fila["mensaje"], fila["respuesta"], fila["estado"], json.dumps(fila["herramientas"], ensure_ascii=False),
                    fila["segundos"], 1 if fila["nota"] else 0, fila["costo"], json.dumps(fila["fuentes"], ensure_ascii=False),
                    fila.get("turno_id"),
                ),
            )
            con.commit()
        finally:
            con.close()
    except (OSError, sqlite3.Error):
        pass


def _fila_desde_db(fila: sqlite3.Row) -> dict[str, Any]:
    return {
        "n": fila["n"], "hora": fila["hora"], "fecha": fila["fecha"], "canal": fila["canal"], "quien": fila["quien"],
        "conversacion": fila["conversacion"], "mensaje": fila["mensaje"], "respuesta": fila["respuesta"],
        "estado": fila["estado"], "herramientas": json.loads(fila["herramientas"] or "[]"),
        "segundos": fila["segundos"], "nota": bool(fila["nota"]), "costo": fila["costo"],
        "fuentes": json.loads(fila["fuentes"] or "[]"),
        "turno_id": fila["turno_id"],
    }


def cargar() -> None:
    """Repuebla la memoria desde SQLite (llamar al arrancar). No borra nada; restaura orden y numeración."""
    global _SIGUIENTE
    with _CERROJO:
        _FILAS.clear()
        _USADAS.clear()
        try:
            con = _conectar()
            con.row_factory = sqlite3.Row
            try:
                filas = con.execute("SELECT * FROM actividad ORDER BY n ASC").fetchall()
            finally:
                con.close()
        except (OSError, sqlite3.Error):
            filas = []
        for cruda in filas[-MAXIMO:]:
            fila = _fila_desde_db(cruda)
            _FILAS.append(fila)
            _USADAS.update(fila["herramientas"])
        _SIGUIENTE = (filas[-1]["n"] + 1) if filas else 1
        for cruda in filas[:-MAXIMO] or []:
            _USADAS.update(json.loads(cruda["herramientas"] or "[]"))


def registrar(
    canal: str,
    telefono: str,
    mensaje: str,
    estado: str,
    herramientas: list[str] | None = None,
    segundos: float | None = None,
    reloj=time.time,
    nota: bool = False,
    costo: float | None = None,
    respuesta: str = "",
    fuentes: list[dict] | None = None,
    turno_id: str | None = None,
) -> dict[str, Any]:
    """Agrega una fila (mensaje entrante + respuesta saliente) y la devuelve. `estado` es uno de ESTADOS (cómo terminó el turno).

    `nota` dice si la respuesta llevó la nota de «dato sin respaldo»; `costo` es lo que costó el turno en dólares (None si no se pudo
    calcular). De cada fuente se guardan documento, fragmento, enlace y extracto, sin repetir fragmentos. `quien` es un hash del
    teléfono, nunca el número; `conversacion` separa canal + día + usuario sin revelarlo.
    """
    global _SIGUIENTE
    unicas = list({(f.get("documento"), f.get("fragmento")): f for f in fuentes or []}.values())[:MAX_FUENTES]
    canal = canal or "chat"
    ahora = reloj()
    with _CERROJO:
        fila = {
            "n": _SIGUIENTE,
            "hora": time.strftime("%H:%M:%S", time.localtime(ahora)),
            "fecha": time.strftime("%Y-%m-%d", time.localtime(ahora)),
            "canal": canal,
            "quien": quien(telefono),
            "conversacion": "",  # se fija justo abajo con fecha + canal + usuario
            "mensaje": " ".join(mensaje.split())[:MAX_TEXTO],
            "estado": estado,
            "herramientas": list(herramientas or []),
            "segundos": None if segundos is None else round(segundos, 1),
            "nota": bool(nota),
            "costo": None if costo is None else round(costo, 5),
            "respuesta": respuesta.strip()[:MAX_RESPUESTA],
            "fuentes": [
                {
                    **{campo: str(f.get(campo, "")) for campo in ("documento", "fragmento", "fuente")},
                    "extracto": str(f.get("extracto", ""))[:MAX_EXTRACTO],
                }
                for f in unicas
            ],
            "turno_id": turno_id,
        }
        # Conversación por canal + día + usuario (quien ya es un hash, no el teléfono).
        fila["conversacion"] = f"{canal}:{fila['fecha']}:{fila['quien']}"
        _SIGUIENTE += 1
        _FILAS.append(fila)
        _USADAS.update(fila["herramientas"])
        _persistir(fila)
    return fila


def registrar_whatsapp_entrada(telefono: str, mensaje: str, turno_id: str | None = None) -> dict[str, Any]:
    """Registra una vez el mensaje entrante real; `message:received` y `message_received` pueden coincidir."""
    canal = "whatsapp"
    telefono = (telefono or "").strip()
    mensaje = " ".join((mensaje or "").split())[:MAX_TEXTO]
    turno_id = (turno_id or "").strip() or None
    with _CERROJO:
        if turno_id:
            for actual in _FILAS:
                if actual.get("turno_id") == turno_id and actual["canal"] == canal:
                    return actual
    return registrar(canal, telefono, mensaje, "respondido", respuesta="", turno_id=turno_id)


def registrar_whatsapp_respuesta(
    telefono: str,
    mensaje: str,
    respuesta: str,
    turno_id: str | None = None,
) -> dict[str, Any]:
    """Registra una conversación real de OpenClaw/WhatsApp sin depender de que el modelo llame a una herramienta."""
    canal = "whatsapp"
    telefono = (telefono or "").strip()
    mensaje = " ".join((mensaje or "").split())[:MAX_TEXTO]
    respuesta = (respuesta or "").strip()[:MAX_RESPUESTA]
    turno_id = (turno_id or "").strip() or None
    with _CERROJO:
        if turno_id:
            for i, actual in enumerate(_FILAS):
                if actual.get("turno_id") != turno_id:
                    continue
                if actual["canal"] == canal and actual["mensaje"] == mensaje and actual["respuesta"] == respuesta:
                    return actual
                actualizada = {**actual, "respuesta": respuesta, "estado": "respondido"}
                _FILAS[i] = actualizada
                _persistir(actualizada)
                return actualizada
    return registrar(
        canal,
        telefono,
        mensaje,
        "respondido",
        respuesta=respuesta,
        turno_id=turno_id,
    )


def herramientas_usadas() -> list[str]:
    """Las herramientas distintas que el agente ha usado desde que arrancó el servidor, en orden alfabético."""
    with _CERROJO:
        return sorted(_USADAS)


def recientes(desde: int = 0) -> list[dict[str, Any]]:
    """Las filas con número mayor que `desde`, de la más vieja a la más nueva."""
    with _CERROJO:
        return [f for f in _FILAS if f["n"] > desde]


def vaciar() -> None:
    """Borra el registro (para las pruebas y para empezar la demostración en limpio)."""
    global _SIGUIENTE
    with _CERROJO:
        _FILAS.clear()
        _USADAS.clear()
        _SIGUIENTE = 1
        try:
            con = _conectar()
            try:
                con.execute("DELETE FROM actividad")
                con.commit()
            finally:
                con.close()
        except (OSError, sqlite3.Error):
            pass
