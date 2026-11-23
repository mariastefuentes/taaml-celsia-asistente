# OpenClaw en el proyecto Celsia

Configuración **versionada y saneada** del gateway de OpenClaw que pide la rúbrica de la sustentación final (ítems 3.1, 3.3 y 4.2). Antes vivía solo en `~/.openclaw/openclaw.json`, en el equipo de un integrante; ahora la plantilla está en el repositorio y el archivo real se genera con un comando.

## Qué hay aquí

| Archivo | Para qué |
|---|---|
| `openclaw.example.json` | Plantilla de la configuración endurecida (decisión D35): `bind: loopback`, token de gateway, modelo primario y respaldo, `tools.deny`, `fs.workspaceOnly`, sandbox Docker, allowlist E.164 del canal de WhatsApp y el servidor MCP `celsia` con sus diez herramientas |
| `workspace/` | Identidad y memoria legibles y editables: `SOUL.md`, `AGENTS.md`, `USER.md`, `MEMORY.md` y la bitácora diaria |

## Instalación

```bash
# 1. Completa las variables en .env (no las subas con valores reales)
#    OPENCLAW_GATEWAY_TOKEN=...   WHATSAPP_ALLOWLIST=+57...,+57...   REPO_CELSIA=C:/ruta/al/repo

# 2. Valida la plantilla sin escribir nada
make openclaw-check

# 3. Escribe ~/.openclaw/openclaw.json y copia el workspace
make openclaw-instalar
#    Si ya había una configuración: make openclaw-instalar ARGS="--forzar" (deja un .bak)

# 4. Con el Gateway apagado, registra el MCP y comprueba el canal
openclaw gateway
openclaw channels status --probe
openclaw security audit
```

## Qué se comprueba en las pruebas

`tests/test_openclaw.py` no valida el esquema de OpenClaw (para eso está `openclaw config validate` en el equipo donde está instalado). Comprueba lo que la rúbrica exige y el equipo decidió:

- `gateway.bind` en `loopback` y token resuelto desde el entorno.
- `tools.deny` con los grupos de automatización, ejecución y sistema de archivos, y `sessions_spawn`.
- `tools.fs.workspaceOnly` en `true` y `tools.exec.mode` en `deny`.
- Permisos elevados y navegador apagados.
- Sandbox en modo `all` con `workspaceAccess: none` y el MCP `celsia__*` permitido dentro.
- Allowlist de WhatsApp con números en E.164.
- Ningún secreto en la plantilla.

## Límites

- La plantilla salió de la configuración que funcionó en D35, pero **cada versión de OpenClaw puede cambiar nombres de claves**: después de instalar, correr `openclaw config validate` y `openclaw security audit` en el equipo de la demo. Si una clave cambió, se actualiza la plantilla en el mismo PR.
- El modelo primario es `deepseek-flash` con `gemini-3.8-flash` de respaldo, como el agente. La clave del proveedor vive en el entorno, nunca aquí.
- La bitácora diaria del workspace se escribe a mano; no se versiona lo que diga de clientes reales.
