# Guía de despliegue de OpenClaw (sustentación final)

Esta guía lleva el asistente de Celsia al gateway de OpenClaw que pide la rúbrica del 28 de noviembre de 2026: **3.1** (gateway con configuración versionada), **3.2** (WhatsApp real con allowlist E.164), **3.3** (workspace) y **4.2** (sandbox y auditoría). La alternativa —el webhook propio con la API Cloud de Meta— sigue siendo la vía principal de la demo y se describe al final.

> **Estado.** La configuración se versionó el 23/11/2026 (`openclaw/openclaw.example.json`, decisiones D47 y D48) a partir de la que funcionó en D35. **No se validó en el equipo donde corre esta guía**: aquí no hay OpenClaw instalado. Antes de la demo hay que ejecutar los pasos 3, 6 y 7 y corregir lo que cambie de nombre entre versiones.

## 0. Qué se necesita

| Pieza | Para qué |
|---|---|
| OpenClaw instalado y en el `PATH` | Gateway y canales |
| Docker | Imagen del sandbox (`openclaw-sandbox:trixie-slim`) |
| `uv` y este repositorio | El servidor MCP `celsia` corre con `uv run` |
| Cuenta de Meta con la app de WhatsApp | Canal de WhatsApp de la vía alterna (webhook propio) |
| Número dedicado para el bot | Chip prepago o eSIM de voz/SMS en un celular de repuesto (nunca el personal de un integrante); ver la sección 6 |
| Clave del proveedor del modelo | `deepseek/deepseek-flash` (la plantilla vigente; respaldo apagado) |

## 1. Variables (en `.env`, nunca en el repositorio)

```text
OPENCLAW_GATEWAY_TOKEN=<cadena larga y aleatoria>
WHATSAPP_ALLOWLIST=*
REPO_CELSIA=C:/ruta/absoluta/a/taaml-celsia-asistente
```

`REPO_CELSIA` es la ruta donde OpenClaw lanzará `uv run python -m taaml.servidor_mcp`; tiene que ser la del equipo que hace la demo, no la de un compañero. `WHATSAPP_ALLOWLIST=*` deja el canal abierto al auditorio (D54); si prefieres una lista cerrada, escribe los números en E.164 separados por comas, pero entonces los invitados que no estén en ella recibirán «Este número no está autorizado».

## 2. Instalar configuración y workspace

```bash
make openclaw-check        # valida endurecimiento, allowlist E.164 y ausencia de secretos; no escribe
make openclaw-instalar     # escribe ~/.openclaw/openclaw.json y copia el workspace
```

Si ya había una configuración, `make openclaw-instalar ARGS="--forzar"` deja un `openclaw.json.bak` al lado. Lo instalado incluye:

- `bind: loopback` y token de gateway.
- `tools.deny`: `group:automation`, `group:runtime`, `group:fs`, `sessions_spawn`.
- `tools.fs.workspaceOnly: true` y `tools.exec.mode: deny`.
- Permisos elevados y navegador apagados.
- Sandbox Docker en modo `all` con `workspaceAccess: none`, permitiendo dentro solo `celsia__*`.
- Modelo primario y respaldo.
- Servidor MCP `celsia` con sus diez herramientas de solo lectura.

## 3. Validar en el equipo de la demo

```bash
openclaw config validate     # esquema de la versión instalada
openclaw security audit      # debe salir en verde
```

Si `config validate` rechaza una clave, se corrige **la plantilla del repositorio** (y su prueba) en la misma PR; no se edita a mano el archivo de `~/.openclaw` y se deja así, porque el siguiente `make openclaw-instalar` lo pisa.

## 4. Imagen del sandbox

Solo la primera vez en el equipo:

```bash
docker build -t openclaw-sandbox:trixie-slim <ruta-de-la-documentación-de-openclaw>
docker images | grep openclaw-sandbox
```

Sin esa imagen, el sandbox activo deja al agente sin herramientas y responde «no tengo evidencia»: es el fallo que documentó D35.

## 5. Registrar el servidor MCP

Con el **gateway apagado** (D35: `mcp add` falla si está encendido):

```bash
openclaw mcp add celsia --transport stdio -- uv run python -m taaml.servidor_mcp
openclaw mcp list
```

Debe listar `celsia` con diez herramientas (`buscar_informacion_celsia`, `consultar_sedes_celsia`, …). Si no, revisar `REPO_CELSIA` y que `uv sync` haya corrido en esa carpeta.

## 6. Canal de WhatsApp

1. Arrancar el gateway (`openclaw gateway`, o como servicio del sistema).
2. Vincular el canal de WhatsApp con el procedimiento nativo de OpenClaw (imprime un QR; escanéalo desde la app WhatsApp → Mis dispositivos vinculados):

```bash
openclaw channels login --channel whatsapp --verbose
openclaw channels logs
```

3. Comprobar el estado, la sesión y los servidores MCP (verificado el 2026-11-24):

```bash
openclaw channels status --probe
openclaw mcp doctor celsia --probe   # «celsia: ok»
openclaw mcp list                    # lista el servidor «celsia»
```

4. Definir la allowlist. Para el auditorio, `WHATSAPP_ALLOWLIST=*` (canal abierto, D54); para una lista cerrada, los números en E.164 separados por comas:

```text
WHATSAPP_ALLOWLIST=*
```

5. Generar el QR del número del bot y proyectarlo:

```bash
make qr-whatsapp ARGS="+57<numero-del-bot>"                 # qr_whatsapp.png
make qr-whatsapp ARGS="+57<numero-del-bot> --html --app"    # + página para proyectar y QR dentro de la app
```

El QR abre `wa.me` con un «Hola» precargado. Quien lo escanea entra al chat del número vinculado, sin instalar nada ni estar en una lista. Con `--app` queda en `assets/whatsapp_qr.png`, que el chat web y el panel en vivo muestran en `/qr-whatsapp.png`.

6. Probar desde dos teléfonos que **no** sean del equipo: una pregunta de sedes (tool de tabla), un «¿qué sabes de mí?» (memoria) y un reclamo con aprobación humana. La traza debe mostrar la herramienta elegida.

### El puente: las 20 herramientas por el canal de OpenClaw (D52)

El agente de OpenClaw solo ve las diez herramientas de solo lectura del MCP `celsia`. Para que **lo que se escribe por el WhatsApp de OpenClaw lo atienda el agente completo** (20 herramientas, memoria por cliente, reclamos con aprobación humana), la plantilla conecta un segundo MCP, `puente`, con **una sola herramienta**: `atender_cliente_celsia(mensaje, telefono)`, que llama a `POST /chat` de la API.

```
cliente → WhatsApp (QR) → OpenClaw → atender_cliente_celsia → POST /chat → agente de Celsia (20 herramientas) → respuesta
```

- **Quién escribe lo fija OpenClaw, no el modelo.** OpenClaw no manda el remitente a los MCP por stdio (se comprobó con un servidor espejo), así que el plugin `openclaw/plugins/puente-celsia.js` usa el gancho `before_tool_call` y reemplaza `telefono` con `ctx.requester.senderId`, el remitente verificado del canal. Sin remitente, bloquea la llamada. El puente además exige que el número esté en `WHATSAPP_ALLOWLIST`.
- **Requisitos:** la API encendida (`make api`), `CHAT_TOKEN` igual en `.env` y en el entorno de OpenClaw, y el plugin del canal instalado (`openclaw plugins install npm:@openclaw/whatsapp`).
- **Instrucciones al modelo:** `workspace/AGENTS.md` (sección «Canal de WhatsApp») manda llamar la herramienta en cada mensaje y devolver su texto sin cambios; `tools.toolSearch: false` deja el esquema a la vista.
- **Si falla el puente**, responde la frase de contingencia con la línea 01 8000 112 115 y la demo sigue por el webhook propio de Meta.

### El número propio del bot (D54)

El canal de OpenClaw se vincula como **dispositivo vinculado** de una cuenta de WhatsApp: el bot responde desde ese número. Por eso hace falta un número dedicado, no el personal de un integrante:

1. Chip prepago o **eSIM de voz/SMS** (las de solo datos no reciben el código) en un celular de repuesto.
2. **La cuenta de WhatsApp vive en ese celular**, no en el computador: instalar WhatsApp, registrar el número (el código llega por SMS o llamada al chip nuevo) y poner el perfil «Asistente Celsia» (foto y descripción). Los invitados verán ese nombre.
3. Con ese celular ya con WhatsApp, ejecutar en el equipo de la demo `openclaw channels login --channel whatsapp`. OpenClaw imprime un **QR de vinculación**; escanearlo **desde ese mismo celular** en WhatsApp → Dispositivos vinculados → Vincular un dispositivo. No se escanea desde el celular de un invitado.
4. El celular puede quedar apagado durante la demo; WhatsApp cierra la sesión del dispositivo vinculado tras unos 14 días sin actividad del teléfono, así que hay que reconectarlo cada dos semanas.

**Los dos QR no son el mismo.** El de `openclaw channels login` se escanea **una sola vez**, desde el celular del chip, para que OpenClaw quede vinculado. El de `make qr-whatsapp` es el que se proyecta al auditorio: cualquier invitado lo escanea con la cámara y abre el chat con el bot. Si el QR de invitados se escaneara desde el celular del chip, no vincularía nada: solo abriría un chat del bot consigo mismo.

**Riesgo.** La automatización de OpenClaw no es oficial: un uso intensivo puede hacer que WhatsApp banee el número. Se usa un número dedicado y el webhook de Meta queda como plan B.

**Si el canal de OpenClaw no queda listo**, la demo no se cae: el bot sigue respondiendo por el webhook propio de Meta (apartado 8).

## 7. Evidencia para el repositorio

Guardar en `docs/auditoria_openclaw.md` la salida real de:

```text
openclaw security audit
openclaw channels status --probe
```

con fecha, equipo y quién lo corrió. **No se inventa la salida**: si algo queda en amarillo, se documenta y se explica en la sustentación.

## 8. Vía alterna: webhook propio con Meta (la de la demo)

Es la que ya funciona y la que usa el agente con las 20 herramientas:

```bash
make api                       # API + PostgreSQL local
make ensayo-whatsapp           # chequeo previo gratis
make ensayo-whatsapp ARGS="--tunel https://<tunel>"
```

El túnel https se registra en el panel de Meta como `https://<túnel>/webhook/whatsapp`. La allowlist E.164 del webhook propio se define con la misma variable `WHATSAPP_ALLOWLIST` y se ve en `/api/salud` (`allowlist_whatsapp`).

## 9. Plan de contingencia (en orden)

| Falla | Qué se hace |
|---|---|
| El canal de WhatsApp de OpenClaw no responde | Mostrar el bot por el webhook propio de Meta; explicar que es la misma API y el mismo agente |
| Meta no entrega (token vencido, número no registrado) | Chat web por QR (`make chat-web`, `make qr-chat-web`) y plan B grabado (`make demo-plan-b`) |
| El gateway no arranca | Mostrar `openclaw config validate` y la configuración versionada; explicar qué falló |
| Sin cuota del modelo | El respaldo `gemini-3.8-flash` entra solo; si tampoco, la respuesta guardada de la evaluación |

## 10. Lista de verificación del viernes

```bash
uv sync
make check                      # lint + pruebas + skills
make openclaw-check
openclaw gateway
openclaw channels status --probe
openclaw security audit
make ensayo-whatsapp
make qr-whatsapp ARGS="+57<numero-del-bot> --html --app"
git status                      # sin .env ni claves
```

Y desde el teléfono de un invitado real: escanear el QR, pedir una sede, pedir «¿qué sabes de mí?» y radicar un reclamo (que otra persona apruebe).

## Límites conocidos

- La plantilla se validó contra OpenClaw 2026.11.7 (esquema del ejecutable instalado localmente). Verificar en el equipo de la demo con `openclaw config validate`: si una clave cambió, se corrige la plantilla y sus pruebas en el mismo PR.
- La allowlist autentica el número, no a la persona.
- Con `WHATSAPP_ALLOWLIST=*` el canal es público: cualquiera que tenga el QR puede escribir y consumir cuota del modelo; solo lo frena el límite por teléfono (8 mensajes por minuto). Es una decisión de demo, no de producción.
- El número del bot es una cuenta de WhatsApp normal: si WhatsApp la bloquea por automatización, el QR deja de funcionar. Número dedicado y plan B (webhook de Meta o chat web).
- El servidor MCP `celsia` es de solo lectura; los reclamos y la memoria del cliente los atiende el agente de Celsia, al que OpenClaw llega por el puente `puente` (más una llamada al modelo: la respuesta tarda más que por el webhook).
- El puente se probó de punta a punta con la CLI de OpenClaw y un remitente de prueba (memoria por cliente incluida); falta el ensayo con el chip real (el plugin lee `ctx.requester.senderId`, que solo existe en mensajes que llegan por un canal).
- `openclaw security audit` no se automatiza; su salida se pega a mano con fecha.
