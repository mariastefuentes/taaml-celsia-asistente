// Plugin de OpenClaw «puente-celsia»: fija quién es el cliente en cada llamada al puente con el agente de Celsia.
//
// El modelo de OpenClaw decide *cuándo* llamar a la herramienta `atender_cliente_celsia`, pero no puede decidir *por quién*: antes de cada
// llamada este gancho reemplaza el argumento `telefono` con el número que OpenClaw tiene para el chat.
// Así un cliente no puede pedirle al bot los datos de otro («mi número es +57…») ni inyectar un teléfono ajeno.
//
// De dónde sale el número: `ctx.requester.senderId` si OpenClaw lo entrega. En las herramientas MCP, como este puente, OpenClaw 2026.11.6
// no lo entrega; ahí sale del nombre de la sesión (`ctx.sessionKey`), que arma OpenClaw y no el modelo:
// `agent:<agente>:whatsapp:direct:+57…` con `session.dmScope: "per-channel-peer"`. Cualquier otra sesión (terminal, tareas, grupos,
// otro canal o un identificador que no sea un número) queda bloqueada.
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

const HERRAMIENTA = "atender_cliente_celsia";
const CHAT_DIRECTO = /^agent:[^:]+:whatsapp:direct:(\+[0-9]{8,15})$/;

export function remitenteE164(requester) {
  const id = requester && typeof requester.senderId === "string" ? requester.senderId.trim() : "";
  const digitos = id.replace(/\D/g, "");
  return digitos.length >= 8 && digitos.length <= 15 ? `+${digitos}` : "";
}

export function remitenteDeLaSesion(sessionKey) {
  const hallado = typeof sessionKey === "string" ? CHAT_DIRECTO.exec(sessionKey) : null;
  return hallado ? hallado[1] : "";
}

export function fijarRemitente(event, ctx) {
  if (!event.toolName.endsWith(HERRAMIENTA)) {
    return undefined;
  }
  const telefono = ctx.requester ? remitenteE164(ctx.requester) : remitenteDeLaSesion(ctx.sessionKey);
  if (!telefono) {
    return { block: true, blockReason: "Sin remitente verificado: no se puede atender a un cliente." };
  }
  return { params: { ...event.params, telefono } };
}

export default definePluginEntry({
  id: "puente-celsia",
  name: "Puente Celsia",
  description: "Fija el teléfono del cliente con el remitente verificado del canal antes de llamar al agente de Celsia.",
  register(api) {
    api.on("before_tool_call", fijarRemitente, { priority: 100 });
  },
});
