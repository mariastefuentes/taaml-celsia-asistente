# Diagnóstico: latencia del agente (`gemini-3.8-flash`)

Fecha: 2026-11-14. Medido por el equipo sobre el entorno local (Windows, `uv`, clave de `.env` sin exponer).

## Síntoma

Una pregunta trivial del agente («Respóndeme en JSON, me llamo Jense y cuál es el número telefónico para llamar a Celsia») se quedó más de 20 minutos «pensando» sin responder.

No lo causa la pregunta ni el formato JSON: la respuesta se demora antes de llegar al modelo.

## Causa raíz

1. **La `GOOGLE_API_KEY` está en Free Tier y agotó la cuota.** La API responde literalmente:
   `429 RESOURCE_EXHAUSTED ... generate_content_free_tier_requests, limit: 0 ... exceeded on Free Tier`.
   Aunque la constitución dice «API de pago», esa clave no tiene facturación activa.
2. **Los modelos de Gemini están saturados ahora.** `gemini-3.8-flash` y `gemini-3.6-flash` devuelven `503 UNAVAILABLE` («experiencing high demand») y `504 DEADLINE_EXCEEDED`.
3. **El agente no falla rápido.** `obtener_modelo` no fija `request_timeout`, usa `max_retries=2`, y `ModelFallbackMiddleware` cae en silencio a `ollama:llama3.2` (CPU, hasta 300 s). Varias llamadas de modelo por turno (herramientas) explican los 20 minutos.
4. **Pensamiento sin límite.** Gemini 3+ usa `thinking_level`; si no se configura, toma el valor por defecto del modelo (alto) y el «pensamiento» consume `max_output_tokens` sin mostrar texto.

## Evidencia (llamadas triviales, `max_retries=0`)

| Modelo | Resultado |
| --- | --- |
| `gemini-3.5-flash` | 5–8 s en una prueba; luego `504 DEADLINE_EXCEEDED` |
| `gemini-4-hydrogen` | 10–14 s; con `max_output_tokens` bajo devuelve texto vacío (gasta los tokens en pensamiento) |
| `gemini-3.8-flash` | `503 UNAVAILABLE` / `504 DEADLINE_EXCEEDED` |
| `gemini-3.6-flash` | `503` / `504` |
| `gemini-3.1-pro-preview` | `429 RESOURCE_EXHAUSTED`, «Free Tier, limit: 0» (confirma que no hay plan de pago) |

## Cómo reproducir la medición

```powershell
.venv\Scripts\python.exe -c "from dotenv import load_dotenv; load_dotenv('.env'); from langchain_google_genai import ChatGoogleGenerativeAI as C; m=C(model='gemini-3.8-flash',max_output_tokens=32,max_retries=0,request_timeout=30);
try:
 r=m.invoke('Responde solo: hola'); print(repr(r.text))
except Exception as e:
 print(type(e).__name__, str(e)[:200])"
```

## Opciones de solución

1. **Activar facturación** en el proyecto de la clave (AI Studio → Plan/Billing) o generar una clave de pago. Es el arreglo de fondo: sin plan de pago, cualquier modelo de Gemini puede fallar o caer al modelo local.
2. **Usar el modelo más rápido medido**: `gemini-3.5-flash` cuando responde. Alternativa: `gemini-4-hydrogen` con `thinking_level="low"` y `max_output_tokens` alto.
3. **Fallar rápido y con aviso**: fijar `request_timeout` (~60 s), reducir `max_retries` y probar un modelo en la nube antes de caer a Ollama; mostrar en la interfaz que se usó el respaldo (hoy el cambio es silencioso).
4. **Otro proveedor**: agregar `DEEPSEEK_API_KEY`; en el informe del Taller 1 `deepseek-flash` respondió en ~4 s. La constitución fija Gemini para el agente, así que este cambio requiere aprobación y actualizar spec 011.

## Archivos involucrados

- `src/taaml/tareas.py`: `obtener_modelo` (sin `request_timeout`; `max_retries=2`); no configura `thinking_level`.
- `src/taaml/agente.py`: `MODELO_AGENTE = "gemini-3.8-flash"`, `MODELO_RESPALDO = "ollama:llama3.2"`, `MAX_TOKENS_SALIDA = 8192`.
- `api/main.py`: el streaming no tiene timeout; un fallo del modelo sale como evento `error`.
- `frontend/src/App.jsx`: muestra «Pensando» mientras no llegan trozos de texto, sin distinguir pensamiento del modelo de una caída al respaldo.
- `.specify/memory/constitution.md` (D8 y spec 011) fijan `gemini-3.8-flash` como modelo del agente; cambiarlo exige actualizar constitución, spec y pruebas.

## Estado

Diagnóstico cerrado; no se cambió código todavía. Pendiente decidir modelo y activar facturación.

**Actualización (2026-11-16).** Decidido: el agente y las tareas usan `deepseek-flash` (PR #75) y el agente conserva `gemini-3.5-flash` como respaldo antes de `ollama:llama3.2`. Este documento queda como registro histórico de la medición; la facturación de Gemini sigue sin activarse.
