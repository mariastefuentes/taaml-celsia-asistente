import { Fragment } from "react";

// Markdown mínimo para las respuestas del agente: títulos, listas (con sangría), negrita, enlaces y separadores.
// Todo se construye como elementos de React (nunca como HTML crudo), así que el texto del modelo no puede inyectar etiquetas.

const URL_SUELTA = /https?:\/\/[^\s)]+/g;

function enlace(url, clave) {
  return <a key={clave} href={url} target="_blank" rel="noreferrer">{url}</a>;
}

function enLinea(texto) {
  // **negrita**, [texto](url) y direcciones sueltas
  const partes = [];
  const patron = /\*\*(.+?)\*\*|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;
  let ultimo = 0;
  let m;
  while ((m = patron.exec(texto))) {
    if (m.index > ultimo) partes.push(...sueltas(texto.slice(ultimo, m.index), partes.length));
    if (m[1] !== undefined) partes.push(<strong key={`n${partes.length}`}>{enLinea(m[1])}</strong>);
    else partes.push(<a key={`a${partes.length}`} href={m[3]} target="_blank" rel="noreferrer">{m[2]}</a>);
    ultimo = m.index + m[0].length;
  }
  if (ultimo < texto.length) partes.push(...sueltas(texto.slice(ultimo), partes.length));
  return partes;
}

function sueltas(texto, base) {
  const salida = [];
  let ultimo = 0;
  for (const m of texto.matchAll(URL_SUELTA)) {
    if (m.index > ultimo) salida.push(<Fragment key={`t${base}-${ultimo}`}>{texto.slice(ultimo, m.index)}</Fragment>);
    salida.push(enlace(m[0], `u${base}-${m.index}`));
    ultimo = m.index + m[0].length;
  }
  if (ultimo < texto.length) salida.push(<Fragment key={`t${base}-${ultimo}`}>{texto.slice(ultimo)}</Fragment>);
  return salida;
}

const ITEM = /^(\s*)([-*]|\d+\.)\s+(.*)$/;

function lista(items, clave) {
  // items: [{sangria, ordenada, texto}] consecutivos; las sangrías mayores se anidan
  const raiz = [];
  const pila = [{ sangria: -1, hijos: raiz }];
  for (const it of items) {
    while (pila.length > 1 && it.sangria <= pila.at(-1).sangria) pila.pop();
    const nodo = { ...it, hijos: [] };
    pila.at(-1).hijos.push(nodo);
    pila.push({ sangria: it.sangria, hijos: nodo.hijos });
  }
  const pintar = (nodos, k) => {
    const Etiqueta = nodos[0].ordenada ? "ol" : "ul";
    return (
      <Etiqueta key={k}>
        {nodos.map((n, i) => (
          <li key={i}>
            {enLinea(n.texto)}
            {n.hijos.length > 0 && pintar(n.hijos, `${k}-${i}`)}
          </li>
        ))}
      </Etiqueta>
    );
  };
  return pintar(raiz, clave);
}

export default function Markdown({ texto }) {
  const lineas = texto.split("\n");
  const bloques = [];
  let i = 0;
  while (i < lineas.length) {
    const linea = lineas[i];
    if (!linea.trim()) { i++; continue; }
    const titulo = linea.match(/^#{1,6}\s+(.*)$/);
    if (titulo) { bloques.push(<h4 key={i}>{enLinea(titulo[1])}</h4>); i++; continue; }
    if (/^\s*---+\s*$/.test(linea)) { bloques.push(<hr key={i} />); i++; continue; }
    if (ITEM.test(linea)) {
      const items = [];
      const inicio = i;
      while (i < lineas.length && ITEM.test(lineas[i])) {
        const [, sangria, marca, cuerpo] = lineas[i].match(ITEM);
        items.push({ sangria: sangria.length, ordenada: /\d/.test(marca), texto: cuerpo });
        i++;
      }
      bloques.push(lista(items, inicio));
      continue;
    }
    const parrafo = [];
    const inicio = i;
    while (i < lineas.length && lineas[i].trim() && !ITEM.test(lineas[i]) && !/^#{1,6}\s/.test(lineas[i]) && !/^\s*---+\s*$/.test(lineas[i])) {
      parrafo.push(lineas[i]);
      i++;
    }
    bloques.push(
      <p key={inicio}>
        {parrafo.map((l, j) => <Fragment key={j}>{j > 0 && <br />}{enLinea(l)}</Fragment>)}
      </p>,
    );
  }
  return <>{bloques}</>;
}
