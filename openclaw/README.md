# OpenClaw en el proyecto Celsia

Configuración **versionada y saneada** del gateway de OpenClaw que pide la rúbrica de la sustentación final (ítems 3.1, 3.3 y 4.2). Antes vivía solo en `~/.openclaw/openclaw.json`, en el equipo de un integrante; ahora la plantilla está en el repositorio y el archivo real se genera con un comando.

## Qué hay aquí

| Archivo | Para qué |
|---|---|
| `openclaw.example.json` | Plantilla de la configuración endurecida, validada contra OpenClaw 2026.11.7 (decisión D35): `bind: loopback`, token de gateway, modelo primario y respaldo, `tools.deny`, `fs.workspaceOnly`, sandbox (`mode: all`, `backend: docker`, `scope: agent`, `docker.image`), canal de WhatsApp encendido y público (`enabled: true`, `dmPolicy: open`, `allowFrom: ["*"]`, D54), `session.dmScope: per-channel-peer`, el servidor MCP `celsia` con sus diez herramientas (`toolFilter`) y el puente `puente` con el plugin `puente-celsia` (D52) |
| `workspace/` | Identidad y memoria legibles y editables: `SOUL.md`, `AGENTS.md`, `USER.md`, `MEMORY.md` y la bitácora diaria |

## Instalación

```bash
# 1. Completa las variables en .env (no las subas con valores reales)
#    OPENCLAW_GATEWAY_TOKEN=...   WHATSAPP_ALLOWLIST=*   REPO_CELSIA=C:/ruta/al/repo
#    (con «*» el canal queda abierto al auditorio; con números, solo esos pasan)
#    La clave del modelo va aparte, en ~/.openclaw/.env: DEEPSEEK_API_KEY=...

# 2. Valida la plantilla sin escribir nada
make openclaw-check

# 3. Escribe ~/.openclaw/openclaw.json y copia el workspace
make openclaw-instalar
#    Si ya había una configuración: make openclaw-instalar ARGS="--forzar" (deja un .bak)

# 4. Con el Gateway apagado, registra el MCP y comprueba el canal
openclaw channels login --channel whatsapp   # QR: escanéalo desde el celular del número dedicado
openclaw gateway
openclaw channels status --probe
openclaw security audit

# 5. QR para el auditorio (número del bot, no el personal)
make qr-whatsapp ARGS="+57<numero-del-bot> --html"
```

## Skill del proyecto (D55)

`workspace/skills/atencion-whatsapp-celsia/SKILL.md` describe cómo atender cada mensaje de WhatsApp con el puente. La plantilla solo deja ver las skills del proyecto (`agents.defaults.skills`) y permite leerlas con `skills_read`, sin abrir el sistema de archivos (`group:fs` sigue denegado). `make openclaw-instalar` la copia con el workspace. Para comprobarlo en el equipo de la demo:

```bash
openclaw skills list --agent main
```

## Qué se comprueba en las pruebas

`tests/test_openclaw.py` no valida el esquema de OpenClaw (para eso está `openclaw config validate` en el equipo donde está instalado). Comprueba lo que la rúbrica exige y el equipo decidió:

- `gateway.bind` en `loopback` y token resuelto desde el entorno.
- `tools.deny` con los grupos de automatización, ejecución y sistema de archivos, y `sessions_spawn`.
- `tools.fs.workspaceOnly` en `true` y `tools.exec.mode` en `deny`.
- Sandbox en modo `all` con backend `docker`, scope `agent`, `workspaceAccess: none` y el MCP `celsia__*` permitido dentro.
- `channels.whatsapp` encendido y abierto (`enabled: true`, `dmPolicy: open`, `allowFrom: ["*"]`) para el auditorio, y `WHATSAPP_ALLOWLIST` en `*` o con números E.164.
- `session.dmScope: per-channel-peer` y `tools.sessions.visibility: self`: cada número tiene su conversación y el chat de un cliente no puede leer ni escribir en las de otros, aunque el sandbox no esté (D70).
- `commands.allowFrom` en `{"*": []}` y `commands.restart` en `false`: las órdenes internas (`/status`, `/model`, `/new`) no responden en el chat (D72).
- Cada modelo de los agentes declarado en `models.providers`, con la clave como referencia al entorno.
- El servidor MCP `celsia` con sus diez herramientas y el puente `puente` (`atender_cliente_celsia`), con el plugin `puente-celsia` activo y `toolSearch` apagado.
- La skill del proyecto es válida, es la única visible, `skills_read` está permitido y el instalador la copia (`tests/test_openclaw_workspace.py`).
- Ningún secreto en la plantilla.

## Límites

- La plantilla se validó contra el esquema de OpenClaw 2026.11.7 (el ejecutable instalado localmente). Verificar en el equipo de la demo con `openclaw config validate`: si una clave cambió, se corrige la plantilla y sus pruebas en el mismo PR.
- El modelo primario es `deepseek/deepseek-flash` y la plantilla declara el proveedor DeepSeek; si falla, responde el respaldo `deepseek/deepseek-v4-pro` (misma clave, D68). La clave (`DEEPSEEK_API_KEY`) va en `~/.openclaw/.env` o en el entorno del Gateway, nunca aquí ni en el `.env` del repositorio (OpenClaw la ignora desde ahí).
- La bitácora diaria del workspace se escribe a mano; no se versiona lo que diga de clientes reales.
