"""Mensajes de error claros para el usuario: sin claves, tokens ni valores de las variables de entorno."""

MENSAJE_CUOTA = "Se agotó la cuota del modelo y no hubo otro disponible. Intenta más tarde o cambia de modelo en la barra lateral."
MENSAJE_API_KEY = "Falta la clave de la API en la configuración (variable de entorno sin valor). Revisa el archivo .env y elige otro modelo en la barra lateral."


def mensaje_error(error: Exception) -> str:
    """Mensaje comprensible para el usuario según el error; nunca incluye claves ni valores de configuración."""
    texto = str(error)
    if "RESOURCE_EXHAUSTED" in texto or "429" in texto:
        return MENSAJE_CUOTA
    if "API_KEY" in texto or "api_key" in texto:
        return MENSAJE_API_KEY
    return f"No se pudo completar la tarea: {texto[:200]}"
