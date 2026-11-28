# Plan 018 - Pendientes de aprobación persistentes

## Cambios

| Archivo | Cambio |
|---|---|
| `src/taaml/aprobaciones.py` | Store opcional, namespace `("aprobaciones",)`, carga al configurar, escritura en `registrar`, borrado en `quitar`, `olvidar_usuario` y fallback a memoria. |
| `api/main.py` | Configurar el Store en `lifespan`; borrar pendientes en `DELETE /api/usuarios/{usuario}/datos`. |
| `tests/test_aprobaciones.py` | Fixture con `InMemoryStore`; reinicio simulado, panel, borrado y aislamiento por cliente. |
| `tests/conftest.py` | No requiere cambios: `vaciar` limpia también el Store configurado. |
| `docs/decisiones.md`, `docs/manual_de_uso.md`, `docs/politica_de_privacidad.md`, `README.md` | D77 y límites. |

## Diseño

- El valor persistido es `asdict(Pendiente)`: código, hilo, usuario, herramienta, args, canal, teléfono y desde.
- `configurar(almacen)` se llama al arrancar; sin llamada, el módulo sigue en memoria.
- `_PENDIENTES` sigue siendo la caché que leen `todos`, `por_codigo` y `por_hilo`.
- Si el Store no responde, se registra el error y se conserva la caché del proceso.
- `_SIN_ENTREGAR` y `_DECIDIENDO` no se tocan.

## Riesgos

- `args` y teléfono quedan en la base mientras el pendiente espera; se actualiza privacidad.
- Los pendientes anteriores al despliegue no se recuperan porque el índice no guardaba `usuario`.
- Varios workers podrían ver cachés distintas; la demo usa un proceso.
- El Store añade una escritura por registro y una lectura al arrancar; no está en el camino del modelo.

## Verificación

`make check` y `make qa` no son necesarios para el panel, pero `make check` debe pasar completo.
