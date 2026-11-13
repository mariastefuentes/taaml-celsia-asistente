import { useEffect, useRef, useState } from "react";
import { cargarDatos, cargarMensajes, enviar, olvidarDatos } from "./api.js";

const SUGERENCIAS = [
  "¿Qué sedes hay en Ibagué?",
  "¿Cómo cancelo mi servicio?",
  "¿Cómo pago mi factura y dónde puedo hacerlo en Cali?",
];

function hiloDeLaDireccion() {
  return new URLSearchParams(window.location.search).get("hilo");
}

function fijarHilo(hilo) {
  const url = new URL(window.location.href);
  if (hilo) url.searchParams.set("hilo", hilo);
  else url.searchParams.delete("hilo");
  window.history.replaceState(null, "", url);
}

function actualizarUltimo(lista, cambio) {
  return [...lista.slice(0, -1), cambio(lista.at(-1))];
}

function etiqueta(h) {
  return h.herramienta === "buscar_en_base" ? "Buscando en el texto del sitio" : `Consultando la tabla ${h.args?.tabla ?? ""}`;
}

export default function App() {
  const [hilo, setHilo] = useState(hiloDeLaDireccion());
  const [mensajes, setMensajes] = useState([]);
  const [texto, setTexto] = useState("");
  const [enCurso, setEnCurso] = useState(false);
  const [error, setError] = useState("");
  const [recuerdos, setRecuerdos] = useState(null); // null = panel cerrado
  const fin = useRef(null);
  const ultimaPregunta = useRef("");

  useEffect(() => {
    if (!hilo) return;
    cargarMensajes(hilo).then(setMensajes).catch(() => setError("No se pudo recuperar la conversación guardada."));
  }, []); // solo al abrir la página: recarga y recupera el hilo desde la memoria del servidor

  useEffect(() => {
    fin.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensajes, enCurso]);

  function alEvento(e) {
    if (e.tipo === "hilo") {
      setHilo(e.hilo);
      fijarHilo(e.hilo);
    } else if (e.tipo === "herramienta") {
      setMensajes((m) => actualizarUltimo(m, (a) => ({ ...a, herramientas: [...(a.herramientas ?? []), e] })));
    } else if (e.tipo === "texto") {
      setMensajes((m) => actualizarUltimo(m, (a) => ({ ...a, texto: a.texto + e.texto })));
    } else if (e.tipo === "fin") {
      setMensajes((m) => actualizarUltimo(m, (a) => ({ ...a, usadas: e.usadas, tokens: e.tokens_entrada + e.tokens_salida, costo: e.costo_usd })));
    } else if (e.tipo === "error") {
      setError(e.mensaje);
      setMensajes((m) => (m.at(-1)?.texto === "" ? m.slice(0, -1) : m));
    }
  }

  async function preguntar(pregunta) {
    const mensaje = pregunta.trim();
    if (!mensaje || enCurso) return;
    ultimaPregunta.current = mensaje;
    setError("");
    setTexto("");
    setEnCurso(true);
    setMensajes((m) => [...m, { rol: "user", texto: mensaje }, { rol: "assistant", texto: "" }]);
    try {
      await enviar(mensaje, hilo, alEvento);
    } catch {
      setError("No hay conexión con el servidor. Revisa que la API esté encendida e intenta de nuevo.");
      setMensajes((m) => (m.at(-1)?.texto === "" ? m.slice(0, -1) : m));
    } finally {
      setEnCurso(false);
    }
  }

  async function verRecuerdos() {
    if (recuerdos) return setRecuerdos(null);
    try {
      setRecuerdos(await cargarDatos());
    } catch {
      setError("No se pudo consultar lo que recuerdo de ti.");
    }
  }

  async function olvidar() {
    try {
      await olvidarDatos();
      setRecuerdos([]);
    } catch {
      setError("No se pudo borrar lo guardado.");
    }
  }

  function nueva() {
    setHilo(null);
    fijarHilo(null);
    setMensajes([]);
    setError("");
  }

  return (
    <div className="app">
      <header>
        <div>
          <h1>Asistente Celsia</h1>
          <p>Agente con memoria, datos exactos y búsqueda en el sitio oficial</p>
        </div>
        <div className="acciones">
          <button className="secundario" onClick={verRecuerdos}>Lo que recuerdo</button>
          <button className="secundario" onClick={nueva} disabled={enCurso}>Nueva conversación</button>
        </div>
      </header>

      {recuerdos && (
        <section className="recuerdos" aria-label="Memoria de largo plazo">
          <strong>Memoria de largo plazo</strong>
          {recuerdos.length === 0 ? <p>No tengo datos tuyos guardados.</p> : <ul>{recuerdos.map((d) => <li key={d}>{d}</li>)}</ul>}
          {recuerdos.length > 0 && <button className="secundario" onClick={olvidar}>Olvidar todo</button>}
        </section>
      )}

      <main aria-live="polite">
        {mensajes.length === 0 && (
          <section className="vacio">
            <p>Pregúntame por sedes, contactos, trámites o tarifas de Celsia.</p>
            <div className="sugerencias">
              {SUGERENCIAS.map((s) => (
                <button key={s} className="secundario" onClick={() => preguntar(s)}>{s}</button>
              ))}
            </div>
          </section>
        )}
        {mensajes.map((m, i) => (
          <article key={i} className={`burbuja ${m.rol}`}>
            {m.rol === "assistant" && (m.herramientas?.length > 0 || m.usadas) && (
              <p className="herramienta">{m.usadas ?? m.herramientas.map(etiqueta).join("; ")}</p>
            )}
            <p className="contenido">{m.texto || (enCurso && i === mensajes.length - 1 ? "Pensando…" : "")}</p>
            {m.tokens > 0 && <p className="pie">{m.tokens.toLocaleString("es-CO")} tokens · ${m.costo?.toFixed(4)} USD</p>}
          </article>
        ))}
        <div ref={fin} />
      </main>

      {error && (
        <div className="error" role="alert">
          <span>{error}</span>
          <button className="secundario" onClick={() => preguntar(ultimaPregunta.current)} disabled={enCurso}>Reintentar</button>
        </div>
      )}

      <form onSubmit={(e) => { e.preventDefault(); preguntar(texto); }}>
        <input value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Escribe tu pregunta…" maxLength={1000} disabled={enCurso} aria-label="Pregunta" />
        <button type="submit" disabled={enCurso || !texto.trim()}>{enCurso ? "Respondiendo…" : "Enviar"}</button>
      </form>
    </div>
  );
}
