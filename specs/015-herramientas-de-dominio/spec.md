# Spec 015 — Veinte herramientas de dominio para el agente

- **Estado:** aprobada (retroactiva para la primera tanda; las siguientes se agregan con su propia PR).
- **Módulo:** 3 (agente en producción) y sustentación final del 28 de noviembre de 2026.
- **Rúbrica que atiende:** ítem 1.1 (20 tools `@tool` con esquema Pydantic, tipadas y trazables) y, de paso, 1.2 (el router elige con criterio) y 3.4 (el servidor MCP expone las de lectura).

## Problema

El agente tiene **5 herramientas**: `buscar_en_base`, `consultar_datos`, `guardar_dato_del_cliente`, `recordar_datos_del_cliente` y `radicar_reclamo`. La rúbrica de la sustentación final exige **20 herramientas conectadas, tipadas y demostrables**, y no acepta un agente con menos. Además, `consultar_datos` junta tres tablas en un solo esquema: el modelo ve campos que no le sirven (por ejemplo `tema` cuando busca sedes) y el enrutamiento pierde precisión.

## Objetivo

Llegar a **20 herramientas**, cada una con:

1. Un esquema Pydantic propio, con los campos justos y con `description` en todos.
2. Datos que existan en el repositorio: tablas (`data/3_gold`, `data/5_extraccion`), el Store de memoria, el registro de reclamos o `data/0_manual/`. **Ninguna herramienta inventa datos.**
3. Una prueba que la invoque sin modelo ni red, y una prueba del esquema.
4. Una etiqueta corta en `etiqueta_herramientas` para que el panel y la traza la muestren.

## Las 20 herramientas

> Ajuste del 24/11/2026 (D50): `consultar_puntos_de_pago` y `consultar_tiendas` se retiraron porque leían la misma tabla que `consultar_sedes` (que acepta el tipo) y causaban errores de conteo; en su lugar entraron las filas 5 y 6.

| # | Herramienta | Qué hace | Fuente |
|---|---|---|---|
| 1 | `buscar_en_base` | RAG sobre el texto oficial | Qdrant + embeddings |
| 2 | `consultar_sedes` | Sedes, tiendas y puntos de atención con dirección, teléfono y horario | `data/3_gold/sedes.json` |
| 3 | `consultar_contactos` | Teléfonos, WhatsApp, correos y enlaces oficiales | `data/5_extraccion/contactos.jsonl` |
| 4 | `consultar_catalogo` | Páginas del sitio por título, sección o categoría | `data/3_gold/_catalogo.csv` |
| 5 | `verificar_canal_oficial` | Dice si un teléfono, correo o enlace «sí figura» o «no figura» entre los canales oficiales (D50) | tablas de contactos y sedes |
| 6 | `calcular_factura_estimada` | Estimado de la factura: kWh × tarifa, cargo fijo y subsidio o contribución (D50) | cálculo con lo que dice el cliente |
| 7 | `consultar_canales_de_atencion` | Canal que corresponde a una necesidad (pagos, emergencia, facturación) | tabla de contactos |
| 8 | `consultar_cobertura` | Si hay atención presencial en una ciudad | tabla de sedes |
| 9 | `consultar_tramite_en_linea` | Enlace oficial para pagar, reportar un daño o registrar la factura digital | `data/0_manual/canales_atencion.md` |
| 10 | `consultar_politica_de_datos` | Cómo trata Celsia los datos del cliente | `docs/politica_de_privacidad.md` |
| 11 | `guardar_dato_del_cliente` | Memoria de largo plazo | Store `("perfil", usuario)` |
| 12 | `recordar_datos_del_cliente` | Devuelve lo guardado | Store `("perfil", usuario)` |
| 13 | `listar_datos_del_cliente` | Lista lo guardado para que el cliente lo revise | Store `("perfil", usuario)` |
| 14 | `olvidar_dato_del_cliente` | Borra un dato puntual (derecho de supresión) | Store `("perfil", usuario)` |
| 15 | `radicar_reclamo` | Radica un reclamo con aprobación humana | Store `("reclamos", usuario)` + HITL |
| 16 | `consultar_mis_reclamos` | Lista los reclamos del cliente | Store `("reclamos", usuario)` |
| 17 | `consultar_estado_reclamo` | Estado de un reclamo por su número | Store `("reclamos", usuario)` |
| 18 | `cancelar_reclamo` | Pide cancelar un reclamo, con aprobación humana | Store + HITL |
| 19 | `derivar_a_asesor` | Registra que el cliente pidió una persona y entrega los canales oficiales | tabla de contactos |
| 20 | `reportar_dano_electrico` | Reporta un daño o falla con aprobación humana | Store + HITL |

`consultar_datos` se retira cuando el prompt v13 ya usa las tres herramientas por tabla: mantener las dos formas dejaría siete herramientas sobre las mismas tablas.

## Fuera de alcance

- Herramientas que dependan de sistemas de Celsia que no tenemos (estado de cuenta, cortes programados, pago real). Se documenta como límite en `docs/decisiones.md`.
- Un glosario o un FAQ nuevos: exigirían datos escritos a mano que hoy no están en `data/0_manual/`.

## Criterios de aceptación

- [ ] `HERRAMIENTAS` tiene 20 elementos y una prueba fija la lista.
- [ ] Cada herramienta tiene `args_schema` propio y todos sus campos tienen `description`.
- [ ] Ninguna herramienta que escribe en el Store o pausa el flujo queda fuera de `APROBACION_HUMANA`.
- [ ] `make test` y `make lint` pasan sin red ni claves.
- [ ] El README y `docs/decisiones.md` describen las 20 herramientas y sus límites.
