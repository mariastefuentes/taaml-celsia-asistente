// Cliente de la API del agente. Un turno llega por streaming (Server-Sent Events sobre un POST).

// Identificador anónimo del cliente: la API lo usa para su memoria de largo plazo. Vive en el navegador (localStorage); si el navegador lo
// bloquea (ventana privada, por ejemplo) se usa uno por pestaña, así «Nueva conversación» sigue recordando al cliente mientras la pestaña esté abierta.
let delaPestana = null;

function nuevoId() {
  return crypto.randomUUID().replaceAll("-", "");
}

export function usuario() {
  try {
    let id = localStorage.getItem("usuario");
    if (!id) {
      id = nuevoId();
      localStorage.setItem("usuario", id);
    }
    return id;
  } catch {
    delaPestana ??= nuevoId();
    return delaPestana;
  }
}

// Estado de la API (`/api/salud`): modelo en uso y base vectorial que está respondiendo (qdrant, numpy o ninguno).
export async function cargarSalud() {
  const r = await fetch("/api/salud");
  if (!r.ok) throw new Error("La API no está disponible");
  return r.json();
}

export async function cargarDatos() {
  const r = await fetch(`/api/usuarios/${usuario()}/datos`);
  if (!r.ok) throw new Error("No se pudieron cargar los datos guardados");
  return (await r.json()).datos;
}

export async function olvidarDatos() {
  const r = await fetch(`/api/usuarios/${usuario()}/datos`, { method: "DELETE" });
  if (!r.ok) throw new Error("No se pudieron borrar los datos");
}

export async function cargarMensajes(hilo) {
  const r = await fetch(`/api/hilos/${hilo}/mensajes`);
  if (!r.ok) throw new Error("No se pudo recuperar la conversación");
  return (await r.json()).mensajes;
}

function leerBloque(bloque) {
  const tipo = /^event: (.+)$/m.exec(bloque)?.[1];
  const datos = /^data: (.+)$/m.exec(bloque)?.[1];
  return tipo && datos ? { tipo, ...JSON.parse(datos) } : null;
}

// Envía la pregunta y llama a `alEvento` por cada evento: hilo, herramienta, texto, fin o error.
export async function enviar(mensaje, hilo, alEvento, senal) {
  const r = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mensaje, hilo, usuario: usuario() }),
    signal: senal,
  });
  if (!r.ok || !r.body) throw new Error(`El servidor respondió ${r.status}`);
  const lector = r.body.pipeThrough(new TextDecoderStream()).getReader();
  let pendiente = "";
  for (;;) {
    const { value, done } = await lector.read();
    if (done) break;
    pendiente += value;
    const bloques = pendiente.split("\n\n");
    pendiente = bloques.pop();
    for (const b of bloques) {
      const e = leerBloque(b);
      if (e) alEvento(e);
    }
  }
}
