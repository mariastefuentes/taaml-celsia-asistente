# Guía de despliegue de OpenClaw (sustentación final)

Esta guía lleva el asistente de Celsia al gateway de OpenClaw que pide la rúbrica del 28 de noviembre de 2026: **3.1** (gateway con configuración versionada), **3.2** (WhatsApp real con allowlist E.164), **3.3** (workspace) y **4.2** (sandbox y auditoría). **La demo va solo por este canal** (QR de OpenClaw, D56). El webhook propio con la API de Meta sigue en el código, pero no se usa.

> **Estado.** La configuración se versionó el 23/11/2026 (`openclaw/openclaw.example.json`, decisiones D47 y D48) a partir de la que funcionó en D35. Antes de la demo hay que ejecutar en el equipo del bot los pasos 3, 6 y 7 y corregir lo que cambie de nombre entre versiones.

## 0. Qué se necesita

| Pieza | Para qué |
|---|---|
| OpenClaw instalado y en el `PATH` | Gateway y canales |
| Docker | Imagen del sandbox (`openclaw-sandbox:trixie-slim`) |
| `uv` y este repositorio | El servidor MCP `celsia` corre con `uv run` |
| Número dedicado para el bot | Chip prepago o eSIM de voz/SMS en un celular de repuesto (nunca el personal de un integrante); ver la sección 6 |
| Clave del proveedor del modelo | `DEEPSEEK_API_KEY`, para `deepseek/deepseek-flash` (la plantilla declara el proveedor; respaldo apagado) |

## 1. Variables (en `.env`, nunca en el repositorio)

```text
OPENCLAW_GATEWAY_TOKEN=<cadena larga y aleatoria>
CHAT_TOKEN=<otra cadena larga: la comparten la API y el puente>
APROBADOR_TOKEN=<la clave de quien aprueba en el panel>
OPENCLAW_AVISOS=1
WHATSAPP_ALLOWLIST=*
REPO_CELSIA=C:/ruta/absoluta/a/taaml-celsia-asistente
```

`REPO_CELSIA` es la ruta donde OpenClaw lanzará `uv run python -m taaml.servidor_mcp`; tiene que ser la del equipo que hace la demo, no la de un compañero. `WHATSAPP_ALLOWLIST=*` deja el canal abierto al auditorio (D54); si prefieres una lista cerrada, escribe los números en E.164 separados por comas, pero entonces los invitados que no estén en ella recibirán «Este número no está autorizado».

**La clave del modelo va aparte.** El Gateway no la toma del `.env` del repositorio: OpenClaw ignora las claves de proveedores que vengan de la carpeta desde la que se arranca. Antes de instalar, escríbela en `~/.openclaw/.env` (en Windows, `%USERPROFILE%\.openclaw\.env`):

```text
DEEPSEEK_API_KEY=<la clave de DeepSeek>
```

La plantilla declara el proveedor `deepseek` y solo nombra esa variable (`models.providers.deepseek.apiKey`), así que la clave no queda escrita en `openclaw.json`. Sin el proveedor declarado, y sin el complemento oficial de DeepSeek, el bot responde «model not found».

## 2. Instalar configuración y workspace

```bash
make openclaw-check        # valida endurecimiento, allowlist E.164 y ausencia de secretos; no escribe
make openclaw-instalar     # escribe ~/.openclaw/openclaw.json y copia el workspace
```

Si ya había una configuración, `make openclaw-instalar ARGS="--forzar"` la **reemplaza entera** (se pierde lo que se hubiera agregado a mano, como otros modelos o perfiles de clave) y deja un `openclaw.json.bak` al lado. Lo instalado incluye:

- `bind: loopback` y token de gateway.
- `tools.deny`: `group:automation`, `group:runtime`, `group:fs`, `sessions_spawn`.
- `tools.fs.workspaceOnly: true` y `tools.exec.mode: deny`.
- Permisos elevados y navegador apagados.
- Sandbox Docker en modo `all` con `workspaceAccess: none`, permitiendo dentro `celsia__*`, `puente__*` y `skills_read`, que solo lee la skill del proyecto (D55).
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

6. Probar desde dos teléfonos que **no** sean del equipo: una pregunta de sedes (tool de tabla), un «¿qué sabes de mí?» (memoria) y un reclamo que otra persona aprueba en el panel (ver «Aprobar en el panel»). El panel debe mostrar la herramienta elegida.

### El puente: las 20 herramientas por el canal de OpenClaw (D52)

El agente de OpenClaw solo ve las diez herramientas de solo lectura del MCP `celsia`. Para que **lo que se escribe por el WhatsApp de OpenClaw lo atienda el agente completo** (20 herramientas, memoria por cliente, reclamos con aprobación humana), la plantilla conecta un segundo MCP, `puente`, con **una sola herramienta**: `atender_cliente_celsia(mensaje, telefono)`, que llama a `POST /chat` de la API.

```
cliente → WhatsApp (QR) → OpenClaw → atender_cliente_celsia → POST /chat → agente de Celsia (20 herramientas) → respuesta
```

- **Quién escribe lo fija OpenClaw, no el modelo.** OpenClaw no manda el remitente a los MCP por stdio (se comprobó con un servidor espejo), así que el plugin `openclaw/plugins/puente-celsia.js` usa el gancho `before_tool_call` y reemplaza `telefono` con el número que OpenClaw tiene para el chat. Como a las herramientas MCP no les entrega el remitente (`ctx.requester`, comprobado en 2026.11.6), lo toma del nombre del chat directo (`agent:main:whatsapp:direct:+57…`), por eso `session.dmScope` debe seguir en `per-channel-peer`. En cualquier otra sesión (terminal, grupos, identificadores sin número) bloquea la llamada. El puente además exige que el número esté en `WHATSAPP_ALLOWLIST`.
- **Requisitos:** la API encendida (`make api`), `CHAT_TOKEN` igual en `.env` y en el entorno de OpenClaw, y el plugin del canal instalado (`openclaw plugins install npm:@openclaw/whatsapp`).
- **Instrucciones al modelo:** `workspace/AGENTS.md` (sección «Canal de WhatsApp») manda llamar la herramienta en cada mensaje y devolver su texto sin cambios; `tools.toolSearch: false` deja el esquema a la vista.
- **Si falla el puente**, responde la frase de contingencia con la línea 01 8000 112 115 y la demo sigue por el chat web.

### Aprobar en el panel (D56)

Radicar un reclamo, cancelarlo o reportar un daño deja la conversación en pausa hasta que una persona decide:

1. En el computador del bot, abrir `http://127.0.0.1:8000/panel`, escribir la clave `APROBADOR_TOKEN` y pulsar «Ver».
2. Arriba aparece **Por aprobar**, con lo que pidió el cliente y sin su teléfono. Pulsar **Aprobar** o **Rechazar**.
3. La API le escribe el resultado al cliente con `openclaw message send`. Necesita `OPENCLAW_AVISOS=1`, `CHAT_TOKEN` y el gateway encendido; `/api/salud` debe decir `"avisos_openclaw": true`.
4. Si el envío falla, el panel lo dice y el cliente recibe el resultado junto con la respuesta a su siguiente mensaje.

Antes de la demo, probar el envío con un teléfono del equipo. La primera orden solo muestra lo que se mandaría; la segunda lo manda:

```powershell
openclaw message send --channel whatsapp --target "+57<numero-de-prueba>" --message "Prueba de aviso" --dry-run
```

```powershell
openclaw message send --channel whatsapp --target "+57<numero-de-prueba>" --message "Prueba de aviso"
```

La lista de pendientes vive en memoria: si la API se reinicia, cada pendiente vuelve a aparecer cuando su cliente escribe de nuevo.

### El número propio del bot (D54)

El canal de OpenClaw se vincula como **dispositivo vinculado** de una cuenta de WhatsApp: el bot responde desde ese número. Por eso hace falta un número dedicado, no el personal de un integrante:

1. Chip prepago o **eSIM de voz/SMS** (las de solo datos no reciben el código) en un celular de repuesto.
2. **La cuenta de WhatsApp vive en ese celular**, no en el computador: instalar WhatsApp, registrar el número (el código llega por SMS o llamada al chip nuevo) y poner el perfil «Asistente Celsia» (foto y descripción). Los invitados verán ese nombre.
3. Con ese celular ya con WhatsApp, ejecutar en el equipo de la demo `openclaw channels login --channel whatsapp`. OpenClaw imprime un **QR de vinculación**; escanearlo **desde ese mismo celular** en WhatsApp → Dispositivos vinculados → Vincular un dispositivo. No se escanea desde el celular de un invitado.
4. El celular puede quedar apagado durante la demo; WhatsApp cierra la sesión del dispositivo vinculado tras unos 14 días sin actividad del teléfono, así que hay que reconectarlo cada dos semanas.

**Los dos QR no son el mismo.** El de `openclaw channels login` se escanea **una sola vez**, desde el celular del chip, para que OpenClaw quede vinculado. El de `make qr-whatsapp` es el que se proyecta al auditorio: cualquier invitado lo escanea con la cámara y abre el chat con el bot. Si el QR de invitados se escaneara desde el celular del chip, no vincularía nada: solo abriría un chat del bot consigo mismo.

**Riesgo.** La automatización de OpenClaw no es oficial: un uso intensivo puede hacer que WhatsApp banee el número. Se usa un número dedicado; el respaldo es el chat web y el plan B grabado.

**Si el canal de OpenClaw no queda listo** no hay otro WhatsApp: la demo sigue por el chat web y el plan B grabado (apartado 9).

## 7. Evidencia para el repositorio

Guardar en `docs/auditoria_openclaw.md` la salida real de:

```text
openclaw security audit
openclaw channels status --probe
```

con fecha, equipo y quién lo corrió. **No se inventa la salida**: si algo queda en amarillo, se documenta y se explica en la sustentación.

## 8. Webhook propio de Meta (no se usa en la demo)

El código y sus pruebas siguen en el repositorio (`/webhook/whatsapp`, `src/taaml/whatsapp.py`), pero la demostración no pasa por Meta (D56): no hace falta cuenta, token ni túnel de Meta. Los pasos para activarlo están en el README.

## 9. Plan de contingencia (en orden)

| Falla | Qué se hace |
|---|---|
| El canal de WhatsApp de OpenClaw no responde | `openclaw channels status --probe`; si no vuelve, chat web por QR (`make chat-web`, `make qr-chat-web`) |
| El chat web tampoco abre (sin red o sin túnel) | Plan B grabado (`make demo-plan-b`) |
| Se aprobó un reclamo y la respuesta no llega | Pedir a la persona que escriba otra vez y pregunte por su reclamo (si el panel dijo que no se pudo enviar, el resultado le llega con esa respuesta) |
| El gateway no arranca | Mostrar `openclaw config validate` y la configuración versionada; explicar qué falló |
| Sin cuota del modelo | El agente de la API usa su respaldo (`gemini-3.8-flash`, luego `deepseek-v4-pro`); el modelo de OpenClaw no tiene respaldo |

## 10. Lista de verificación del viernes

```bash
uv sync
make check                      # lint + pruebas + skills
make openclaw-check
openclaw gateway
openclaw channels status --probe
openclaw security audit
Invoke-RestMethod http://127.0.0.1:8000/api/salud   # almacen qdrant y avisos_openclaw true
make qr-whatsapp ARGS="+57<numero-del-bot> --html --app"
git status                      # sin .env ni claves
```

Y desde el teléfono de un invitado real: escanear el QR, pedir una sede, pedir «¿qué sabes de mí?» y radicar un reclamo (que otra persona apruebe en el panel y llegue al WhatsApp).

## Límites conocidos

- La plantilla se validó contra OpenClaw 2026.11.7 (esquema del ejecutable instalado localmente). Verificar en el equipo de la demo con `openclaw config validate`: si una clave cambió, se corrige la plantilla y sus pruebas en el mismo PR.
- La allowlist autentica el número, no a la persona.
- Con `WHATSAPP_ALLOWLIST=*` el canal es público: cualquiera que tenga el QR puede escribir y consumir cuota del modelo; solo lo frena el límite por teléfono (8 mensajes por minuto). Es una decisión de demo, no de producción.
- El número del bot es una cuenta de WhatsApp normal: si WhatsApp la bloquea por automatización, el QR deja de funcionar. Número dedicado y respaldo con el chat web o el plan B grabado.
- El servidor MCP `celsia` es de solo lectura; los reclamos y la memoria del cliente los atiende el agente de Celsia, al que OpenClaw llega por el puente `puente` (más una llamada al modelo: la respuesta tarda más que con un solo modelo).
- El puente se probó con OpenClaw 2026.11.6, su sandbox, un modelo falso y un canal de Telegram simulado (D52). **Falta el ensayo con WhatsApp y el chip real:** enviar un mensaje desde otro teléfono y comprobar que la terminal de la API muestra `POST /chat` con `200 OK`.
- El aviso de la aprobación (`openclaw message send`) no se ha probado con el canal real vinculado.
- `openclaw security audit` no se automatiza; su salida se pega a mano con fecha.
