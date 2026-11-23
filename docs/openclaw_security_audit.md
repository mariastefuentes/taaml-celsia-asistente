# Salida de `openclaw security audit` (23/11/2026, OpenClaw 2026.11.6)

Resumen: 0 críticos · 1 advertencia · 1 informativo.

- ADVERTENCIA `gateway.trusted_proxies_missing`: el gateway está en loopback y `gateway.trustedProxies` está vacío. Solo importa si la interfaz de control se expone por un proxy inverso; aquí se usa solo en local, así que se acepta.
- INFO: grupos abiertos = 0, mensajes directos abiertos = 0, `tools.elevated` desactivado, webhooks del gateway desactivados, control del navegador desactivado, `hooks.internal` activo.

## Repetición con `--deep`

Primer intento: 0 críticos · 2 advertencias; la segunda, `gateway.probe_failed` (timeout), porque el gateway no respondía. Se reinició el gateway (arranque lento, unos 190 s con antivirus) y, ya respondiendo, el segundo intento dio **0 críticos · 1 advertencia** (la del proxy inverso, aceptada) y 1 informativo. Sonda profunda superada.

Aviso para la demo: tras encender `openclaw gateway` hay que esperar unos 3 minutos antes de probar.
