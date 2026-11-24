// Plugin de OpenClaw «puente-celsia»: fija quién es el cliente en cada llamada al puente con el agente de Celsia.
//
// El modelo de OpenClaw decide *cuándo* llamar a la herramienta `atender_cliente_celsia`, pero no puede decidir *por quién*: antes de cada
// llamada este gancho reemplaza el argumento `telefono` con el remitente que OpenClaw verificó en el canal (`ctx.requester.senderId`).
// Así un cliente no puede pedirle al bot los datos de otro («mi número es +57…») ni inyectar un teléfono ajeno. Sin remitente
// verificado (ejecuciones del sistema, cron, etc.) la llamada se bloquea.
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

const HERRAMIENTA = "atender_cliente_celsia";

export function remitenteE164(requester) {
  const id = requester && typeof requester.senderId === "string" ? requester.senderId.trim() : "";
  const digitos = id.replace(/\D/g, "");
  return digitos.length >= 8 && digitos.length <= 15 ? `+${digitos}` : "";
}

export function fijarRemitente(event, ctx) {
  if (!event.toolName.endsWith(HERRAMIENTA)) {
    return undefined;
  }
  const telefono = remitenteE164(ctx.requester);
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
