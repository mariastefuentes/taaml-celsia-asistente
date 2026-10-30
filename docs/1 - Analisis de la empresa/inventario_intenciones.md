# Inventario de intenciones: Celsia (definido desde el recorrido del cliente nuevo)

Generado automáticamente desde `inventario_intenciones.csv` (que se puede editar en Excel). Una **intención** es lo que el cliente quiere lograr.

**Cómo se definió.** El enunciado pide definir qué debería poder preguntar un cliente que interactúa por primera vez con la empresa, y da seis **ejemplos** (horarios, sedes, productos, historia, contacto y procesos básicos). Los ejemplos no son una lista cerrada: se recorrió todo el trayecto de un cliente nuevo (conocer la empresa, evaluarla, contratar, usar el servicio, resolver problemas) preguntando qué querría saber una persona nueva (hogar, pyme o empresa), **sin mirar antes si el sitio lo responde**. Eso hizo aparecer tres tipos más: confianza y regulación, calidad y evaluación, y derechos y datos. Después se contrastó con la base de conocimiento. Las que no tienen respuesta están al final, con el motivo.

**Ampliación del alcance (27/10/2026).** El objetivo del asistente es responder cualquier pregunta que el sitio oficial conteste, no solo las de un cliente nuevo. Por eso la base pasó de 107 a más de 350 documentos (sostenibilidad, inversionistas, proyectos, regulación y más) y se agregaron intenciones de esos temas (códigos J) y tres tipos de pregunta nuevos. Las que antes no tenían respuesta por haber sido excluidas (comprar acciones, quién dirige Celsia, plazo de una PQR) pasaron al alcance.

## Resumen por tipo de pregunta

| Tipo | Intenciones | Con respaldo | Con una sola fuente | Sin respuesta en la base |
|---|---|---|---|---|
| horarios | 2 | 2 | 0 | 1 |
| sedes | 2 | 2 | 1 | 2 |
| productos y servicios | 16 | 16 | 4 | 1 |
| historia y empresa | 12 | 12 | 1 | 2 |
| contacto | 6 | 6 | 2 | 0 |
| procesos básicos | 27 | 27 | 8 | 7 |
| confianza y regulación | 1 | 1 | 0 | 0 |
| calidad y evaluación | 0 | 0 | 0 | 1 |
| derechos y datos | 0 | 0 | 0 | 4 |
| sostenibilidad y proyectos | 2 | 2 | 0 | 0 |
| inversionistas y gobierno corporativo | 2 | 2 | 0 | 0 |
| regulación y autogeneración | 1 | 1 | 0 | 0 |

**Total:** 72 intenciones en el alcance (72 con respaldo, 16 con una sola fuente) y 17 preguntas típicas de un cliente nuevo que hoy la base no responde. **Momento del cliente** (dentro del alcance): ambos: 20; cliente actual: 17; primer contacto: 34. «Primer contacto» es lo que pregunta quien interactúa por primera vez; «cliente actual» quien ya tiene el servicio; «ambos» sirve a los dos.

## Fallas y daños (3)

| ID | Tipo | Momento | Intención | Ejemplos de pregunta | Región | Fuente de origen | Docs | Estado |
|---|---|---|---|---|---|---|---|---|
| A1 | procesos básicos | cliente actual | Reportar que no tengo servicio de energía o un daño en la red | Se fue la luz en mi casa, ¿dónde reporto? / ¿Cómo reporto un daño? | Valle y Tolima | Portada (acceso directo «Reporta un daño»); blog de trámites | 13 | cubierta |
| A2 | procesos básicos | cliente actual | Saber de mantenimientos o cortes programados | ¿Habrá corte de luz esta semana en mi barrio? / ¿Dónde veo los mantenimientos? | Valle y Tolima | Portada y menú («Mantenimientos programados») | 6 | cubierta |
| A3 | procesos básicos | cliente actual | Reclamar por electrodomésticos dañados por bajones de energía | Se me quemó la nevera por un bajón, ¿Celsia responde? / ¿Qué datos necesito para el reclamo? | Valle y Tolima | Blog de trámites (siniestros); Mitos y verdades | 2 | cubierta |

## Factura y pagos (13)

| ID | Tipo | Momento | Intención | Ejemplos de pregunta | Región | Fuente de origen | Docs | Estado |
|---|---|---|---|---|---|---|---|---|
| B1 | procesos básicos | cliente actual | Pagar la factura de energía (dónde y cómo) | ¿Dónde pago mi factura? / ¿Se puede pagar en línea? | Valle y Tolima | Portada (acceso directo); blog de pagos | 3 | cubierta |
| B2 | procesos básicos | cliente actual | Pagar con canales digitales o Bre-B | ¿Puedo pagar con Bre-B? / ¿Qué canales digitales hay para pagar? | General | Blog de pagos digitales | 46 | cubierta |
| B3 | procesos básicos | cliente actual | Abonar, hacer un acuerdo de pago o pagar en Tolima | ¿Cómo abono a mi factura? / Quiero un acuerdo de pago | Tolima | Blog de pagos (Tolima y acuerdo de pago) | 4 | cubierta |
| B4 | procesos básicos | cliente actual | Activar la factura digital (y qué pasa si vivo en arriendo o si quiero darme de baja) | ¿Cómo recibo la factura por correo? / Vivo en arriendo, ¿puedo suscribirme? / ¿Cómo me desuscribo? | Valle y Tolima | Portada; blog «Preguntas frecuentes factura digital» | 3 | cubierta |
| B5 | procesos básicos | cliente actual | Encontrar mi código de cuenta | ¿Dónde veo mi código de cuenta? | Valle y Tolima | Blog de factura digital y de trámites | 9 | cubierta |
| B6 | procesos básicos | cliente actual | Entender los conceptos de mi factura | ¿Qué significa cada cobro de mi factura? / ¿Qué es el cargo por…? | General | Blog «Factura de energía Celsia: conceptos y cómo entenderla» | 72 | cubierta |
| B7 | procesos básicos | cliente actual | Saber por qué subió el valor de mi factura | ¿Por qué me llegó más cara la factura? | General | Blog «causas del aumento en el valor de tu factura» | 2 | cubierta |
| B8 | procesos básicos | cliente actual | Entender el cobro de aseo y alumbrado público, y quién responde por el alumbrado | ¿Por qué cobran alumbrado público? / ¿Celsia arregla las luces del parque? | General | Blog «aseo y alumbrado público»; Mitos y verdades | 14 | cubierta |
| B9 | procesos básicos | cliente actual | Conocer los subsidios y el consumo de subsistencia | ¿Qué es el consumo de subsistencia? / ¿Hay subsidio para estrato 3? | Valle y Tolima | Blog de subsidios y consumo de subsistencia | 12 | cubierta |
| B10 | procesos básicos | ambos | Entender las tarifas y si bajaron | ¿Por qué es tan cara la tarifa? / ¿Bajaron las tarifas? | Valle y Tolima | Mitos y verdades; blog «Redujimos nuestras tarifas» | 18 | cubierta |
| B11 | procesos básicos | cliente actual | Consultar o descargar mi factura, duplicados y mi historial | ¿Cómo descargo un duplicado de mi factura? / ¿Dónde veo mi consumo? | Valle y Tolima | Blog «Nuevo acceso seguro a Zona Clientes» | 1 | cubierta (1 fuente) |
| B12 | procesos básicos | cliente actual | Pagar la factura de internet | ¿Dónde pago mi internet de Celsia? | General | Portada (acceso directo) | 2 | cubierta |
| B13 | procesos básicos | ambos | Pagar de forma segura y evitar fraudes | ¿Cómo evito que me estafen al pagar? / ¿Cuáles son los canales oficiales? | General | Blog «Que no te engañen» | 35 | cubierta |

## Trámites (9)

| ID | Tipo | Momento | Intención | Ejemplos de pregunta | Región | Fuente de origen | Docs | Estado |
|---|---|---|---|---|---|---|---|---|
| C1 | procesos básicos | primer contacto | Solicitar un nuevo servicio de energía | ¿Qué documentos necesito para pedir luz en mi vivienda nueva? | Valle y Tolima | Blog de trámites | 1 | cubierta (1 fuente) |
| C2 | procesos básicos | ambos | Cambiar el estrato | ¿Cómo cambio el estrato de mi vivienda? | Valle y Tolima | Blog de trámites | 1 | cubierta (1 fuente) |
| C3 | procesos básicos | ambos | Cambiar el titular o el nombre de la cuenta | ¿Cómo pongo la cuenta a mi nombre? | Valle y Tolima | Blog de trámites | 2 | cubierta |
| C4 | procesos básicos | cliente actual | Cancelar el servicio o la matrícula | ¿Cómo cancelo mi servicio de energía? (el trámite cambia entre Valle y Tolima) | Valle y Tolima | Blog de trámites | 1 | cubierta (1 fuente) |
| C5 | procesos básicos | ambos | Presentar una PQR y obtener el radicado | ¿Cómo pongo una queja? / ¿Dónde hago un reclamo? | Valle y Tolima | Portada (acceso directo PQR); blog de trámites | 22 | cubierta |
| C6 | procesos básicos | cliente actual | Registrarme o iniciar sesión en la Zona Clientes | ¿Cómo creo mi perfil en Zona Clientes? / ¿Por qué me piden registrarme? | Valle y Tolima | Blog «Nuevo acceso seguro» (desde 15/09/2025); Zona Clientes | 2 | cubierta |
| C7 | procesos básicos | ambos | Autorizar o limitar que Celsia me contacte (Ley 2300) | ¿Cómo autorizo que me contacten? / ¿Cómo evito llamadas de cobranza? | General | Formulario Ley 2300 | 1 | cubierta (1 fuente) |
| C8 | procesos básicos | ambos | Saber qué pasa si no pago a tiempo (mora, suspensión y reconexión) | ¿Me cortan la luz si me atraso? / ¿Cobran intereses? | Valle y Tolima | Aviso de canales digitales (06/2026) | 1 | cubierta (1 fuente) |
| H12 | procesos básicos | cliente actual | Saber en cuánto tiempo responden una PQR | Puse una queja, ¿en cuánto tiempo me responden? (la apelación no está en la base) | General | Pregunta típica al reclamar | 1 | cubierta (1 fuente) |

## Atención y sedes (10)

| ID | Tipo | Momento | Intención | Ejemplos de pregunta | Región | Fuente de origen | Docs | Estado |
|---|---|---|---|---|---|---|---|---|
| D1 | contacto | primer contacto | Conocer el teléfono, el WhatsApp y el correo de atención de energía | ¿Cuál es la línea de atención? / ¿Tienen WhatsApp? | General | Menú; página Encuéntranos | 6 | cubierta |
| D2 | sedes | primer contacto | Encontrar una sede o punto de atención y su horario | ¿Dónde hay una Tienda Celsia en Palmira? / ¿A qué hora abren? | Valle y Tolima | Menú «Puntos de atención»; capa pública de sedes | 4 | cubierta |
| D3 | contacto | primer contacto | Contactar a Celsia Internet | ¿Cuál es el WhatsApp del internet? / ¿Cómo hablo con soporte de internet? | General | Página «Contáctenos Internet» | 2 | cubierta |
| D4 | contacto | ambos | Usar la línea de transparencia | ¿Cómo denuncio una irregularidad? | General | Página Encuéntranos | 1 | cubierta (1 fuente) |
| D5 | horarios | ambos | Saber el horario de la línea telefónica | ¿A qué hora atienden por teléfono? / ¿Atienden los domingos? | General | Avisos de Celsia sobre fraude (2021): la línea 01 8000 112 115 «está disponible las 24 horas del día de lunes a domingo». Dato antiguo: verificar | 7 | cubierta |
| D6 | horarios | primer contacto | Saber si atienden sábados, domingos y festivos | ¿Atienden los sábados? / ¿Abren en festivos? | Valle y Tolima | Horarios de las 58 sedes | 2 | cubierta |
| D7 | sedes | primer contacto | Saber si hay una sede o punto en mi ciudad | ¿Tienen oficina en Cali? / ¿Dónde pago en Ibagué? | Valle y Tolima | Lista pública de sedes (33 ciudades; no incluye Cali) | 1 | cubierta (1 fuente) |
| D8 | contacto | primer contacto | Encontrar las redes sociales oficiales de Celsia | ¿Cuál es el Instagram de Celsia? | General | Pie de celsia.com (resumido en el documento manual) | 1 | cubierta (1 fuente) |
| D9 | contacto | primer contacto | Contactar a un asesor comercial (hogares, pymes y empresas) | ¿Con quién hablo para una cotización de mi empresa? | General | Menú «Empresas» y portal empresas.celsia.com | 54 | cubierta |
| K3 | contacto | ambos | Conocer a Luz I.A., la asistente virtual de voz | ¿Qué es Luz I.A.? / ¿Hay un asistente de voz? | General | Blog «Conoce a Luz I.A.» | 2 | cubierta |

## Servicios para hogares (10)

| ID | Tipo | Momento | Intención | Ejemplos de pregunta | Región | Fuente de origen | Docs | Estado |
|---|---|---|---|---|---|---|---|---|
| E1 | productos y servicios | primer contacto | Instalar paneles solares en mi casa (beneficios y requisitos) | ¿Cuánto me ahorro con paneles solares? / ¿Qué necesito para instalarlos? | General | Menú «Hogares»; blogs de energía solar | 33 | cubierta |
| E2 | productos y servicios | primer contacto | Instalar un cargador para vehículo eléctrico en casa | ¿Celsia instala cargadores para carro eléctrico? | General | Blog de cargadores | 2 | cubierta |
| E3 | productos y servicios | primer contacto | Comprar en la Tienda Celsia (electrodomésticos eficientes) | ¿Dónde compro electrodomésticos de bajo consumo con Celsia? | General | Blog «Tienda Celsia Virtual» | 4 | cubierta |
| E4 | productos y servicios | primer contacto | Conocer el servicio de internet de Celsia y su calidad | ¿Qué ofrece Celsia Internet? / ¿Por qué va lenta mi conexión? | General | Menú «Internet» | 1 | cubierta (1 fuente) |
| E5 | productos y servicios | ambos | Ahorrar energía y medir mi consumo | ¿Cómo reduzco mi consumo? / ¿Cómo mido cuánto gasto? | General | Blogs de ahorro y consumo | 7 | cubierta |
| E6 | productos y servicios | ambos | Seguridad eléctrica en el hogar | ¿Por qué debo contratar un electricista certificado? | General | Blog de electricistas | 1 | cubierta (1 fuente) |
| E7 | productos y servicios | primer contacto | Instalar energía solar fuera de la red o con contrato PPA | ¿Puedo tener paneles solares en una finca sin red? / ¿Qué es un contrato PPA? | General | Blogs «Requisitos para instalar energía solar» y «Genera energía solar para tu casa o empresa» | 10 | cubierta |
| E8 | productos y servicios | primer contacto | Comprar electrodomésticos financiados desde la factura | ¿Puedo pagar un electrodoméstico en cuotas con la factura de energía? | General | Blogs de la Tienda Celsia y de la factura | 3 | cubierta |
| E9 | productos y servicios | primer contacto | Conocer los planes y precios de Celsia Internet | ¿Cuánto cuesta el internet de Celsia? / ¿Qué velocidades tienen? | Valle, Tolima y Cundinamarca | www.celsiainternet.com (sitio oficial de internet) | 1 | cubierta (1 fuente) |
| J3 | productos y servicios | ambos | Conocer el distrito térmico de Serena del Mar (aire acondicionado) | ¿Qué es el distrito térmico de Serena del Mar? | General | Blog del 18/09/2024 | 11 | cubierta |

## Pymes y empresas (7)

| ID | Tipo | Momento | Intención | Ejemplos de pregunta | Región | Fuente de origen | Docs | Estado |
|---|---|---|---|---|---|---|---|---|
| F1 | productos y servicios | primer contacto | Soluciones de eficiencia energética para pymes | ¿Qué ofrece Celsia a mi negocio? | General | Menú «Pymes» | 1 | cubierta (1 fuente) |
| F2 | productos y servicios | primer contacto | Energía solar para empresas y pymes | ¿Cómo instalo energía solar en mi empresa? | General | Menú «Empresas» | 2 | cubierta |
| F3 | productos y servicios | primer contacto | Eficiencia energética, iluminación y calidad de la energía | ¿Cómo mejoro la calidad de energía de mi planta? | General | Menú «Empresas» | 18 | cubierta |
| F4 | productos y servicios | primer contacto | Energía de respaldo y cogeneración | ¿Tienen plantas de respaldo para mi empresa? | General | Menú «Empresas» | 22 | cubierta |
| F5 | productos y servicios | primer contacto | Conectar un proyecto o comprar energía (constructoras y grandes clientes) | ¿Cómo conecto mi proyecto inmobiliario? | General | Menú «Empresas»; blog de trámites | 26 | cubierta |
| F6 | productos y servicios | primer contacto | Ahorrar energía en una copropiedad o edificio | ¿Cómo bajo la tarifa en mi conjunto residencial? | General | Blogs de copropiedades y edificios | 5 | cubierta |
| F7 | procesos básicos | primer contacto | Cambiarse a Celsia como comercializador de energía (empresas) | ¿Puedo comprarle energía a Celsia para mi empresa? | General | Página «Energía Eléctrica» para empresas | 1 | cubierta (1 fuente) |

## Sobre Celsia (14)

| ID | Tipo | Momento | Intención | Ejemplos de pregunta | Región | Fuente de origen | Docs | Estado |
|---|---|---|---|---|---|---|---|---|
| G1 | historia y empresa | primer contacto | Saber qué es Celsia y qué hace | ¿Qué es Celsia? / ¿A qué se dedica? | General | Menú «Quiénes somos» | 6 | cubierta |
| G2 | historia y empresa | primer contacto | Saber de qué grupo hace parte y dónde opera | ¿Quién es el dueño de Celsia? / ¿En qué países está? | General | Menú «Quiénes somos» | 42 | cubierta |
| G3 | historia y empresa | primer contacto | Conocer la historia de la empresa | ¿Desde cuándo existe Celsia? / ¿Cuándo cambió de nombre? | General | Menú «Quiénes somos» | 2 | cubierta |
| G4 | historia y empresa | primer contacto | Saber de dónde viene la energía que generan | ¿Su energía es renovable? | General | Menú «Qué hacemos» | 106 | cubierta |
| G5 | historia y empresa | primer contacto | Conocer su gestión de sostenibilidad | ¿Qué es Celsia PermaneC? | General | Menú «Sostenibilidad» | 24 | cubierta |
| G6 | historia y empresa | primer contacto | Conocer los programas sociales y la Fundación | ¿Qué hace la Fundación Celsia? | General | Menú «Fundación» | 15 | cubierta |
| G7 | procesos básicos | primer contacto | Trabajar en Celsia | ¿Cómo envío mi hoja de vida? | General | Menú «Sé parte de nuestro equipo» | 2 | cubierta |
| G8 | historia y empresa | ambos | Entender las mejoras de servicio y los mitos más comunes | ¿Es cierto que Celsia es la más cara? / ¿Qué inversiones hacen en mi región? | Valle y Tolima | Mitos y verdades; Inversiones para mejorar el servicio | 8 | cubierta |
| G9 | historia y empresa | primer contacto | Entender qué diferencia a Celsia, EPSA y Cetsa | ¿Es lo mismo EPSA que Celsia? | Valle y Tolima | Perfiles corporativos y asambleas de celsia.com (resumidos en el documento manual) | 11 | cubierta |
| G10 | historia y empresa | primer contacto | Conocer la cultura, el propósito y los valores de Celsia | ¿Cuál es el propósito de Celsia? / ¿Cómo es trabajar allí? | General | Menú «Cultura Celsia» | 5 | cubierta |
| G12 | confianza y regulación | primer contacto | Saber quién regula y vigila a Celsia | ¿Celsia decide cuánto cobra? / ¿Quién la vigila? | General | Blog «Factura de energía Celsia: conceptos»; «Mitos y verdades» | 3 | cubierta |
| J5 | historia y empresa | ambos | Conocer el pódcast de Celsia | ¿Quiénes conducen el pódcast de Celsia? | General | Página del pódcast | 3 | cubierta |
| K1 | historia y empresa | primer contacto | Saber quién es el dueño o accionista controlante de Celsia | ¿Quién es el dueño de Celsia? / ¿Es de Grupo Argos? | General | Estructura societaria (celsia.com/inversionistas) | 3 | cubierta |
| K2 | historia y empresa | primer contacto | Saber cuántas personas trabajan en Celsia | ¿Cuántos empleados tiene Celsia? | General | Blog sobre la planta Caracolito de Cemex | 1 | cubierta (1 fuente) |

## Sin respuesta en la base (18)

Preguntas que un cliente nuevo haría y la base no responde. El asistente debe reconocerlo y remitir a un canal oficial. Si alguna llegara a aparecer en el corpus, su estado cambia solo.

| ID | Tipo | Pregunta | Ejemplos | Por qué no se responde |
|---|---|---|---|---|
| H1 | productos y servicios | Saber el precio de paneles solares u otros productos y pedir una cotización | ¿Cuánto cuesta instalar paneles solares? / ¿Cómo pido una cotización? | El sitio no publica precios de paneles solares ni otros productos; se cotiza con un asesor |
| H2 | procesos básicos | Saber cuánto demora una conexión o instalación | ¿Cuánto tardan en instalarme la luz? | Celsia no publica el plazo; la regulación general (CREG) fija plazos y el Contrato de condiciones uniformes está en PDF bloqueado |
| H3 | sedes | Saber en qué municipios hay cobertura | ¿Celsia llega a mi pueblo? | No hay una cifra oficial vigente de municipios atendidos; las sedes dan solo una lista parcial |
| H4 | procesos básicos | Ser proveedor o contratista de Celsia | ¿Cómo me inscribo como proveedor? | La base incluye la sección de proveedores (proceso de abastecimiento, requisitos de facturación, plataformas de apoyo), pero no explica cómo inscribirse |
| H8 | procesos básicos | Saber cuánto cuesta una conexión nueva | ¿Cuánto me cobran por conectarme? | El sitio no publica el costo de la conexión |
| H9 | horarios | Saber el horario del WhatsApp de atención | ¿A qué hora responden por WhatsApp? | El sitio no publica el horario del WhatsApp |
| H11 | calidad y evaluación | Saber qué tan confiable es el servicio en mi zona | ¿Qué tanto se va la luz en mi barrio? | El sitio no publica indicadores de calidad de la energía por zona (solo los de internet, en tablas descargables) |
| H13 | procesos básicos | Saber cuánto cuesta una reconexión | ¿Cuánto cobran por reconectarme? | Solo se advierte que hay costos; no se publican |
| H14 | derechos y datos | Saber cómo protegen mis datos personales y ejercer mis derechos | ¿Qué hacen con mis datos? / ¿Cómo pido que los borren? | La base solo menciona la política de tratamiento de datos y su objetivo; el texto completo (derechos del titular, cómo ejercerlos) está en un PDF que el robots.txt bloquea |
| H15 | derechos y datos | Saber si hay atención para personas con discapacidad o en otros idiomas | ¿Tienen atención en lengua de señas? | No aparece en el sitio |
| K4 | historia y empresa | Conocer la misión y la visión de Celsia | ¿Cuál es la misión y la visión de Celsia? | El sitio habla de la «Cultura Celsia» pero no publica un texto de misión y visión |
| K5 | historia y empresa | Saber el NIT de Celsia | ¿Cuál es el NIT de Celsia? | Las páginas descargadas no publican el NIT |
| K6 | sedes | Saber si Celsia Internet llega a mi barrio | ¿Celsia Internet tiene cobertura en mi barrio? | El sitio no publica un mapa ni una lista de zonas con Celsia Internet |
| K7 | procesos básicos | Saber qué hacer ante un cable caído | Vi un cable caído en la calle, ¿qué hago? | No hay una guía de seguridad; solo el canal para reportar un daño |
| K8 | derechos y datos | Saber cómo apelar una decisión de Celsia (recurso de reposición) | ¿Qué es un recurso de reposición? / ¿Cómo apelo? | El sitio no explica el recurso de reposición ni la apelación |
| K9 | derechos y datos | Consultar el contrato de condiciones uniformes | ¿Dónde veo mi contrato con Celsia? | El contrato está en un PDF que el robots.txt de celsia.com bloquea |
| K10 | procesos básicos | Saber del medidor inteligente o pedir el cambio del medidor | ¿Cómo me cambian el medidor? / ¿Qué es un medidor inteligente? | Solo menciona el «cambio de medidores» como inversión; no explica el trámite |
| K11 | procesos básicos | Trasladar mi servicio de energía a una nueva vivienda | Me estoy mudando, ¿cómo llevo mi servicio? | El sitio no describe el trámite de mudanza |

## Inversionistas y gobierno (2)

| ID | Tipo | Momento | Intención | Ejemplos de pregunta | Región | Fuente de origen | Docs | Estado |
|---|---|---|---|---|---|---|---|---|
| H5 | inversionistas y gobierno corporativo | ambos | Comprar acciones de Celsia o invertir | ¿Cómo compro acciones de Celsia? | General | Sección Inversionistas (excluida por no ser de cliente) | 6 | cubierta |
| H10 | inversionistas y gobierno corporativo | ambos | Saber quién dirige Celsia | ¿Quién es el presidente de Celsia? | General | Noticias y publicaciones de la empresa | 22 | cubierta |

## Sostenibilidad y proyectos (2)

| ID | Tipo | Momento | Intención | Ejemplos de pregunta | Región | Fuente de origen | Docs | Estado |
|---|---|---|---|---|---|---|---|---|
| J1 | sostenibilidad y proyectos | ambos | Saber qué hace Celsia por el medio ambiente (siembra de árboles) | ¿Cuántos árboles ha sembrado Celsia? / ¿Qué es ReverdeC? | General | Página «Programa ReverdeC y siembra de árboles» | 9 | cubierta |
| J2 | sostenibilidad y proyectos | ambos | Conocer las centrales y proyectos de generación de Celsia | ¿Qué es Salvajina? / ¿De cuántos MW es? | General | Página «Salvajina» y otras de activos y proyectos | 10 | cubierta |

## Regulación y autogeneración (1)

| ID | Tipo | Momento | Intención | Ejemplos de pregunta | Región | Fuente de origen | Docs | Estado |
|---|---|---|---|---|---|---|---|---|
| J4 | regulación y autogeneración | ambos | Saber si puedo producir y vender mi propia energía (autogeneración) | ¿Puedo vender la energía de mis paneles solares? / ¿Qué es un AGPE? | General | Blog sobre la resolución CREG; página regulatoria | 10 | cubierta |

## Atención: cobertura débil

- **B11** Consultar o descargar mi factura, duplicados y mi historial: cubierta (1 fuente)
- **C1** Solicitar un nuevo servicio de energía: cubierta (1 fuente)
- **C2** Cambiar el estrato: cubierta (1 fuente)
- **C4** Cancelar el servicio o la matrícula: cubierta (1 fuente)
- **C7** Autorizar o limitar que Celsia me contacte (Ley 2300): cubierta (1 fuente)
- **C8** Saber qué pasa si no pago a tiempo (mora, suspensión y reconexión): cubierta (1 fuente)
- **D4** Usar la línea de transparencia: cubierta (1 fuente)
- **D7** Saber si hay una sede o punto en mi ciudad: cubierta (1 fuente)
- **D8** Encontrar las redes sociales oficiales de Celsia: cubierta (1 fuente)
- **E4** Conocer el servicio de internet de Celsia y su calidad: cubierta (1 fuente)
- **E6** Seguridad eléctrica en el hogar: cubierta (1 fuente)
- **E9** Conocer los planes y precios de Celsia Internet: cubierta (1 fuente)
- **F1** Soluciones de eficiencia energética para pymes: cubierta (1 fuente)
- **F7** Cambiarse a Celsia como comercializador de energía (empresas): cubierta (1 fuente)
- **H12** Saber en cuánto tiempo responden una PQR: cubierta (1 fuente)
- **K2** Saber cuántas personas trabajan en Celsia: cubierta (1 fuente)
