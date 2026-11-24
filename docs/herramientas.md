# Inventario de las 20 herramientas del agente (23/11/2026)

El agente `create_agent` decide con *function calling*: cada herramienta tiene un esquema Pydantic estricto (`extra="forbid"`, largos y valores validados) del que sale el JSON Schema que ve el modelo. Las que usan la memoria o al cliente llevan `runtime` en el esquema, marcado `exclude`: lo inyecta LangChain y el modelo no lo ve. Código: `src/taaml/agente.py` (las 5 primeras y los dos borrados) y `src/taaml/herramientas_servicio.py` (las demás). Pruebas: `tests/test_agente.py`, `tests/test_herramientas_servicio.py`, `tests/test_prompts.py`. Prompt vigente: `prompts/v13_agente.md`.

| # | Herramienta | Para qué sirve | Guarda algo | Aprobación humana |
|---|---|---|---|---|
| 1 | `buscar_en_base` | Busca en la información oficial (Qdrant, significado + palabras) y devuelve fuentes | No | No |
| 2 | `consultar_datos` | Consulta exacta de sedes, contactos y catálogo (con total contado por código) | No | No |
| 3 | `guardar_dato_del_cliente` | Guarda un dato que el cliente contó de sí mismo | `perfil` | No |
| 4 | `recordar_datos_del_cliente` | Devuelve lo que contó antes | No | No |
| 5 | `radicar_reclamo` | Radica un reclamo (simulado) | `reclamos` | **Sí** |
| 6 | `sedes_cercanas` | Las 3 sedes más cercanas por coordenadas o ciudad | No | No |
| 7 | `ciudades_con_atencion` | Ciudades con atención, por departamento, con total | No | No |
| 8 | `verificar_canal_oficial` | Dice si un número, correo o enlace «sí figura» o «no figura» como oficial (nunca «es falso») | No | No |
| 9 | `canales_de_emergencia` | La 123, WhatsApp de energía, reporte de daños y la línea 01 8000 | No | No |
| 10 | `fecha_y_hora_actual` | Día y hora de Colombia (para «¿está abierta ahora?») | No | No |
| 11 | `calcular_factura_estimada` | kWh × tarifa + cargo fijo + ajuste; siempre «estimado» | No | No |
| 12 | `consumo_de_un_aparato` | Consumo de un aparato (W × horas × días); nunca supone la potencia | No | No |
| 13 | `estimar_ahorro_solar` | Ahorro hipotético con paneles; declara el escenario | No | No |
| 14 | `consultar_estado_reclamo` | Qué figura de un radicado del cliente (sin inventar la gestión) | No | No |
| 15 | `listar_mis_reclamos` | Reclamos del cliente, el más nuevo primero | No | No |
| 16 | `agregar_detalle_a_reclamo` | Añade una nota a un reclamo ya radicado | `reclamos` | **Sí** |
| 17 | `escalar_a_asesor` | Anota que pide hablar con una persona y da los canales; no promete llamada ni tiempo | `escalamientos` | No (solo es una nota) |
| 18 | `calificar_atencion` | Guarda una nota de 1 a 5 con comentario opcional (tope de 10) | `calificaciones` | No |
| 19 | `olvidar_datos_del_cliente` | Borra todo lo guardado del cliente, en dos pasos: avisa y pide confirmación; solo borra si el cliente confirma | borra todo | La confirma el cliente |
| 20 | `resumen_de_mi_actividad` | Cuenta datos, reclamos, solicitudes y calificaciones del cliente | No | No |

## Reglas comunes
- Un cliente anónimo no guarda nada; cada cliente solo ve y borra lo suyo (el espacio del Store lleva su identificador).
- Los textos guardados pasan por `quitar_invisibles` y tienen largo máximo; no se guardan cédulas, claves ni tarjetas.
- El borrado del cliente (`olvidar_cliente`) elimina `perfil`, `reclamos`, `escalamientos` y `calificaciones`.
- Lo que devuelve una herramienta es dato, no orden (defensa contra inyección indirecta).

## Límites conocidos
- `sedes_cercanas` solo funciona con ciudades que tienen una sede (por ejemplo, Cali no).
- «Buga» y «Guadalajara de Buga» cuentan como dos ciudades en `ciudades_con_atencion`.
- Los reclamos, solicitudes y calificaciones son una simulación: no llegan a un sistema real de Celsia.
- Los botones de WhatsApp para el mensaje de aprobación del detalle no se probaron con Meta real.
- El almacén en memoria de las pruebas reinicia la fecha de creación en cada guardado; Postgres la conserva.
