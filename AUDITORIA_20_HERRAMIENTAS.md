# AUDITORIA_20_HERRAMIENTAS — TAAML Celsia

**Solo lectura; no código, no config, no WhatsApp, no token, no commits/push/PR.** Fuentes: `src/taaml/agente.py`, `src/taaml/servidor_mcp.py`, `src/taaml/openclaw.py`, `src/taaml/puente_mcp.py`, `openclaw/openclaw.example.json`, `openclaw/plugins/puente-celsia.js`, `~/.openclaw/openclaw.json`, `openclaw/README.md`, `docs/guia_despliegue_openclaw.md`, `docs/decisiones.md`, `AGENTS.md`, `tests/`. `make test` **547 passed, 2 skipped**; `make qa` `14 passed`; `openclaw config validate`; `openclaw mcp list`; `openclaw mcp doctor`; `openclaw sandbox explain`; `openclaw plugins inspect`. `make test`. **No real token.**

## Regla de conteo (no doble)
**Herramienta independiente del agente** = `@tool` + entrada en `taaml.agente.HERRAMIENTAS` + `create_agent(tools=...)`. **MCP no cuenta como 20 extra**: `servidor_mcp.py` **no añade funcionalidad**, envuelve 10 tools del agente; `puente_mcp.atender_cliente_celsia` **no añade** tools, llama `POST /chat`→`conversar`→mismas 20. **OpenClaw `skills_read`,`exec`,`process`,`read`,`write`,`whatsapp`,`memory`,`sessions`,`browser`,`canvas`,`gateway`,`cron`... no son tools Celsia.** `OpenClaw` `toolFilter`,`sandbox` no crea herramientas. `flujo_reclamo.construir_flujo` `radicar_simulado` **no registrada**; `radicar_reclamo` usa `radicar_simulado` `REC-XXXXXXXX` **no sistema real Celsia**. `flujo_reclamo.Reclamo` vs `agente.Reclamo` no separadas. `mcp` 10 + `puente` 1 no suman al 20. `HITL` no tool.

**20 agente + 10 MCP `celsia` + 1 MCP `puente` + OpenClaw propios.** 

## Veredicto
**CUMPLE PARCIALMENTE.** **20 independientes del agente; faltan 0 para 20.** `HERRAMIENTAS len=20`, `APROBACION_HUMANA 3`, `make test`. **OpenClaw tiene acceso** a las 20 **vía `mcp puente atender_cliente_celsia`→`POST /chat`** (no `celsia` directo a memoria/reclamos; `mcp list`,`mcp doctor`,`sandbox puente__*`,`puente-celsia`,`toolFilter`,`problemas=0`,`POST /chat` `200 ok` verificado antes; no real test ahora). MCP `celsia` da **10 de lectura**. **Caveats no numéricos:** `puente-celsia record-missing`, `mcp probe offline-only`, `radicar_simulado`, `DAN-`, `avisos_openclaw=false`, `OPENCLAW_AVISOS`, `CHAT_TOKEN`, `APROBADOR_TOKEN`, `record-missing`, `POST /chat` no WhatsApp real. **Cuenta 20 CUMPLE; funcionalidad/OpenClaw completa no afirmada.**

## A. 20 herramientas del agente (`taaml.agente`, `src/taaml/agente.py`; registración `@tool(args_schema=...)` + `HERRAMIENTAS` + `create_agent`; OpenClaw indirecto `puente__atender_cliente_celsia`)

| # | Nombre | Función | Archivo | Registración | Funciona / prueba |
|---|---|---|---|---|---|
| 1 | `buscar_en_base` | RAG oficial Celsia Qdrant; `categoria`,`region`,`k=12`,`fuente`; `response_format=content_and_artifact`,`Citas`. | `src/taaml/agente.py:205`,`taaml.recuperacion`,`taaml.vectorstore`,`taaml.citas`. | `@tool(args_schema=BusquedaEnBase,response_format="content_and_artifact")`,`HERRAMIENTAS`. | `make test`,`test_agente`,`test_recuperacion`,`test_citas`,`test_api`; `POST /chat` `buscar_en_base` `POST /chat 200` antes; `mcp.servidor_mcp.buscar_informacion_celsia`. |
| 2 | `consultar_sedes` | sedes/tiendas/puntos; ciudad/depto/tipo; dirección/tel/horario. | `src/taaml/agente.py:310`,`taaml.consulta_datos`. | `@tool(args_schema=ConsultaSedes)`,`HERRAMIENTAS`. | `test_agente`,`test_consulta_datos`,`test_api`,`test_flujo`; `POST /chat` `consultar_sedes` `POST /chat 200` antes. `consultar_sedes_celsia`. |
| 3 | `consultar_contactos` | teléfonos WhatsApp correos enlaces oficiales. | `src/taaml/agente.py:335`,`taaml.servicios_celsia`. | `@tool(args_schema=ConsultaContactos)`,`HERRAMIENTAS`. | `test_servicios_celsia`,`test_agente`,`POST /chat` `consultar_contactos` `200` antes. `consultar_contactos_celsia`. |
| 4 | `consultar_catalogo` | páginas por título/sección/categoría enlace. | `src/taaml/agente.py:351`,`taaml.consulta_datos`. | `@tool(args_schema=ConsultaCatalogo)`,`HERRAMIENTAS`. | `test_consulta_datos`,`test_agente`. `consultar_catalogo_celsia`. |
| 5 | `consultar_canales_de_atencion` | canal oficial por necesidad/tipo. | `src/taaml/agente.py:370`,`taaml.servicios_celsia`. | `@tool(args_schema=ConsultaCanales)`,`HERRAMIENTAS`. | `test_servicios_celsia`,`test_agente`. `consultar_canales_de_atencion_celsia`. |
| 6 | `consultar_cobertura` | atención presencial ciudad + nº puntos. | `src/taaml/agente.py:383`,`taaml.servicios_celsia`. | `@tool(args_schema=ConsultaCobertura)`,`HERRAMIENTAS`. | `test_servicios_celsia`,`test_agente`. `consultar_cobertura_celsia`. |
| 7 | `consultar_tramite_en_linea` | enlace pagar/reportar/factura digital/PQR/Zona Clientes. | `src/taaml/agente.py:412`,`taaml.servicios_celsia`. | `@tool(args_schema=ConsultaTramiteEnLinea)`,`HERRAMIENTAS`. | `test_servicios_celsia`,`test_agente`. `consultar_tramite_en_linea_celsia`. |
| 8 | `consultar_politica_de_datos` | política privacidad asistente. | `src/taaml/agente.py:434`,`taaml.informacion_manual`. | `@tool(args_schema=ConsultaPoliticaDeDatos)`,`HERRAMIENTAS`. | `test_informacion_manual`,`test_agente`. `consultar_politica_de_datos_celsia`. |
| 9 | `verificar_canal_oficial` | tel/WhatsApp/correo/enlace oficial? sin llamar si figura. | `src/taaml/agente.py:450`,`taaml.servicios_celsia`. | `@tool(args_schema=CanalAVerificar)`,`HERRAMIENTAS`. | `test_servicios_celsia`,`test_agente`. `verificar_canal_oficial_celsia`. |
| 10 | `calcular_factura_estimada` | kWh*tarifa+fijo+ajuste%; no factura oficial. | `src/taaml/agente.py:468`. | `@tool(args_schema=FacturaEstimada)`,`HERRAMIENTAS`. | `test_agente`,`test_api`,`PDF`. `calcular_factura_estimada_celsia`. `150*900=135000`. |
| 11 | `guardar_dato_del_cliente` | memoria larga propio; no secretos; no anónimo; no `referencia`. | `src/taaml/agente.py:532`. | `@tool(args_schema=DatoDelCliente)`,`HERRAMIENTAS`. | `test_agente`,`test_api`,`test_conversaciones`,`test_memoria_postgres`,`test_api`. `PostgresStore`. |
| 12 | `recordar_datos_del_cliente` | recall propio. | `src/taaml/agente.py:548`. | `@tool(args_schema=SinArgumentos)`,`HERRAMIENTAS`. | `test_agente`,`test_conversaciones`,`PDF`. PDF #12 no requiere tool. |
| 13 | `listar_datos_del_cliente` | lista memoria. | `src/taaml/agente.py:579`. | `@tool(args_schema=SinArgumentos)`,`HERRAMIENTAS`. | `test_agente`,`test_api`,`PDF`. |
| 14 | `olvidar_dato_del_cliente` | borra dato propio; sin tildes; no anónimo; `olvidar_todo`. | `src/taaml/agente.py:591`,`api`. | `@tool(args_schema=DatoAOlvidar)`,`HERRAMIENTAS`. | `test_agente`,`test_api`,`test_memoria`,`test_conversaciones`,`test_api`. `/api/olvidar`. `Olvidar todo`. `make qa`. `origin`. `PR #218`. |
| 15 | `radicar_reclamo` | `tipo falla_de_servicio/facturacion/otro`,`ciudad`,`descripcion`,`referencia`; **HITL `radicar_reclamo` approve/edit/reject/respond**; `MENSAJE_EN_REVISION`,`MENSAJES_APROBADO`,`radicar_simulado REC-XXXXXXXX`,**no radicado oficial Celsia**; memoria sin `referencia`. | `src/taaml/agente.py:616`,`taaml.flujo_reclamo`,`taaml.aprobaciones`,`api`. | `@tool(args_schema=Reclamo)`,`HERRAMIENTAS`,`APROBACION_HUMANA`. | `test_flujo_reclamo`,`test_agente`,`test_aprobaciones`,`test_api`,`test_memoria_postgres`,`PDF`,`make qa`. `/panel` `Por aprobar`,`/api/pendientes`. **No aprobar.** |
| 16 | `consultar_mis_reclamos` | lista reclamos propio `REC`; máx `MAX_RECLAMOS_POR_CLIENTE`. | `src/taaml/agente.py:663`. | `@tool(args_schema=SinArgumentos)`,`HERRAMIENTAS`. | `test_agente`,`test_flujo`,`PDF`. `radicar_simulado`. |
| 17 | `consultar_estado_reclamo` | estado por radicado propio; si no coincide. | `src/taaml/agente.py:679`. | `@tool(args_schema=ConsultaEstadoReclamo)`,`HERRAMIENTAS`. | `test_agente`,`test_flujo`,`PDF`. `REC`. no oficial. |
| 18 | `cancelar_reclamo` | pide cancelar propio; **HITL `cancelar_reclamo` approve/reject/respond**; no `referencia`. | `src/taaml/agente.py:707`,`api`. | `@tool(args_schema=CancelarReclamo)`,`HERRAMIENTAS`,`APROBACION_HUMANA`. | `test_agente`,`test_aprobaciones`,`test_api`,`PDF`. `MENSAJES_APROBADO`,`REC`. no cancelar real sin aprobar. |
| 19 | `derivar_a_asesor` | deriva a persona canales oficiales; `urgente`; `derivaciones`. | `src/taaml/agente.py:736`,`taaml.servicios`. | `@tool(args_schema=Derivacion)`,`HERRAMIENTAS`. | `test_agente`,`test_api`,`PDF`. `01 8000 112 115`. `origin` `PR`. no promete llamada. `APROBADOR_WHATSAPP`. |
| 20 | `reportar_dano_electrico` | daño eléctrico; datos; `123`,`01 8000 112 115`,`DAN-XXXXXXXX`; **HITL `reportar_dano_electrico` approve/edit/reject/respond**. | `src/taaml/agente.py:768`,`api`. | `@tool(args_schema=ReporteDeDano)`,`HERRAMIENTAS`,`APROBACION_HUMANA`. | `test_agente`,`test_aprobaciones`,`test_api`,`PDF`. `consultar_canales_de_atencion`,`MENSAJES_APROBADO`,`DAN`. **no reporte real sin aprobar.** |

**`HERRAMIENTA 20` nota `PDF`:** `recordar_datos_del_cliente` puede ser usada; también `memoria` tras reiniciar, chat web, `Nueva conversación`. 

## B. Herramientas MCP `celsia` (`servidor_mcp.py`, NO +20; solo 10 lectura/cálculo, no escritura/memoria/reclamos; `make mcp`, `uv run python -m taaml.servidor_mcp`,`stdio`,`MCPServer("celsia")`,`@servidor.tool`,`toolFilter.include`; OpenClaw `mcp.servers.celsia`,`celsia__*`,`mcp list`,`mcp doctor`)
1 `buscar_informacion_celsia`→`buscar_en_base` (#1). 
2 `consultar_sedes_celsia`→`consultar_sedes` (#2). 
3 `consultar_contactos_celsia`→`consultar_contactos` (#3). 
4 `consultar_catalogo_celsia`→`consultar_catalogo` (#4). 
5 `consultar_canales_de_atencion_celsia`→`consultar_canales_de_atencion` (#5). 
6 `consultar_cobertura_celsia`→`consultar_cobertura` (#6). 
7 `consultar_tramite_en_linea_celsia`→`consultar_tramite_en_linea` (#7). 
8 `consultar_politica_de_datos_celsia`→`consultar_politica_de_datos` (#8). 
9 `verificar_canal_oficial_celsia`→`verificar_canal_oficial` (#9). 
10 `calcular_factura_estimada_celsia`→`calcular_factura_estimada` (#10). `tests/test_servidor_mcp.py`. 

## C. MCP `puente` (`puente_mcp.py`, NO +20; `MCPServer("puente")`,`@servidor.tool`,`atender_cliente_celsia`,`toolFilter`,`stdio`,`uv run python -m taaml.puente_mcp`,`CELSIA_API_URL`,`CHAT_TOKEN`,`WHATSAPP_ALLOWLIST`,`E164`,`autorizado`,`LIMITE`,`MENSAJE_NO_AUTORIZADO`,`MENSAJE_DE_FALLO`,`X-Api-Key`,`POST /chat`,`respuesta`,`sandbox puente__*`,`mcp.servers.puente`,`mcp list`,`mcp doctor`,`toolSearch=false`,`puente-celsia`,`skills atencion-whatsapp-celsia`)
`atender_cliente_celsia(mensaje,telefono)`→`atender`→`POST /chat`→`conversar`→**20** + `pendiente`/`resolver_aprobacion`→devuelve `respuesta` sin cambios. `tests/test_puente_mcp.py`. **`puente-celsia` `record-missing`.** `POST /chat 200 ok=true` antes. `mcp probe offline-only`. **`POST /chat` `CHAT_TOKEN` no público `/chat`; acceso público WhatsApp≠`/chat` público.** 

## D. OpenClaw propias (NO contar como 20 Celsia)
`OpenClaw 2026.11.7`. `agent` `create_agent`. `openclaw` `skills_read`,`tools`,`memory`,`exec`,`process`,`read`,`ls`,`write`,`edit`,`apply_patch`,`view_image`,`github`,`sessions`,`subagents`,`session_status`,`goal`,`browser`,`canvas`,`nodes`,`automation`,`gateway`,`channels`,`cron`,`whatsapp`,`memory-core`,`dream`,`a2a`,`telegram`,`discord`,`slack`,`matrix`,`...`. `deny group:automation,group:runtime,group:fs,sessions_spawn`; `workspaceOnly`,`exec deny`,`elevated false`,`sandbox mode=all backend=docker scope=agent workspaceAccess=none`,`protectedSkill`. `messaging`. `plugins puente-celsia`,`whatsapp`,`deepseek`,`skills`. `atencion-whatsapp-celsia`. `openclaw` `mcporter`. `tools.toolSearch=false`. `OpenClaw `**no** `radicar_reclamo` directo; `mcp puente`.** `tests/test_openclaw.py`,`test_openclaw_workspace.py`,`test_puente_mcp.py`. 

## OpenClaw acceso a 20
- `mcp.servers.puente` `atender_cliente_celsia`,`puente__*`,`mcp puente`,`puente-celsia`,`CHAT_TOKEN`,`POST /chat`,`X-Api-Key`,`LIMITE`,`respuesta`. **20 indirecto.** `mcp servers.celsia` `10`. `mcp list`,`mcp doctor`,`mcp status`,`mcp reload`. `problemas=0`. `openclaw config validate`. `POST /chat`. `record-missing`. `mcp probe`. `skill`. `PDF ver_panel`. `usadas 20`. **No real PDF Fase5 ejecutada aquí.** 

## `taaml.openclaw.problemas` (no número tools pero exige puente/20)
`mcp servers.celsia`,`mcp servers.puente`,`puente__*`,`puente-celsia`,`toolSearch=false`,`atencion-whatsapp-celsia`,`modelo`,`deepseek`,`dmPolicy`,`allowlist`,`WHATSAPP_ALLOWLIST`,`sandbox`,`gateway`,`tools`. `"lleva los mensajes al agente de Celsia con sus 20 herramientas"`. `problemas=0`. **`record-missing`.** 

## Conteo
**20** independientes `taaml.agente`. `falta 0`. `MCP` `10`+`1`. `OpenClaw`. **`CUMPLE` numérico; `CUMPLE PARCIALMENTE`.** `test`. no code. 

## Limitaciones
No real PDF Fase5 full; no `make qa QA_MODELO_REAL`; no `mcp probe` con Gateway off; no `openclaw plugins registry`; `record-missing`; `radicar_simulado`/`DAN`; `POST /chat` sin repetir; `/panel` no aprobar; `APROBADOR_TOKEN`; `OPENCLAW_AVISOS`; `avisos_openclaw=false`; `CHAT_TOKEN`; `WHATSAPP_ALLOWLIST`; `dmPolicy`; `**64`,`**69`,`*`; no `.env`; no producción; no real WhatsApp. `modelo=deepseek-flash`,`RAG_MODO=cadena`,`Qdrant`,`PostgreSQL`,`gemini-embedding`,`MCP`,`HITL`; no afectan conteo. 

## Veredicto final
**CUMPLE PARCIALMENTE** — requisito académico **20 herramientas: CUMPLE (`20`,`0` faltan)**, `test_agente`,`test_servidor_mcp`,`test_puente_mcp`,`test_openclaw`,`test_flujo`,`test_aprobaciones`,`test_*`,`make test`,`make qa`; OpenClaw `mcp`,`sandbox`,`puente`,`puente-celsia`,`problemas`,`POST`. No afirmar `record-missing`,`radicar_simulado`,`real WhatsApp`,`avisos` listo. 
