# Guion de la sustentación del Módulo 3 (WhatsApp)

Sábado 21 de noviembre de 2026, 8:00 a. m. Duración: **15 minutos, sin diapositivas**. El profesor y el público le escriben al bot por WhatsApp mientras se muestra la terminal. Lo que no se pueda mostrar en vivo se muestra con el diagrama de `docs/arquitectura_agente.html` (diagrama interactivo, hecho con Archify) y el cuaderno de t-SNE.

Lo marcado como **(verificar)** no se ha probado con Meta real: se confirma en el ensayo.

## Reparto sugerido (cuatro integrantes)
| Quién | Qué hace en la sustentación |
|---|---|
| Persona 1 | Abre y cierra: qué es el sistema, el recorrido del mensaje (diagrama) y por qué servidor propio y no N8N |
| Persona 2 | Maneja la terminal: API, túnel, reinicio, aprobación del reclamo |
| Persona 3 | Maneja el teléfono y recibe los mensajes del público; lee en voz alta lo que responde el bot |
| Persona 4 | Explica el código cuando el profesor pregunte (herramientas, esquemas, HITL, PostgresSaver) y muestra el cuaderno de t-SNE |

## Antes de empezar (la noche anterior y 30 minutos antes)
0. **Chequeo automático:** `make ensayo-whatsapp` (gratis) revisa claves, Ollama, índice, API, panel y si el token de Meta sigue vivo; con el túnel encendido, `make ensayo-whatsapp ARGS="--tunel https://<túnel>"` prueba también ese camino. No cambia nada ni llama al modelo. Si dice FALTA, se arregla antes de seguir con los pasos.
1. **Token de Meta.** El token temporal del panel de Meta vence en unas 24 horas **(verificar)**: generar uno nuevo la mañana del sábado y ponerlo en `.env` (`WHATSAPP_TOKEN`). Sin esto el bot recibe pero no puede responder.
2. **Destinatarios de prueba.** Con el número de prueba, Meta solo entrega mensajes a los teléfonos registrados como destinatarios, y hay un máximo pequeño **(verificar cuántos)**. Registrar el teléfono del profesor y los de los cuatro integrantes. Si el profesor no está en la lista, no recibirá respuesta: tener el plan B listo.
3. **Ollama encendido** (los embeddings lo necesitan) y las claves del modelo en `.env`.
4. **Memoria limpia:** `make demo-limpiar` borra lo que el bot recuerda de los ensayos. Las conversaciones de los ensayos siguen guardadas por teléfono: usar un teléfono que no haya ensayado para la parte de memoria, o decir que es el mismo.
5. **Terminal 1:** `make api` (levanta PostgreSQL local y la API). Esperar `Application startup complete` y comprobar `http://127.0.0.1:8000/api/salud`: debe decir `"almacen":"qdrant"` y `"memoria":"postgresql"`.
6. **Terminal 2:** el túnel https hacia el puerto 8000 (por ejemplo `cloudflared tunnel --url http://localhost:8000`). La dirección cambia cada vez: copiarla y **registrarla de nuevo en el panel de Meta** como `https://<túnel>/webhook/whatsapp` con el token de verificación (`WHATSAPP_VERIFY_TOKEN`). Con el campo `messages` suscrito.
7. **Prueba de humo:** escribir «Hola» desde un teléfono registrado y comprobar que llega la respuesta (5 a 25 s la primera vez).
8. Tener a mano: este guion, el diagrama, el cuaderno `notebooks/analisis_conversaciones.ipynb` abierto y el comando de aprobación (más abajo) con el teléfono del que va a escribir el reclamo.

## Línea de tiempo (15 minutos)
| Minuto | Qué | Quién |
|---|---|---|
| 0:00 a 2:00 | Qué es el sistema y el recorrido de un mensaje: cliente, Meta, nuestro webhook en FastAPI, agente, herramientas, PostgreSQL y vuelta por la Graph API (diagrama). Decir que es la vía 2: servidor propio, sin N8N | 1 |
| 2:00 a 3:00 | Mostrar la terminal con los registros de la API y pedir al público que escriba al bot (enlace `https://wa.me/<número>` o el número escrito en la pizarra) | 1, 3 |
| 3:00 a 6:30 | **Casos con el público** (abajo): tabla, documento, fuera de alcance | 3, 2 |
| 6:30 a 9:00 | **Memoria que sobrevive al reinicio** | 2, 3 |
| 9:00 a 11:30 | **Reclamo con aprobación humana** | 2, 3 |
| 11:30 a 13:00 | **Qué tan bien lo hace**: cuaderno de t-SNE y los límites que ya conocemos | 4 |
| 13:00 a 15:00 | Cierre: por qué servidor propio y no N8N, lo que mejoraríamos, preguntas | 1 |

## Casos con el público (3:00 a 6:30)
Lo que debe pasar, medido con el agente real:
| Escriben | Debe pasar | Qué señalar |
|---|---|---|
| «¿Qué sedes hay en Ibagué?» | Consulta la tabla de sedes y lista direcciones y horarios exactos | En la terminal: la herramienta `consultar_datos` con sus argumentos validados |
| «¿Cuántas tiendas Celsia hay?» | Responde 21, el total lo cuenta el código, no el modelo | El modelo no suma: cita el «Total» de la herramienta |
| «¿Qué es Celsia Solar?» o «¿Qué es la energía renovable?» | Busca en el texto oficial (`buscar_en_base`) y responde con lo que encuentra | Es el RAG sobre Qdrant; con el prompt v7 las preguntas de energía ya no se rechazan |
| «¿Quién ganó el mundial de 2014?» | Rechaza con cortesía y ofrece ayuda con temas de Celsia | El prompt v7 prohíbe responder con conocimiento propio |
| «¿Cuánto cuesta un cargador de carro eléctrico?» | Dice «No tengo esa información» (el sitio no trae el precio) y da la línea 01 8000 112 115 | Prefiere no inventar: es una decisión de diseño |

Evitar en vivo: «¿Cuánto cuesta reconectar el servicio?» (gasta muchos tokens y tarda) y preguntas de Cali sobre sedes (no hay filas).

## Memoria que sobrevive al reinicio (6:30 a 9:00)
1. Desde un teléfono: «Me llamo Laura y vivo en Palmira» → el bot lo guarda y lo confirma.
2. En la terminal 1: Ctrl+C y `make api` otra vez (unos 20 s; PostgreSQL sigue encendido). Decir lo que se prueba: el proceso murió y la conversación vive en PostgreSQL (`PostgresSaver`), por teléfono (el número no se guarda, se guarda su hash).
3. Desde el mismo teléfono: «¿Cómo me llamo y dónde vivo?» → responde Laura y Palmira.
4. Si no responde bien, repetir con «¿Qué sabes de mí?».

## Reclamo con aprobación humana (9:00 a 11:30)
1. Desde un teléfono registrado: «Quiero poner un reclamo: llevo dos días sin luz en Cali, barrio San Fernando». El bot pide lo que falte y responde que **quedó en revisión**, sin dar número de radicado.
2. En la terminal 2 se ve el aviso `pendiente de aprobación … radicar_reclamo`. Decir: el flujo está pausado por `HumanInTheLoopMiddleware`; nadie radicó nada todavía.
3. Aprobar como persona de Celsia (PowerShell; el token es `APROBADOR_TOKEN` de `.env`, y el teléfono el del cliente, con indicativo):

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/aprobar -Headers @{ "X-Aprobador" = "<APROBADOR_TOKEN>" } -ContentType "application/json" -Body '{"telefono":"57300XXXXXXX","decision":"aprobar"}'
```

4. Al teléfono del cliente llega la decisión; si se aprobó, con el número de radicado (`REC-…`). Probar también `"decision":"rechazar"` si sobra tiempo.
5. Señalar: un argumento inválido (por ejemplo, sin ciudad) ni siquiera llega a la persona que aprueba: se corrige antes de pausar.

## Qué tan bien lo hace (11:30 a 13:00)
Abrir `notebooks/analisis_conversaciones.ipynb` y mostrar el mapa t-SNE:
- Son 114 conversaciones **simuladas** (se dice en voz alta), pasadas por el agente real. Los vectores sí separan los temas: reclamos juntos, datos personales juntos, preguntas de producto en tres grupos.
- De 20 conversaciones marcadas como fallidas, 15 son rechazos correctos, 3 son datos que no están en la base y 2 son fallos reales (rechazos erróneos de preguntas de energía, que el prompt v7 corrige). La tasa real es de unos 5 en 114.
- Límites que decimos nosotros antes de que pregunten: la prueba con Meta se hizo con un número de prueba; el reclamo se radica en un registro simulado, no en el sistema de Celsia; los datos del análisis no son de clientes reales.

## Cierre (13:00 a 15:00)
- **Por qué servidor propio y no N8N.** Un solo servicio (FastAPI) en vez de dos sistemas que mantener; la firma del webhook, el límite por teléfono, la aprobación humana y el reintento de Meta se prueban con pruebas automáticas; el estado vive en nuestra base y no en el flujo de una herramienta externa. N8N habría sido más rápido de armar y más fácil de modificar sin código; lo que se pierde es esa velocidad y el editor visual.
- **Qué mejoraríamos:** desplegar en un servidor fijo (hoy el túnel cambia de dirección), un sistema real de radicación, más contenido en la base (precios, fechas) y más pruebas con conversaciones reales.

## Ayudas opcionales para la demostración
- **Panel en vivo.** En una pestaña aparte: `http://127.0.0.1:8000/panel`, con el `APROBADOR_TOKEN` de `.env`. Cada mensaje que llega aparece con la herramienta que eligió el agente, lo que tardó y cómo terminó. Se proyecta durante «Casos con el público». Muestra lo que escriben, así que se avisa al público.
- **Aprobar con botones.** Con `APROBADOR_WHATSAPP=<teléfono de quien aprueba>` en `.env`, el reclamo le llega a esa persona por WhatsApp con «Aprobar» y «Rechazar». Hay que haberle escrito al número de prueba en las últimas 24 horas (si no, Meta no entrega el mensaje) y estar entre los destinatarios de prueba. **No se ha probado con Meta real:** ensayarlo antes y, si falla, usar `POST /aprobar` como arriba.
- **Notas de voz (tentativo).** Apagado por defecto. No lo mostramos en vivo; si se ensaya, ver `src/taaml/voz.py`.
- **Menú, `/nuevo` y «escribiendo…».** Quien escribe «Hola», «menú» o «ayuda» recibe tres botones (Sedes y canales, Poner un reclamo, Celsia Solar) sin gastar el modelo; si Meta no entrega los botones, el menú va como texto. Tocar un botón es una pregunta normal al agente. `/nuevo` borra la conversación para empezar de cero (conserva lo que el agente sabe del cliente; no funciona con un reclamo pendiente: sirve para repetir la demostración con el mismo teléfono). Cada mensaje se marca como leído y muestra «escribiendo…». **Nada de esto se ha probado con Meta real**: ensayarlo antes.
- **Preguntas incómodas.** `make preguntas-hostiles` (gasta unas 15 a 25 llamadas) le hace al agente real 12 preguntas tipo profesor (ambigua, fuera de alcance, celular del gerente, competencia, insulto, reclamo dado por hecho…). La regla automática solo mira patrones: hay que **leer** cada respuesta antes de la demo.
- **Informe final.** `make informe-borrador` arma el esqueleto del informe con lo que hay en el repo y marca con «COMPLETAR» lo que escribe el equipo.
- **Chats reales para el t-SNE.** Los ensayos con otros celulares quedan guardados en PostgreSQL. Después, `make exportar-chats` los deja en `data/analisis/reales/` (no se suben a Git). Avisar antes a quienes escriban que sus mensajes se guardan.

## Si algo falla
| Falla | Qué hacer |
|---|---|
| El bot no responde por WhatsApp | Revisar la terminal: si no llega el aviso, el túnel o el webhook de Meta no están bien registrados (la dirección cambió); si llega pero no responde, el token de Meta venció o el teléfono no es destinatario de prueba. Pasar al plan B |
| El profesor no recibe respuesta | Probablemente no está en los destinatarios de prueba. Que escriba un integrante desde un teléfono registrado mientras se explica |
| Meta no entrega nada | **Plan B:** la misma API por `POST /chat` desde PowerShell (`Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body '{"mensaje":"Hola","telefono":"57300XXXXXXX"}'`) o el frontend React (`make app`). Decir que Meta no está entregando y que el agente es el mismo |
| Meta, el túnel o la red caen del todo | **Plan B grabado:** `make demo-plan-b` repite en pantalla una conversación real con el agente. Decir en voz alta que es una repetición grabada: la pantalla también lo avisa en cada mensaje |
| La respuesta tarda más de 40 s | Esperar sin tocar nada; pasar al siguiente caso si pasa de un minuto |
| Un solo teléfono escribe muy seguido | El bot responde una vez «estás escribiendo muy rápido» y no gasta cuota (límite de 8 mensajes por minuto por teléfono) |
| Gemini o DeepSeek no responden | El agente cae solo al modelo de respaldo; es más lento y acierta menos. Decirlo y seguir |
| Ollama apagado | `buscar_en_base` cae a búsqueda por palabras; las tablas siguen funcionando. Encenderlo y repetir |
