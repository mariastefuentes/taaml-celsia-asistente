"""Notas de voz de WhatsApp a texto (TENTATIVO: apagado por defecto y sin probar con audios reales de Meta).

Se activa con `VOZ_ACTIVA=1` y necesita `faster-whisper` instalado a mano (`uv pip install faster-whisper`; no está en `pyproject.toml`
a propósito: baja un modelo de cientos de MB y no queremos meter ese peso en el entorno de todos). El audio se transcribe en este
mismo equipo, sin enviarlo a ningún servicio externo. Si algo falta o falla, `transcribir` devuelve None y el bot responde que por
ahora solo lee texto, como antes.

  VOZ_ACTIVA   "1" para atender notas de voz (por defecto apagado)
  VOZ_MODELO   tamaño del modelo de Whisper (por defecto "base": rápido y suficiente para frases cortas)
"""

import logging
import os
import tempfile
from pathlib import Path

log = logging.getLogger("taaml.voz")
MAX_BYTES = 2_000_000  # unos minutos de audio de WhatsApp: más que eso no es una pregunta
_MODELO = None


def activa() -> bool:
    return os.environ.get("VOZ_ACTIVA") == "1"


def _modelo():
    global _MODELO
    if _MODELO is None:
        from faster_whisper import WhisperModel  # noqa: PLC0415  (opcional: solo se importa si la voz está activa)

        _MODELO = WhisperModel(os.environ.get("VOZ_MODELO", "base"), device="cpu", compute_type="int8")
    return _MODELO


def transcribir(audio: bytes, mime: str = "audio/ogg") -> str | None:
    """El texto del audio, o None si la voz está apagada, falta la biblioteca, el audio es demasiado grande o la transcripción falla."""
    if not activa() or not audio or len(audio) > MAX_BYTES:
        return None
    sufijo = ".ogg" if "ogg" in mime else ".mp3" if "mpeg" in mime else ".m4a"
    try:
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / f"nota{sufijo}"
            ruta.write_bytes(audio)
            segmentos, _ = _modelo().transcribe(str(ruta), language="es")
            texto = " ".join(s.text.strip() for s in segmentos).strip()
    except Exception:  # falta la biblioteca, el formato no se lee o el modelo falla: no se tumba el webhook
        log.exception("no se pudo transcribir la nota de voz")
        return None
    return texto or None
