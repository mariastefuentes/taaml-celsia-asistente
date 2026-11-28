# Plan 018 — Atajos de intención

## Cambios

| Archivo | Cambio |
|---|---|
| `src/taaml/atajos.py` | `normalizar()`, `respuesta_rapida()` y los cuatro textos compartidos. Coincidencia exacta sobre la frase completa. |
| `src/taaml/aprobaciones.py` | `hay_sin_entregar(hilo)` para consultar sin consumir la decisión pendiente. |
| `api/main.py` | Atajo en `_turno` (chat web) y en `responder_a_telefono` (puente de OpenClaw); `_responder_comando` usa el normalizador compartido. |
| `tests/test_atajos.py` | Variantes triviales y mensajes con contenido que no deben usar el atajo. |
| `tests/test_api.py` | Saludo web y por teléfono sin modelo; saludo con pregunta sigue al agente; reclamo pendiente no usa el atajo. |
| `docs/decisiones.md` | D76 (atajo por reglas; Jev no adoptado) y nota en D9/D17. |
| `README.md` | Fila de la tabla del agente. |

## Decisiones

- **Reglas, no Jev:** cero dependencia nueva, cero costo y determinista para la demo. Jev queda como mejora futura.
- **Coincidencia completa:** el patrón va anclado; si hay una palabra de contenido, no coincide. Es el seguro contra respuestas bobas.
- **Textos compartidos:** web y OpenClaw usan los mismos; Meta conserva botones.
- **Sin historial:** el atajo no escribe en el checkpointer; al recargar el chat no reaparece.

## Verificación

`make check`, `make qa` y una prueba manual: «hola» en el chat web debe responder al instante, el chat debe mostrar `atajo: saludo` y el panel debe registrar la fila con costo 0.
