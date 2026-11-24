# Guía de despliegue de OpenClaw (sustentación final)

Esta guía lleva el asistente de Celsia al gateway de OpenClaw que pide la rúbrica del 28 de noviembre de 2026: **3.1** (gateway con configuración versionada), **3.2** (WhatsApp real con allowlist E.164), **3.3** (workspace) y **4.2** (sandbox y auditoría). La alternativa —el webhook propio con la API Cloud de Meta— sigue siendo la vía principal de la demo y se describe al final.

> **Estado.** La configuración se versionó el 23/11/2026 (`openclaw/openclaw.example.json`, decisiones D47 y D48) a partir de la que funcionó en D35. **No se validó en el equipo donde corre esta guía**: aquí no hay OpenClaw instalado. Antes de la demo hay que ejecutar los pasos 3, 6 y 7 y corregir lo que cambie de nombre entre versiones.

## 0. Qué se necesita

| Pieza | Para qué |
|---|---|
| OpenClaw instalado y en el `PATH` | Gateway y canales |
| Docker | Imagen del sandbox (`openclaw-sandbox:trixie-slim`) |
| `uv` y este repositorio | El servidor MCP `celsia` corre con `uv run` |
| Cuenta de Meta con la app de WhatsApp | Canal de WhatsApp y número vinculado |
| Clave del proveedor del modelo | `deepseek-flash` primario, `gemini-3.8-flash` de respaldo |

## 1. Variables (en `.env`, nunca en el repositorio)

```text
OPENCLAW_GATEWAY_TOKEN=<cadena larga y aleatoria>
WHATSAPP_ALLOWLIST=+573001112233,+573104445566
REPO_CELSIA=C:/ruta/absoluta/a/taaml-celsia-asistente
```

`REPO_CELSIA` es la ruta donde OpenClaw lanzará `uv run python -m taaml.servidor_mcp`; tiene que ser la del equipo que hace la demo, no la de un compañero.

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

4. Definir la allowlist solo con los teléfonos de los invitados y del equipo:

```text
WHATSAPP_ALLOWLIST=+57...,+57...
```

5. Probar desde un teléfono autorizado: una pregunta de sedes (tool de tabla) y un «¿qué sabes de mí?» (memoria). La traza debe mostrar la herramienta elegida.

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
git status                      # sin .env ni claves
```

Y desde el teléfono de un invitado real: pedir una sede, pedir «¿qué sabes de mí?» y radicar un reclamo (que otra persona apruebe).

## Límites conocidos

- La plantilla se validó contra OpenClaw 2026.11.7 (esquema del ejecutable instalado localmente). Verificar en el equipo de la demo con `openclaw config validate`: si una clave cambió, se corrige la plantilla y sus pruebas en el mismo PR.
- La allowlist autentica el número, no a la persona.
- El servidor MCP es de solo lectura: los reclamos y la memoria solo existen en el agente del webhook propio, no en OpenClaw.
- `openclaw security audit` no se automatiza; su salida se pega a mano con fecha.
