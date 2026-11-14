import { useEffect, useRef, useState } from "react";
import { Navigate, useLocation, useMatch, useNavigate, useParams } from "react-router-dom";
import Markdown from "./Markdown.jsx";
import { cargarDatos, cargarMensajes, enviar, olvidarDatos } from "./api.js";

const SUGERENCIAS = [
  "¿Qué sedes hay en Ibagué?",
  "¿Cómo cancelo mi servicio?",
  "Quiero reportar un daño en Ibagué: ¿qué hago y a qué número llamo?",
];

const HILO_VALIDO = /^[0-9a-f]{32}$/; // los hilos son uuid4 en hexadecimal; cualquier otra cosa en la dirección no es una conversación

function actualizarUltimo(lista, cambio) {
  return [...lista.slice(0, -1), cambio(lista.at(-1))];
}

function sinRepetidas(fuentes) {
  return [...new Map(fuentes.map((f) => [f.chunk_id, f])).values()];
}

// Si la respuesta es «no tengo esa información» no se muestran fuentes: no hubo evidencia que citar.
function sinEvidencia(texto) {
  return /no tengo esa informaci[oó]n/i.test(texto ?? "");
}

function Fuentes({ fuentes, texto }) {
  if (!fuentes?.length || sinEvidencia(texto)) return null;
  return (
    <details className="fuentes" open>
      <summary>Fragmentos consultados ({fuentes.length})</summary>
      <ul>
        {fuentes.map((f) => (
          <li key={f.chunk_id}>
            <strong>{f.documento}</strong>, fragmento {f.fragmento} · <a href={f.fuente} target="_blank" rel="noreferrer">{f.fuente}</a>
            {f.extracto && <blockquote className="extracto">{f.extracto}</blockquote>}
          </li>
        ))}
      </ul>
    </details>
  );
}

function etiqueta(h) {
  if (h.herramienta === "buscar_en_base") return "Buscando en el texto del sitio";
  if (h.herramienta === "guardar_dato_del_cliente") return "Guardando un dato del cliente";
  if (h.herramienta === "recordar_datos_del_cliente") return "Recordando lo que sabe del cliente";
  return `Consultando la tabla ${h.args?.tabla ?? ""}`;
}

export default function App() {
  const { hilo: hiloDeLaRuta } = useParams();
  const { search } = useLocation();
  const navegar = useNavigate();
  const enInicio = useMatch("/");
  const enConversacion = useMatch("/c/:hilo");
  const direccionConocida = enInicio || enConversacion; // los dos hooks se llaman siempre: no se pueden encadenar con ||
  const hiloViejo = new URLSearchParams(search).get("hilo"); // direcciones antiguas: /?hilo=<id>
  const [hilo, setHilo] = useState(hiloDeLaRuta ?? hiloViejo);
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

  function fijarHilo(id) {
    navegar(id ? `/c/${id}` : "/", { replace: true }); // la dirección sigue a la conversación sin crear pasos en el historial
  }

  function alEvento(e) {
    if (e.tipo === "hilo") {
      setHilo(e.hilo);
      fijarHilo(e.hilo);
    } else if (e.tipo === "herramienta") {
      setMensajes((m) => actualizarUltimo(m, (a) => ({ ...a, herramientas: [...(a.herramientas ?? []), e] })));
    } else if (e.tipo === "fuentes") {
      setMensajes((m) => actualizarUltimo(m, (a) => ({ ...a, fuentes: sinRepetidas([...(a.fuentes ?? []), ...e.fuentes]) })));
    } else if (e.tipo === "texto") {
      setMensajes((m) => actualizarUltimo(m, (a) => ({ ...a, texto: a.texto + e.texto })));
    } else if (e.tipo === "aviso") {
      setMensajes((m) => actualizarUltimo(m, (a) => ({ ...a, aviso: e.datos })));
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

  if (!direccionConocida || (hiloDeLaRuta && !HILO_VALIDO.test(hiloDeLaRuta))) return <Navigate to="/" replace />;
  if (!hiloDeLaRuta && hiloViejo && HILO_VALIDO.test(hiloViejo)) return <Navigate to={`/c/${hiloViejo}`} replace />;

  return (
    <div className="app">
      <header>
        <div className="marca">
          <img src="/celsia-icono.png" alt="" aria-hidden="true" />
          <div>
            <h1>Asistente <span>Celsia</span></h1>
            <p>Agente con memoria, datos exactos y búsqueda en el sitio oficial</p>
          </div>
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
            <img className="logo-grande" src="/celsia-logo.png" alt="Celsia" />
            <h2>¿En qué te puedo ayudar?</h2>
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
            <div className="contenido">{m.texto ? <Markdown texto={m.texto} /> : (enCurso && i === mensajes.length - 1 ? <span className="pensando">Pensando<i /><i /><i /></span> : "")}</div>
            {m.rol === "assistant" && m.aviso?.length > 0 && (
              <p className="aviso">Verifica antes de usar: estos datos de la respuesta no aparecen en lo que el asistente consultó ({m.aviso.join(", ")}).</p>
            )}
            {m.rol === "assistant" && <Fuentes fuentes={m.fuentes} texto={m.texto} />}
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
