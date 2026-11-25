"""Configuración de OpenClaw versionada y saneada, e instalación en la carpeta del usuario.

La plantilla `openclaw/openclaw.example.json` se resolvió desde la configuración endurecida de la decisión D35. Este módulo no
ejecuta OpenClaw: sustituye las variables de entorno, valida el endurecimiento y, si se le pide, escribe la configuración y el
workspace en `~/.openclaw`. La validación de esquema la hace `openclaw config validate` en el equipo donde esté instalado.
"""

import json
import os
import re
from pathlib import Path

from taaml.whatsapp import LISTA_ABIERTA

RAIZ = Path(__file__).resolve().parents[2]
PLANTILLA = RAIZ / "openclaw" / "openclaw.example.json"
WORKSPACE = RAIZ / "openclaw" / "workspace"

E164 = re.compile(r"^\+[1-9]\d{7,14}$")
VARIABLES = ("OPENCLAW_GATEWAY_TOKEN", "WHATSAPP_ALLOWLIST", "REPO_CELSIA")


class ConfiguracionInvalida(ValueError):
    """La plantilla no cumple el endurecimiento que exige la rúbrica o le falta una variable."""


def _resolver(texto: str, entorno: dict[str, str] | None = None) -> str:
    """Sustituye `${VARIABLE}` por su valor. Falla si falta: una configuración a medias es peor que ninguna.

    Los valores que empiezan por `[` van sin comillas (arrays JSON, por ejemplo `allowFrom`); el resto va dentro de
    la comilla que el template puso alrededor del `${...}`.
    """
    entorno = {**os.environ, **(entorno or {})}
    faltan = [v for v in VARIABLES if f"${{{v}}}" in texto and not entorno.get(v)]

    def reemplazo(match: re.Match) -> str:
        nombre = match.group(1)
        if nombre not in entorno:
            return match.group(0)
        valor = entorno[nombre]
        return valor if valor.lstrip().startswith("[") else json.dumps(valor)[1:-1]

    resuelto = re.sub(r"\$\{([A-Z0-9_]+)\}", reemplazo, texto)
    if faltan:
        raise ConfiguracionInvalida(f"Faltan variables de entorno: {', '.join(faltan)}")
    return resuelto


def configuracion(entorno: dict[str, str] | None = None, plantilla: Path | None = None) -> dict:
    """Devuelve la configuración como diccionario, con las variables ya sustituidas."""
    texto = _resolver((plantilla or PLANTILLA).read_text(encoding="utf-8"), entorno)
    return json.loads(texto)


def problemas(config: dict) -> list[str]:
    """Lista lo que falta para el endurecimiento de la rúbrica en OpenClaw 2026.11.7: sandbox, deny, workspaceOnly, allowlist E.164.

    No es un validador del esquema de OpenClaw (eso lo hace la herramienta): comprueba las decisiones que el equipo tomó y que
    la auditoría debe poder mostrar.
    """
    fallos: list[str] = []
    gateway = config.get("gateway", {})
    if gateway.get("mode") != "local":
        fallos.append("gateway.mode debe ser «local»")
    if gateway.get("bind") != "loopback":
        fallos.append("gateway.bind debe ser «loopback»")
    token = gateway.get("auth", {}).get("token", "")
    if not token or token.startswith("${"):
        fallos.append("gateway.auth.token sin resolver")
    herramientas = config.get("tools", {})
    for grupo in ("group:automation", "group:runtime", "group:fs", "sessions_spawn"):
        if grupo not in herramientas.get("deny", []):
            fallos.append(f"tools.deny debe incluir «{grupo}»")
    if herramientas.get("fs", {}).get("workspaceOnly") is not True:
        fallos.append("tools.fs.workspaceOnly debe ser true")
    if herramientas.get("exec", {}).get("mode") != "deny":
        fallos.append("tools.exec.mode debe ser «deny»")
    if herramientas.get("elevated", {}).get("enabled") is not False:
        fallos.append("tools.elevated.enabled debe ser false")
    if not config.get("agents", {}).get("entries", {}):
        fallos.append("agents.entries debe contener al menos un agente configurado (por ejemplo «main»)")
    if not config.get("plugins", {}).get("entries", {}).get("whatsapp", {}).get("enabled"):
        fallos.append("plugins.entries.whatsapp.enabled debe ser true")
    if config.get("env", {}).get("shellEnv", {}).get("enabled") is not True:
        fallos.append("env.shellEnv.enabled debe ser true")
    sandbox = config.get("agents", {}).get("defaults", {}).get("sandbox", {})
    if sandbox.get("mode") != "all":
        fallos.append("el sandbox debe ser mode «all»")
    if sandbox.get("backend") != "docker":
        fallos.append("el sandbox debe ser backend «docker»")
    if sandbox.get("scope") not in ("session", "agent", "shared"):
        fallos.append("el sandbox scope debe ser session, agent o shared")
    if sandbox.get("workspaceAccess") != "none":
        fallos.append("el sandbox debe ser workspaceAccess «none»")
    if not sandbox.get("docker", {}).get("image"):
        fallos.append("el sandbox debe tener una imagen en docker.image")
    if "celsia__*" not in herramientas.get("sandbox", {}).get("tools", {}).get("alsoAllow", []):
        fallos.append("el sandbox debe permitir el servidor MCP «celsia__*»")
    whatsapp = config.get("channels", {}).get("whatsapp", {})
    if whatsapp.get("enabled") is not True:
        fallos.append("channels.whatsapp.enabled debe ser true: el canal público de la demo es WhatsApp")
    dm_policy = whatsapp.get("dmPolicy")
    if dm_policy not in ("allowlist", "open"):
        fallos.append("channels.whatsapp.dmPolicy debe ser «allowlist» o «open»")
    allowlist = whatsapp.get("allowFrom", [])
    if not allowlist:
        fallos.append("channels.whatsapp.allowFrom está vacía")
    if dm_policy == "open" and "*" not in allowlist:
        fallos.append("con dmPolicy «open», allowFrom debe contener «*»")
    if dm_policy == "allowlist":
        for numero in allowlist:
            if not E164.match(str(numero).strip()):
                fallos.append(f"«{numero}» no está en formato E.164 (+57…)")
    allowlist_puente = str(
        config.get("mcp", {}).get("servers", {}).get("puente", {}).get("env", {}).get("WHATSAPP_ALLOWLIST", "")
    ).strip()
    if allowlist_puente and allowlist_puente != LISTA_ABIERTA:
        for numero in re.split(r"[,;]+", allowlist_puente):
            if numero.strip() and not E164.match(numero.strip()):
                fallos.append(f"WHATSAPP_ALLOWLIST del puente: «{numero.strip()}» no está en formato E.164 (+57…)")
    if not config.get("mcp", {}).get("servers", {}).get("celsia"):
        fallos.append("falta el servidor MCP propio «celsia»")
    if not config.get("mcp", {}).get("servers", {}).get("puente"):
        fallos.append("falta el servidor MCP «puente» (lleva los mensajes al agente de Celsia con sus 20 herramientas)")
    if "puente__*" not in herramientas.get("sandbox", {}).get("tools", {}).get("alsoAllow", []):
        fallos.append("el sandbox debe permitir el servidor MCP «puente__*»")
    if config.get("plugins", {}).get("entries", {}).get("puente-celsia", {}).get("enabled") is not True:
        fallos.append("falta el plugin «puente-celsia» (fija el teléfono del cliente con el remitente verificado)")
    if herramientas.get("toolSearch") is not False:
        fallos.append("tools.toolSearch debe ser false: el modelo tiene que ver la herramienta del puente sin buscarla")
    return fallos


def instalar(destino: Path, entorno: dict[str, str] | None = None, forzar: bool = False) -> list[Path]:
    """Escribe la configuración y el workspace en `destino` (~/.openclaw) y devuelve los archivos escritos.

    No sobrescribe una configuración existente salvo con `forzar`; en ese caso deja un respaldo `.bak` al lado.
    """
    config = configuracion(entorno)
    fallos = problemas(config)
    if fallos:
        raise ConfiguracionInvalida("; ".join(fallos))
    destino.mkdir(parents=True, exist_ok=True)
    archivo = destino / "openclaw.json"
    escritos: list[Path] = []
    if archivo.exists() and not forzar:
        raise ConfiguracionInvalida(f"Ya existe {archivo}; usa --forzar para reemplazarla (se guarda un respaldo)")
    if archivo.exists():
        respaldo = archivo.with_suffix(".json.bak")
        respaldo.write_text(archivo.read_text(encoding="utf-8"), encoding="utf-8")
        escritos.append(respaldo)
    archivo.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    escritos.append(archivo)
    carpeta = destino / "workspace"
    carpeta.mkdir(parents=True, exist_ok=True)
    for origen in sorted(WORKSPACE.rglob("*.md")):
        copia = carpeta / origen.relative_to(WORKSPACE)
        copia.parent.mkdir(parents=True, exist_ok=True)
        copia.write_text(origen.read_text(encoding="utf-8"), encoding="utf-8")
        escritos.append(copia)
    return escritos
