import { useEffect, useRef, useState } from "react";
import { Navigate, useLocation, useMatch, useNavigate, useParams } from "react-router-dom";
import Markdown from "./Markdown.jsx";
import { cargarDatos, cargarEstado, cargarMensajes, cargarSalud, enviar, olvidarDatos } from "./api.js";

// Las preguntas que más hace un cliente: sirven de punto de partida; lo demás se descubre conversando.
const SUGERENCIAS = [
  { icono: "💳", titulo: "Pagar la factura", pregunta: "¿Cómo puedo pagar mi factura?" },
  { icono: "⚡", titulo: "Sin energía", pregunta: "Se fue la luz en mi casa, ¿qué hago?" },
  { icono: "📍", titulo: "Puntos de atención", pregunta: "¿Qué puntos de atención hay en Ibagué?" },
  { icono: "📝", titulo: "Reclamos", pregunta: "Quiero hacer un reclamo por mi factura" },
];

const ALMACENES = { qdrant: "Qdrant", numpy: "búsqueda local", ninguno: "sin índice" };

const DISTINTIVOS = {
  mixto: { icono: "🧭", clase: "mixto" },
  gestion: { icono: "📝", clase: "datos" }, // reclamos, reportes de daño y paso a un asesor
  datos: { icono: "📊", clase: "datos" },
  texto: { icono: "📄", clase: "texto" },
  memoria: { icono: "🧠", clase: "memoria" },
  directa: { icono: "💬", clase: "directa" },
};
const GESTIONES = ["radicar_reclamo", "consultar_mis_reclamos", "consultar_estado_reclamo", "cancelar_reclamo", "derivar_a_asesor", "reportar_dano_electrico"];

function tipoDeHerramienta(nombre) {
  if (nombre === "buscar_en_base") return "texto";
  if (/_datos?_del_cliente$/.test(nombre)) return "memoria";
  return GESTIONES.includes(nombre) ? "gestion" : "datos";
}

// Una conversación recuperada al recargar solo trae la frase («Usó: consultó las sedes; …»), no los nombres de las herramientas.
function tipoDeFrase(frase) {
  if (/texto del sitio/.test(frase)) return "texto";
  if (/reclamo|asesor|daño/.test(frase)) return "gestion";
  return /(sabe|dato) del cliente/.test(frase) ? "memoria" : "datos";
}

// Qué hizo el router en este turno, para el distintivo de la respuesta: una herramienta (con su ícono) o ninguna.
function tipoDeUso(m) {
  const usadas = m.usadas ?? "";
  let tipos = (m.herramientas ?? []).map((h) => tipoDeHerramienta(h.herramienta));
  if (!tipos.length && usadas.startsWith("Usó: ")) tipos = usadas.slice(5).split("; ").map(tipoDeFrase);
  if (!tipos.length && /revisión/.test(usadas)) tipos = ["gestion"];
  if (tipos.includes("datos") && tipos.includes("texto")) return DISTINTIVOS.mixto;
  return DISTINTIVOS[["gestion", "datos", "texto", "memoria"].find((t) => tipos.includes(t)) ?? "directa"];
}

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

const RESPUESTA_QR = "Ve arriba a la derecha donde dice WhatsApp, ahí puedes escanear el código.";

// El único QR de esta página es el de WhatsApp: la pregunta se contesta sin llamar al modelo.
function pideElQrDeWhatsapp(texto) {
  const t = texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  if (/que es (un |el )?(codigo )?qr|para que sirve (el |un )?qr/.test(t)) return false;
  return /\bqr\b/.test(t) || (/whatsapp|wsp|wasap/.test(t) && /escan/.test(t));
}

// QR del WhatsApp del bot: el mismo agente que atiende esta página, para quien prefiera escribir desde el celular.
function QrWhatsApp() {
  return (
    <section className="qr-whatsapp" aria-label="Habla con el asistente por WhatsApp">
      <img src="/qr-whatsapp.png" alt="Código QR para abrir el chat de WhatsApp del asistente" />
      <div>
        <strong>¿Prefieres WhatsApp?</strong>
        <p>Escanea el código con la cámara de tu celular y escríbele al asistente. Te responde el mismo agente, con sus 20 herramientas.</p>
      </div>
    </section>
  );
}

// Acciones de la respuesta: copiar, reacciones 👍/👎 (exclusivas), escuchar en español y regenerar la última respuesta.
function AccionesRespuesta({ indice, reaccion, onReaccion, texto, regenerando, onRegenerar, puedeRegenerar }) {
  const [copiado, setCopiado] = useState(false);
  const [escuchando, setEscuchando] = useState(false);
  const soportaVoz = typeof speechSynthesis !== "undefined";
  const hayTexto = Boolean((texto ?? "").trim()); // mientras la respuesta se escribe no hay nada que copiar ni leer
  const activa = (seleccionada) => (seleccionada ? "acc-btn activa" : "acc-btn");

  useEffect(() => () => { if (soportaVoz) speechSynthesis.cancel(); }, [soportaVoz]);

  const hacerCopiar = async () => {
    let ok = false;
    try {
      await navigator.clipboard.writeText(texto);
      ok = true;
    } catch {
      // Sin permiso o sin https (el chat abierto por la dirección de la red): copia con un campo temporal.
      const tmp = document.createElement("textarea");
      tmp.value = texto;
      document.body.appendChild(tmp);
      tmp.select();
      ok = document.execCommand("copy");
      document.body.removeChild(tmp);
    }
    if (ok) {
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    }
  };

  const hacerEscuchar = () => {
    if (escuchando) {
      speechSynthesis.cancel();
      setEscuchando(false);
      return;
    }
    const voz = new SpeechSynthesisUtterance(texto);
    voz.lang = "es";
    voz.onend = () => setEscuchando(false);
    voz.onerror = () => setEscuchando(false);
    speechSynthesis.cancel(); // evita que dos respuestas suenen a la vez
    speechSynthesis.speak(voz);
    setEscuchando(true);
  };

  return (
    <div className="acciones-respuesta" aria-label="Acciones de la respuesta del asistente">
      <button type="button" className="acc-btn" onClick={hacerCopiar} title="Copiar la respuesta" aria-label="Copiar">
        {copiado ? "Copiado" : <span className="icono" aria-hidden="true">📋</span>}
      </button>
      <button type="button" className={activa(reaccion === "up")} onClick={() => onReaccion(indice, "up")} title="Útil" aria-label="Reaccionar: útil" aria-pressed={reaccion === "up"}>
        👍
      </button>
      <button type="button" className={activa(reaccion === "down")} onClick={() => onReaccion(indice, "down")} title="No útil" aria-label="Reaccionar: no útil" aria-pressed={reaccion === "down"}>
        👎
      </button>
      {soportaVoz && hayTexto && (
        <button type="button" className={activa(escuchando)} onClick={hacerEscuchar} title="Escuchar la respuesta" aria-label="Escuchar" aria-pressed={escuchando}>
          {escuchando ? "⏹" : "🔊"}
        </button>
      )}
      {puedeRegenerar && (
        <button type="button" className={activa(false)} onClick={() => onRegenerar(indice)} title="Regenerar la respuesta" aria-label="Regenerar" disabled={regenerando} aria-busy={regenerando}>
          {regenerando ? "⏳" : "🔄"}
        </button>
      )}
    </div>
  );
}

function Fuentes({ fuentes, texto, abiertas }) {
  if (!fuentes?.length || sinEvidencia(texto)) return null;
  return (
    <details className="fuentes" open={abiertas}>
      <summary><span aria-hidden="true">📄</span> Fuentes ({fuentes.length})</summary>
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
  return h.args?.tabla ? `Consultando la tabla ${h.args.tabla}` : "Consultando una herramienta";
}

// Los detalles técnicos (herramientas, tokens, costo, base de búsqueda) están ocultos para el cliente; quien los activa los conserva en su navegador.
function leerDetalles() {
  try {
    return localStorage.getItem("detalles") === "1";
  } catch {
    return false;
  }
}

export default function App() {
  const { hilo: hiloDeLaRuta } = useParams();
  const { search } = useLocation();
  const navegar = useNavigate();
  const enInicio = useMatch("/");
  const enConversacion = useMatch("/c/:hilo");
  const direccionConocida = enInicio || enConversacion; // los dos hooks se llaman siempre: no se pueden encadenar con ||
  const hiloViejo = new URLSearchParams(search).get("hilo"); // direcciones antiguas: /?hilo=<id>
  const hiloDeLaDireccion = hiloDeLaRuta ?? hiloViejo;
  // Una dirección dañada no es una conversación: si se guardara, ni la consulta del historial ni la primera pregunta funcionarían.
  const [hilo, setHilo] = useState(HILO_VALIDO.test(hiloDeLaDireccion ?? "") ? hiloDeLaDireccion : null);
  const [mensajes, setMensajes] = useState([]);
  const [recuperando, setRecuperando] = useState(HILO_VALIDO.test(hiloDeLaDireccion ?? "")); // al abrir una conversación guardada no se muestra la bienvenida mientras llega
  const [texto, setTexto] = useState("");
  const [enCurso, setEnCurso] = useState(false);
  const [pendiente, setPendiente] = useState(null); // una persona está revisando algo de este hilo
  const [error, setError] = useState("");
  const [recuerdos, setRecuerdos] = useState(null); // null = panel cerrado
  const [verQr, setVerQr] = useState(false); // QR de WhatsApp plegado; en el inicio se muestra siempre
  const [salud, setSalud] = useState(null); // null = aún no se sabe; false = la API no responde
  const [detalles, setDetalles] = useState(leerDetalles);
  const [reacciones, setReacciones] = useState({}); // por índice de respuesta: "up" | "down"; visuales, no se persisten
  const [regenerando, setRegenerando] = useState(null); // índice de la respuesta que se está regenerando
  const fin = useRef(null);
  const ultimaPregunta = useRef("");

  useEffect(() => {
    let vivo = true;
    const revisar = () => cargarSalud().then((s) => vivo && setSalud(s)).catch(() => vivo && setSalud(false));
    revisar();
    const cada = setInterval(revisar, 15000);
    return () => {
      vivo = false;
      clearInterval(cada);
    };
  }, []);

  useEffect(() => {
    if (!hilo) return;
    cargarMensajes(hilo)
      .then(setMensajes)
      .catch(() => setError("No se pudo recuperar la conversación guardada."))
      .finally(() => setRecuperando(false));
  }, []); // solo al abrir la página: recarga y recupera el hilo desde la memoria del servidor

  // Si el hilo quedó esperando una persona (también al recargar), el chat se bloquea hasta que la decisión esté lista.
  useEffect(() => {
    setPendiente(null);
    if (!hilo) return;
    let vivo = true;
    cargarEstado(hilo)
      .then((e) => {
        if (vivo && e.pendiente) setPendiente({ tipo: "pendiente", ...e.pendiente });
      })
      .catch(() => {});
    return () => {
      vivo = false;
    };
  }, [hilo]);

  const hayPendiente = Boolean(pendiente);
  useEffect(() => {
    if (!hilo || !hayPendiente) return;
    let vivo = true;
    const cada = setInterval(async () => {
      try {
        const e = await cargarEstado(hilo);
        if (!vivo || e.pendiente) return;
        // La persona ya decidió: su respuesta se trae del historial y aparece sin que el cliente escriba nada.
        const respuesta = (await cargarMensajes(hilo)).filter((m) => m.rol === "assistant").at(-1);
        if (!vivo) return;
        if (respuesta) {
          setMensajes((m) =>
            m.some((x) => x.rol === "assistant" && x.texto === respuesta.texto)
              ? m
              : [...m, { rol: "assistant", texto: respuesta.texto, usadas: "Respuesta de la revisión por una persona", entregado: true }],
          );
        }
        setPendiente(null);
      } catch {
        // sin conexión: se vuelve a intentar en la siguiente consulta
      }
    }, 3000);
    return () => {
      vivo = false;
      clearInterval(cada);
    };
  }, [hilo, hayPendiente]);

  useEffect(() => {
    // Una respuesta que cabe en pantalla se sigue hasta el final; una más larga se ancla en su inicio para que se lea desde arriba.
    const ultima = fin.current?.previousElementSibling;
    const ventana = fin.current?.parentElement;
    if (ultima && ventana && ultima.offsetHeight > ventana.clientHeight - 24) ultima.scrollIntoView({ behavior: "smooth", block: "start" });
    else fin.current?.scrollIntoView({ behavior: "smooth" });
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
    } else if (e.tipo === "pendiente") {
      setPendiente(e);
    } else if (e.tipo === "fin") {
      setMensajes((m) => actualizarUltimo(m, (a) => ({ ...a, usadas: e.usadas, tokens: e.tokens_entrada + e.tokens_salida, costo: e.costo_usd })));
    } else if (e.tipo === "error") {
      setError(e.mensaje);
      setMensajes((m) => (m.at(-1)?.texto === "" ? m.slice(0, -1) : m));
    }
  }

  async function preguntar(pregunta) {
    const mensaje = pregunta.trim();
    if (!mensaje || enCurso || pendiente) return;
    ultimaPregunta.current = mensaje;
    setError("");
    setTexto("");
    if (pideElQrDeWhatsapp(mensaje)) {
      setMensajes((m) => [...m, { rol: "user", texto: mensaje }, { rol: "assistant", texto: RESPUESTA_QR }]);
      return;
    }
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

  // Reacciones: visualmente, por índice de respuesta; pulsar la que está seleccionada la desactiva.
  function registrarReaccion(indice, tipo) {
    setReacciones((r) => ({ ...r, [indice]: r[indice] === tipo ? undefined : tipo }));
  }

  // Regenerar: repite la última pregunta y sustituye su respuesta, sin duplicar mensajes en pantalla.
  async function hacerRegenerar(indice) {
    if (enCurso || regenerando !== null || pendiente) return;
    const pregunta = [...mensajes.slice(0, indice)].reverse().find((m) => m.rol === "user")?.texto;
    if (!pregunta) return;
    ultimaPregunta.current = pregunta;
    setError("");
    setRegenerando(indice);
    setEnCurso(true); // como en un turno normal: no se envía nada más hasta que termine, o las dos respuestas se mezclan
    setReacciones((r) => {
      const copia = { ...r };
      delete copia[indice]; // la respuesta nueva empieza sin reacción
      return copia;
    });
    setMensajes((m) => [...m.slice(0, indice), { rol: "assistant", texto: "" }]); // quita la respuesta anterior
    try {
      await enviar(pregunta, hilo, alEvento);
    } catch {
      setError("No pude volver a generar la respuesta; intenta de nuevo.");
    } finally {
      setEnCurso(false);
      setRegenerando(null);
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

  function alternarDetalles() {
    setDetalles(!detalles);
    try {
      localStorage.setItem("detalles", detalles ? "0" : "1");
    } catch {
      // sin almacenamiento (ventana privada): vale mientras la pestaña esté abierta
    }
  }

  function nueva() {
    setHilo(null);
    fijarHilo(null);
    setMensajes([]);
    setPendiente(null);
    setError("");
  }

  if (!direccionConocida || (hiloDeLaRuta && !HILO_VALIDO.test(hiloDeLaRuta))) return <Navigate to="/" replace />;
  if (!hiloDeLaRuta && hiloViejo && HILO_VALIDO.test(hiloViejo)) return <Navigate to={`/c/${hiloViejo}`} replace />;

  // Solo la última respuesta se puede regenerar: así lo que se ve y lo que guarda el hilo no se separan.
  const ultimoAsistente = mensajes.reduce((ultimo, m, i) => (m.rol === "assistant" ? i : ultimo), -1);

  return (
    <div className="app">
      <header>
        <div className="marca">
          <img src="/celsia-icono.png" alt="" aria-hidden="true" />
          <div>
            <h1>Asistente <span>Celsia</span></h1>
            <p>Te ayudo con tu factura, cortes de luz, sedes y reclamos</p>
          </div>
        </div>
        <div className="acciones">
          {salud !== null && (
            <span className={`estado ${salud ? "ok" : "caida"}`} role="status" title={salud ? (detalles ? `Modelo ${salud.modelo}` : undefined) : "La API no responde"}>
              {salud ? `En línea${detalles && salud.almacen ? ` · ${ALMACENES[salud.almacen] ?? salud.almacen}` : ""}` : "Sin conexión"}
            </span>
          )}
          <button className="secundario" onClick={verRecuerdos}><span className="largo">Lo que recuerdo</span><span className="corto">Mis datos</span></button>
          <button className="secundario" onClick={() => setVerQr((v) => !v)} aria-expanded={verQr}>WhatsApp</button>
          <button className="secundario" onClick={nueva} disabled={enCurso}><span className="largo">Nueva conversación</span><span className="corto">Nueva</span></button>
        </div>
      </header>

      {verQr && (mensajes.length > 0 || recuperando) && <QrWhatsApp />}

      {recuerdos && (
        <section className="recuerdos" aria-label="Memoria de largo plazo">
          <strong>Memoria de largo plazo</strong>
          {recuerdos.length === 0 ? <p>No tengo datos de tu perfil guardados.</p> : <ul>{recuerdos.map((d) => <li key={d}>{d}</li>)}</ul>}
          <p>«Olvidar todo» borra tu perfil, tus reclamos y tus pedidos de asesor.</p>
          <button className="secundario" onClick={olvidar}>Olvidar todo</button>
        </section>
      )}

      <main aria-live="polite">
        {recuperando && <p className="vacio" role="status">Recuperando la conversación<span className="pensando"><i /><i /><i /></span></p>}
        {!recuperando && mensajes.length === 0 && (
          <section className="vacio">
            <img className="logo-grande" src="/celsia-logo.png" alt="Celsia" />
            <h2>¿En qué te puedo ayudar?</h2>
            <p>Pregúntame por sedes, contactos, trámites o tarifas de Celsia.</p>
            <div className="sugerencias">
              {SUGERENCIAS.map((s) => (
                <button key={s.titulo} className="tarjeta" onClick={() => preguntar(s.pregunta)}>
                  <span className="icono" aria-hidden="true">{s.icono}</span>
                  <strong>{s.titulo}</strong>
                  <span className="ejemplo">{s.pregunta}</span>
                </button>
              ))}
            </div>
            <QrWhatsApp />
          </section>
        )}
        {mensajes.map((m, i) => (
          <div key={i} className="bloque-mensaje">
            <article className={`burbuja ${m.rol}`}>
            {m.rol === "assistant" && (detalles || m.entregado) && (m.herramientas?.length > 0 || m.usadas) && (
              <p className={`herramienta ${tipoDeUso(m).clase}`}>
                <span aria-hidden="true">{tipoDeUso(m).icono}</span> {m.usadas ? [...new Set(m.usadas.split("; "))].join("; ") : [...new Set(m.herramientas.map(etiqueta))].join(" · ")}
              </p>
            )}
            <div className="contenido">{m.texto ? <Markdown texto={m.texto} /> : (enCurso && i === mensajes.length - 1 ? <span className="pensando">Pensando<i /><i /><i /></span> : "")}</div>
            {m.rol === "assistant" && m.aviso?.length > 0 && (
              <p className="aviso">Verifica antes de usar: estos datos de la respuesta no aparecen en lo que el asistente consultó ({m.aviso.join(", ")}).</p>
            )}
            {m.rol === "assistant" && <Fuentes fuentes={m.fuentes} texto={m.texto} abiertas={detalles} />}
            {detalles && m.tokens > 0 && <p className="pie">{m.tokens.toLocaleString("es-CO")} tokens · ${m.costo?.toFixed(4)} USD</p>}
            </article>
            {m.rol === "assistant" && !(enCurso && i === mensajes.length - 1) && (
              <AccionesRespuesta
                indice={i}
                reaccion={reacciones[i] ?? null}
                onReaccion={registrarReaccion}
                texto={m.texto}
                regenerando={regenerando === i}
                onRegenerar={hacerRegenerar}
                puedeRegenerar={i === ultimoAsistente && !m.entregado}
              />
            )}
          </div>
        ))}
        <div ref={fin} />
      </main>

      {pendiente && (
        <div className="pendiente-aviso" role="status">
          <span>En revisión por una persona. El chat se desbloquea cuando se decida.</span>
        </div>
      )}

      {error && (
        <div className="error" role="alert">
          <span>{error}</span>
          <button className="secundario" onClick={() => preguntar(ultimaPregunta.current)} disabled={enCurso || !!pendiente}>Reintentar</button>
        </div>
      )}

      <form onSubmit={(e) => { e.preventDefault(); preguntar(texto); }}>
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder={pendiente ? "En revisión por una persona…" : "Escribe tu pregunta…"}
          maxLength={1000}
          disabled={enCurso || !!pendiente}
          aria-label="Pregunta"
        />
        <button type="submit" disabled={enCurso || !!pendiente || !texto.trim()}>
          {pendiente ? "En revisión…" : enCurso ? "Respondiendo…" : "Enviar"}
        </button>
      </form>
      <button type="button" className="detalles-btn" onClick={alternarDetalles} aria-pressed={detalles}>
        {detalles ? "Ocultar detalles técnicos" : "Ver detalles técnicos"}
      </button>
    </div>
  );
}
