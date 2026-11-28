// Plugin de OpenClaw Â«puente-celsiaÂ»: fija quiÃ©n es el cliente en cada llamada al puente con el agente de Celsia.
//
// El modelo de OpenClaw decide *cuÃ¡ndo* llamar a la herramienta `atender_cliente_celsia`, pero no puede decidir *por quiÃ©n*: antes de cada
// llamada este gancho reemplaza el argumento `telefono` con el nÃºmero que OpenClaw tiene para el chat.
// AsÃ­ un cliente no puede pedirle al bot los datos de otro (Â«mi nÃºmero es +57â€¦Â») ni inyectar un telÃ©fono ajeno.
//
// De dÃ³nde sale el nÃºmero: `ctx.requester.senderId` si OpenClaw lo entrega. En las herramientas MCP, como este puente, OpenClaw 2026.11.6
// no lo entrega; ahÃ­ sale del nombre de la sesiÃ³n (`ctx.sessionKey`), que arma OpenClaw y no el modelo:
// `agent:<agente>:whatsapp:direct:+57â€¦` con `session.dmScope: "per-channel-peer"`. Cualquier otra sesiÃ³n (terminal, tareas, grupos,
// otro canal o un identificador que no sea un nÃºmero) queda bloqueada.
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

const HERRAMIENTA = "atender_cliente_celsia";
const CHAT_DIRECTO = /^agent:[^:]+:whatsapp:direct:(\+[0-9]{8,15})$/;
const pendientesWhatsApp = new Map();

function apiCelsia() {
  return (process.env.CELSIA_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
}

async function registrarActividadRealWhatsApp(pendiente, respuesta, evento) {
  // No se registra por el modelo ni por `atender_cliente_celsia`: si esa herramienta no se usa, esto sigue guardando el turno.
  // No se imprimen nÃºmeros, tokens ni errores internos; el telÃ©fono solo viaja al endpoint local y Celsia lo convierte en hash.
  try {
    const headers = { "Content-Type": "application/json" };
    if (process.env.CHAT_TOKEN) headers["X-Api-Key"] = process.env.CHAT_TOKEN;
    const r = await fetch(apiCelsia() + "/api/actividad/whatsapp", {
      method: "POST",
      headers,
      body: JSON.stringify({
        telefono: pendiente.telefono,
        mensaje: pendiente.mensaje,
        respuesta,
        evento,
        turno_id: pendiente.id || undefined,
      }),
      signal: AbortSignal.timeout(10000),
    });
    if (!r.ok) { console.warn(`[puente-celsia] ${evento} POST /api/actividad/whatsapp HTTP ${r.status}`); return; }
    console.info(`[puente-celsia] ${evento} registrado; POST /api/actividad/whatsapp HTTP ${r.status}`); // sin mensaje, telÃ©fono ni token
  } catch { console.warn(`[puente-celsia] ${evento} no se pudo enviar /api/actividad/whatsapp`); }
}

function claveSesion(ctx, event) {
  return ctx.sessionKey || event.sessionKey || ctx.conversationId || event.conversationId || "";
}

function remitenteDeEventoWhatsApp(event, ctx) {
  const metadata = event.metadata || {};
  const remitente = event.senderE164 || metadata.senderE164 || event.senderId || metadata.senderId || event.from || ctx.senderId;
  const directo = remitenteE164({ senderId: remitente });
  if (directo) return directo;
  return remitenteDeLaSesion(claveSesion(ctx, event));
}

export async function registrarEntradaWhatsApp(event = {}, ctx = {}) {
  const clave = claveSesion(ctx, event);
  const canales = [ctx.channelId, event.channelId]
    .filter((v) => typeof v === "string")
    .map((v) => v.trim().toLowerCase());

  const sesionWhatsApp = /(?:^|:)whatsapp(?=:|$)/i.test(clave);
  const esWhatsApp = canales.includes("whatsapp") || sesionWhatsApp;

  console.info("[puente-celsia] message_received:", JSON.stringify({
    canalContexto: ctx.channelId || "",
    canalEvento: event.channelId || "",
    sesionWhatsApp,
    tieneContenido: typeof event.content === "string" && event.content.trim().length > 0
  }));

  if (!esWhatsApp) return;

  if (typeof event.content !== "string" || !event.content.trim()) {
    console.warn("[puente-celsia] WhatsApp recibido sin contenido de texto");
    return;
  }

  const telefono = remitenteDeEventoWhatsApp(event, ctx);
  if (!telefono) {
    console.warn("[puente-celsia] WhatsApp recibido sin remitente verificable");
    return;
  }

  const id = typeof (event.messageId || ctx.messageId) === "string"
    ? String(event.messageId || ctx.messageId).trim()
    : "";

  const pendiente = { telefono, mensaje: event.content, id };
  pendientesWhatsApp.set(clave || telefono, pendiente);

  await registrarActividadRealWhatsApp(pendiente, "", "message_received");
}

export async function registrarEntradaInternaWhatsApp(event) {
  if (event.type !== "message" || event.action !== "received") return;
  const contexto = event.context || {};
  if (contexto.channelId !== "whatsapp" || !contexto.content) return;
  const telefono = remitenteDeEventoWhatsApp(contexto, { sessionKey: event.sessionKey, senderId: contexto.senderId });
  if (!telefono) return;
  const clave = event.sessionKey || contexto.conversationId || telefono;
  const id = typeof contexto.messageId === "string" ? contexto.messageId.trim() : "";
  const pendiente = { telefono, mensaje: contexto.content, id };
  pendientesWhatsApp.set(clave, pendiente);
  console.info("[puente-celsia] message:received recibido"); // evento interno; sin mensaje ni telÃ©fono
  await registrarActividadRealWhatsApp(pendiente, "", "message_received");
}

export async function registrarRespuestaWhatsApp(event, ctx) {
  if ((ctx.channelId || event.channelId) !== "whatsapp" || !event.success || !event.content) return;
  const clave = claveSesion(ctx, event);
  const pendiente = pendientesWhatsApp.get(clave);
  if (!pendiente) return;
  pendientesWhatsApp.delete(clave); // `message_sent` no duplica si OpenClaw vuelve a emitirlo
  console.info("[puente-celsia] message_sent recibido; success=true"); // sin contenido ni telÃ©fono
  await registrarActividadRealWhatsApp(pendiente, event.content, "message_sent");
}

export async function registrarRespuestaInternaWhatsApp(event) {
  if (event.type !== "message" || event.action !== "sent") return;
  const contexto = event.context || {};
  if (contexto.channelId !== "whatsapp" || !contexto.success || !contexto.content) return;
  const clave = event.sessionKey || contexto.conversationId || "";
  const pendiente = pendientesWhatsApp.get(clave);
  if (!pendiente) return;
  pendientesWhatsApp.delete(clave); // no duplicar con `message_sent`
  console.info("[puente-celsia] message:sent recibido; success=true"); // sin contenido ni telÃ©fono
  await registrarActividadRealWhatsApp(pendiente, contexto.content, "message_sent");
}

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
  description: "Fija el telÃ©fono del cliente con el remitente verificado del canal antes de llamar al agente de Celsia.",
  register(api) {
    api.on("before_tool_call", fijarRemitente, { priority: 100 });
    api.on("message_received", registrarEntradaWhatsApp);
    api.on("message_sent", registrarRespuestaWhatsApp);
  },
});

