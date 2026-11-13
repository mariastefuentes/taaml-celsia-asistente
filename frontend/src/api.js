// Cliente de la API del agente. Un turno llega por streaming (Server-Sent Events sobre un POST).

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
    body: JSON.stringify({ mensaje, hilo }),
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
