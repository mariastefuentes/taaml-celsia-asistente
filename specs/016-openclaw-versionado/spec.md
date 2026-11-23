# Spec 016 — OpenClaw versionado y endurecido

- **Estado:** aprobada (retroactiva: la primera PR la implementa en parte).
- **Módulo:** 3 y sustentación final del 28 de noviembre de 2026.
- **Rúbrica que atiende:** 3.1 (gateway y configuración versionada, 8 %), 3.3 (workspace operativo, 7 %) y 4.2 (sandbox, `tools.deny`, `fs.workspaceOnly`, pairing/allowlist, 7 %).

## Problema

La configuración de OpenClaw existe y funciona (decisión D35), pero vive **solo en `~/.openclaw/openclaw.json`** del equipo de un integrante. La rúbrica pide configuración versionada, workspace con `SOUL.md`, `AGENTS.md`, `USER.md` y `MEMORY.md`, allowlist E.164 en el canal de WhatsApp y evidencia de `openclaw security audit`. Un revisor que abra el repositorio no puede comprobar nada de eso.

## Objetivo

1. Versionar una **plantilla saneada** del gateway: sin claves, con las variables resueltas al instalar.
2. Versionar el **workspace** (identidad, límites, memoria y bitácora) como archivos legibles.
3. Instalar con **un comando** (`make openclaw-instalar`) sin tocar el repositorio ni subir secretos.
4. Tener **pruebas** que fallen si alguien debilita el endurecimiento (por ejemplo, abrir el `bind` o quitar `tools.deny`).
5. Documentar la instalación, la vinculación del canal de WhatsApp y la auditoría.

## Fuera de alcance

- Cambiar el canal principal de WhatsApp: el webhook propio de Meta sigue siendo la vía de la demo; OpenClaw es el segundo cliente con las mismas herramientas por MCP.
- Automatizar `openclaw security audit`: se corre a mano en el equipo donde está instalado y su salida se guarda como evidencia.

## Criterios de aceptación

- [ ] `openclaw/openclaw.example.json` está versionado y no contiene secretos.
- [ ] `make openclaw-check` valida el endurecimiento sin escribir nada.
- [ ] `make openclaw-instalar` escribe `~/.openclaw/openclaw.json` y el workspace, con respaldo si ya existía.
- [ ] Las pruebas cubren: plantilla válida, variable faltante, allowlist que no es E.164, endurecimiento debilitado e instalación con y sin `--forzar`.
- [ ] `openclaw/README.md` y la guía de despliegue explican el proceso completo.
