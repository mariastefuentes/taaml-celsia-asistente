"""Comprueba que las claves guardadas en .env funcionan (Gemini y Hugging Face).

Uso:  uv run python scripts/utilidades/verificar_claves.py
"""
import json
import os
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def pedir(url: str, cabeceras: dict) -> dict:
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=cabeceras), timeout=20))


def probar(nombre: str, variable: str, url: str, cabecera: str, prefijo: str = "") -> None:
    valor = os.getenv(variable)
    if not valor:
        print(f"-  {nombre}: sin clave ({variable} está vacía)")
        return
    try:
        datos = pedir(url, {cabecera: prefijo + valor})
        extra = f", usuario: {datos['name']}" if "name" in datos else f", {len(datos.get('models', []))} modelos listados"
        print(f"OK {nombre}: la clave es válida{extra}")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR {nombre}: {getattr(exc, 'code', '')} {exc}")


probar("Gemini", "GOOGLE_API_KEY", "https://generativelanguage.googleapis.com/v1beta/models?pageSize=5", "x-goog-api-key")
probar("Hugging Face", "HF_TOKEN", "https://huggingface.co/api/whoami-v2", "Authorization", "Bearer ")
