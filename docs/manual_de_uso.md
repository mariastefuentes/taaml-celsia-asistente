# Manual de uso del asistente de Celsia

Proyecto académico del Grupo 4 (UAO). **No es un servicio oficial de Celsia**: los reclamos, los reportes de daño y las solicitudes de asesor son simulados.

Para instalarlo, ver el [README](../README.md) y la [guía de despliegue](guia_despliegue_openclaw.md).

## 1. Si usted es la persona que pregunta

**Cómo entrar.** Escanee el código QR con la cámara del celular y envíe el «Hola» que ya viene escrito. No hay que instalar nada ni estar en una lista. También hay un chat web en el computador del proyecto.

### Qué puede pedir

| Para | Escriba, por ejemplo |
|---|---|
| Preguntar por un tema del sitio de Celsia | «¿Qué es una granja solar?» |
| Encontrar una sede y su horario | «¿Qué sedes hay en Ibagué?» |
| Saber si hay atención en su ciudad | «¿Hay atención presencial en Tuluá?» |
| Un teléfono o un correo | «¿Cuál es la línea de atención y el correo?» |
| Pagar o hacer un trámite en línea | «¿Dónde pago mi factura en línea?» |
| Saber si un número es de Celsia | «Me llamaron del 300 123 4567, ¿ese número es de ustedes?» |
| Calcular un estimado | «Consumí 150 kWh y la tarifa es de 900 pesos por kWh, ¿cuánto pago?» |
| Saber qué se hace con sus datos | «¿Qué hacen con mis datos?» |

El cálculo es un estimado con las cifras que usted da: no es su factura.

### La fuente de una respuesta

Escriba **«fuente»** o **«¿de dónde sacaste eso?»** justo después de la respuesta. Recibe el documento, el número de fragmento y el enlace. Si la última respuesta salió de una lista (por ejemplo, sedes o contactos) y no de un texto del sitio, se lo dice.

### Lo que el asistente recuerda de usted

- Guardar: «Me llamo Ana y vivo en Ibagué, recuérdalo.»
- Consultar: «¿Qué datos míos tienes guardados?»
- Borrar uno: «Olvida que vivo en Ibagué.»

Borrar un dato lo quita de lo que recuerda, pero no borra la conversación. Para borrar todo, ver la [política de privacidad](politica_de_privacidad.md).

**No escriba cédulas, claves, datos de tarjetas ni datos de salud.**

### Reclamos y daños

1. Pida: «Radica un reclamo de facturación en Palmira: me cobraron dos veces.» El asistente necesita al menos la ciudad y lo que pasó.
2. Le responde que **una persona lo está revisando**. Todavía no hay número.
3. Cuando esa persona aprueba, recibe el número (`REC-…` para reclamos, `DAN-…` para daños). Si el aviso no le llega solo, escriba «hola»: sale con la respuesta.
4. Después puede preguntar «¿Qué reclamos tengo?», «¿Cómo va el REC-…?» o pedir «Cancela el reclamo REC-…» (la cancelación también la aprueba una persona).

Si hay un **cable caído, chispas o humo**, aléjese y llame a la línea de emergencias **123**.

Para hablar con una persona escriba «Quiero hablar con una persona»: queda registrado el pedido y recibe los canales oficiales. No se promete una llamada.

### Límites

- Solo atiende temas de Celsia. Si no tiene un dato, dice «No tengo esa información».
- Máximo 8 mensajes por minuto desde un mismo número.
- Una respuesta puede tardar; el primer mensaje después de encender el sistema es el más lento.
- Puede equivocarse: confirme lo importante en la línea 01 8000 112 115.

## 2. Si usted aprueba reclamos

1. En el computador del bot abra `http://127.0.0.1:8000/panel`, escriba la clave `APROBADOR_TOKEN` y pulse **Ver**.
2. Lo que espera decisión aparece arriba, en **Por aprobar**, sin el teléfono de la persona.
3. Pulse **Aprobar** o **Rechazar**.
4. El resultado se le envía a la persona por WhatsApp (requiere los avisos activados). Si no se pudo enviar, el panel lo dice y le llega con su siguiente mensaje.

El panel muestra además las herramientas usadas, el tiempo, el costo y, en **Ver respuesta**, lo que se contestó. Las cuentas vuelven a cero cuando se reinicia la API. El índice de pendientes se guarda en la base de memoria y sobrevive a reiniciar la API; las filas del panel sí se reinician.

## 3. Si usted enciende el sistema

1. Abra Docker Desktop y espere a que diga que está corriendo.
2. En la carpeta del proyecto: `make api`.
3. En otra ventana: `openclaw gateway`.
4. Abra `http://127.0.0.1:8000/api/salud`. Debe decir `"estado":"ok"`, `"almacen":"qdrant"`, `"memoria":"postgresql"` y `"avisos_openclaw":true`.
5. Envíe un mensaje de prueba desde un celular y espere la respuesta antes de que lleguen los invitados. El primero puede tardar varios minutos o fallar con un aviso en inglés («OpenClaw couldn't finish this request»): envíe otro hasta que conteste bien.
6. Deje el computador conectado a la corriente, sin suspenderse y con las dos ventanas abiertas.

| Si pasa esto | Haga esto |
|---|---|
| `almacen` dice `numpy` | Quedó abierto un servidor viejo: ciérrelo y vuelva a correr `make api`. Si sigue, `make indice` |
| `avisos_openclaw` dice `false` | Falta `OPENCLAW_AVISOS=1` o `CHAT_TOKEN`; ver la guía de despliegue |
| WhatsApp no contesta | `openclaw channels status --probe` y revisar las dos ventanas |
| No vuelve WhatsApp | Chat web (`make chat-web`) o el plan de contingencia de la guía de despliegue |
