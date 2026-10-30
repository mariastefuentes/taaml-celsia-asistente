# Inventario de fuentes públicas: Celsia

Taller 1, punto 1. Última actualización: 17/10/2026. Qué fuentes existen, si se pueden usar y qué decisión se tomó. El resumen de la estrategia está en [analisis_empresa.md](analisis_empresa.md). Todo lo que aparece aquí fue revisado el 17/10/2026; lo que no se pudo verificar se marca como tal.

## 1. Sitio oficial (celsia.com)

WordPress con HTML legible. `robots.txt`: `Disallow: /wp-admin/`, `/es/docs-inversionistas/11-de-mayo/` y **`/*.pdf$`** (los PDF no se descargan de forma automatizada).

| Sección | Sitemap | URLs | Decisión |
|---|---|---|---|
| Páginas generales | `/es/page-sitemap.xml` | 677 (la mitad son copias `/en/`) | **Descargadas 325 páginas `/es/`**: 273 conservadas, 28 casi vacías y 24 duplicados exactos descartados (otras 5 URLs dieron error y no se descargaron) |
| Blog | `/es/blog-celsia-sitemap.xml` | 252 (la mitad `/en/`) | **Descargadas 126 páginas `/es/`** |
| Noticias | `/es/noticias-sitemap.xml` | 1.646 (823 en español y 823 copias en inglés) | **Selección por tema y vigencia** (ver 1.1) |
| Mantenimientos programados | `/es/mantenimientos-sitemap.xml` | 1.326 | Excluida: información temporal de cortes (cada aviso vence a los pocos días) |
| Podcasts y libros | sitemaps propios | 68 y 18 | Excluidos |
| Puntos de atención | `/es/encuentranos/` | 1 | Sin texto en el HTML: incrusta un visor ArcGIS (`gis.celsia.com`). Se usa su capa pública de sedes: **58 sedes con dirección y horario** |

Dentro de las páginas generales, por tema: «Quiénes somos» y «Qué hacemos», soluciones para hogares, pymes y empresas, Celsia Internet, sostenibilidad e inversionistas. Las de inversionistas, regulatorio y las muy largas se filtran en la curaduría por ser técnicas para un cliente nuevo.

**Enlaces y botones que el sitio no muestra como texto** (WhatsApp, PQR, pago de facturas, Zona Clientes): se escribieron a mano, con su fuente, en `data/0_manual/canales_atencion.md`. Celsia Internet tiene canales propios, distintos a los de energía.

**Celsia Internet tiene sitio propio, `www.celsiainternet.com`**, con planes de 200 a 800 Mbps, precios por estrato (vigentes hasta el 30/11/2026), instalación gratis y validación de cobertura por dirección. El enlace `internet.celsia.com`, que aparece en el sitio de energía, ya no funciona. Los datos clave están en `data/0_manual/datos_complementarios.md`; los precios cambian, así que el asistente debe remitir al sitio para confirmarlos.

**Lista pública de sedes:** tiene 33 ciudades y no incluye Cali.

### 1.1 Noticias: la decisión depende del tema y de la vigencia
Descartarlas todas sería perder avisos útiles (fraudes, programa de ahorro, canales de pago); incluirlas todas llenaría la base de contenido vencido o corporativo. Por eso se decidió con datos:

- Se identificaron **71 noticias en español con tema de cliente** (por palabras del título: tarifa, factura, pago, estafa, subsidio, canales, ahorro…) y se descargaron 70 (una ya estaba), con pausa entre peticiones.
- El año de modificación del sitemap no sirve (902 URLs aparecen de 2021 por una actualización masiva), así que se extrajo la **fecha real de publicación** de cada página: van de 2017 a 2026, y solo 6 son de 2026 y 7 de 2025.
- **Regla R7 de la curaduría:** entra la noticia si trata un tema de cliente **y** tiene menos de 12 meses, o si es atemporal (avisos de fraude y explicaciones de la tarifa). El resto se excluye, con su motivo en el registro.
- **Resultado: entran 8 noticias**: 4 avisos de fraude o suplantación (el de Tuluá de octubre de 2026 y tres atemporales de 2021 y 2024), 2 sobre el programa de ahorro de energía de la CREG (septiembre y octubre de 2026), 1 sobre canales digitales de pago (junio de 2026) y 1 sobre la atención de la emergencia por el sismo (septiembre de 2026). Las 57 restantes se excluyen: 2 son recientes pero corporativas o locales (resultados financieros y jornadas en Venadillo), 1 quedó fuera por solo 3 días (canales de pago de octubre de 2025) y el resto está vencido (tarifas de 2020 a 2025, aperturas de tiendas, cortes de 2021, etc.).
- La regla es repetible: `uv run python scripts/01_scrape_celsia.py --sections noticias --filtro "..."` y luego los scripts de Silver, Gold y curaduría. Si el equipo quiere otro plazo (por ejemplo 24 meses), se cambia un número en `05_curar_base.py`.

## 2. Documentos PDF (informes)

Existen y son valiosos, pero el `robots.txt` de celsia.com bloquea los `.pdf`. **Decisión:** no se descargan, porque se respeta el `robots.txt`; sus datos no entran al corpus y se declara como limitación en el informe.

- Reporte integrado 2025 y 2024; informes ASG 2021 a 2023.
- Informe de gestión para accionistas 2025.
- Presentación corporativa (jun 2026) y resultados 2T-2026.
- Avance ODS 2025, informe TCFD 2025 e informe TNFD 2025.
- Copias en Grupo Argos (`files.grupoargos.com/uploads-grupo-argos/...`): su `robots.txt` no se pudo verificar.

## 3. Redes sociales

Los enlaces salen del propio sitio oficial. Se revisó qué se ve sin iniciar sesión.

| Red | Perfil | Qué se encontró | Utilidad para el asistente | Decisión |
|---|---|---|---|---|
| **LinkedIn** | `linkedin.com/company/celsiaenergia` | 227.713 seguidores. Lema «Ponemos ON la #TransiciónEnergética». Sede en Medellín. Se presenta como la empresa de energía del Grupo Argos y dice atender a más de 1,3 millones de hogares y empresas. Las publicaciones recientes son corporativas y financieras: la venta de la participación de EMCALI (18,06 %), el ranking Merco (subió del puesto 45 al 37), el precio objetivo de la acción, charlas y un pódcast. | **Baja** para el cliente. Útil solo como descripción institucional. | No se scrapea. Se cita la descripción de forma manual |
| **Instagram** | `instagram.com/celsia_energia` | Cuenta verificada, ~54.100 seguidores, enlace a `linktr.ee/celsia_`. Historias destacadas: «Meta de consumo», «¿Cómo hago?», reportar un daño, «CelsiaEnCasa», «Celsia a la calle» y pódcast. Publica carruseles, reels y contenido con humor. No se leyeron los textos de las publicaciones. | **Media-baja.** Sus destacados confirman intenciones ya cubiertas (meta de consumo, reportar daño). | No se scrapea. Confirma el alcance |
| **Facebook** | `facebook.com/celsia.energia` | Revisada el 27/10/2026 sin iniciar sesión: 94 mil seguidores, 819 opiniones (recomendada por el 24 %). La descripción repite la del sitio (1,3 millones de hogares y empresas; operador de red en 39 municipios del Valle del Cauca y 47 del Tolima) y publica el WhatsApp 310 3903468. No se leyeron las publicaciones. | **Baja.** Los datos de contacto coinciden con la base. | No se scrapea. Confirma el alcance |
| **X** | `x.com/Celsia_Energia` (antes twitter.com) | Revisada el 27/10/2026: publica enlaces a notas de prensa (por ejemplo, una de Forbes Colombia del 23/10/2026 sobre inversiones cercanas a US$6.000 millones). | **Baja.** Contenido corporativo y de prensa. | No se scrapea. Confirma el alcance |
| **YouTube** | `youtube.com/@celsiaenergia` | Revisada el 27/10/2026: 10,4 mil suscriptores y 725 videos. Los recientes tratan de cómo pagar la factura y de un seminario sobre el fenómeno de El Niño para empresas (1 h). | **Media-baja.** Hay videos instructivos, pero el contenido está en audio y video, no en texto. | No se transcribe. Se documenta |

**Conclusión:** donde se pudo ver, el contenido de redes es institucional, financiero o de comunicación de marca, y no sustituye las páginas del sitio para responder dudas de un cliente nuevo. Se documentan, no se scrapean (exigen sesión y tienen términos de uso restrictivos). Ojo: `@celarisenergy` es otra marca (Perú), no Celsia.

## 4. Medios de comunicación

Se buscaron apariciones concretas de Celsia en medios locales y nacionales. Las cifras son las que reportan los medios o la empresa, no verificadas de forma independiente.

| Fecha | Medio | Tema | Enlace | ¿Aporta al asistente? |
|---|---|---|---|---|
| 28/05/2026 | La República, La FM y El País | La Superservicios anuncia una evaluación integral a Celsia Colombia en Valle y Tolima (aspectos administrativos, financieros, técnicos, comerciales y tarifarios). No hay resultados todavía. | [La República](https://www.larepublica.co/economia/superservicios-inicio-vigilancia-de-servicio-electrico-de-celsia-en-valle-del-cauca-y-tolima-4402675), [La FM](https://www.lafm.com.co/economia/superservicios-inicia-evaluacion-a-celsia-400661), [El País](https://www.elpais.com.co/economia/superservicios-revisara-inversiones-continuidad-operativa-y-calidad-del-servicio-de-celsia-2844.html) | No: contexto regulatorio |
| 10/08/2026 (el hecho) | La República | Terremoto: cerca de 450.000 clientes del Valle quedaron sin servicio y el restablecimiento tardó días. Un comunicado del 10/09/2026 dice que se atendió el 100 % de las fallas causadas por el sismo. | [La República](https://www.larepublica.co/empresas/servicio-de-energia-en-el-valle-del-cauca-4456251) | Solo como contexto de emergencia; las cifras vienen de la empresa |
| 18 al 22/06/2026 | El País | Mantenimientos programados con listas de barrios afectados en el Valle. | [El País](https://www.elpais.com.co/valle/mantenimientos-de-celsia-del-18-al-22-de-junio-barrios-y-corregimientos-afectados-en-valle-del-cauca-1851.html) | No: datos que vencen en días |
| Jul-ago 2024 | La República | Reducción de la tarifa en el Tolima (11,1 % en julio de 2024, según el presidente de Celsia). | [La República](https://www.larepublica.co/empresas/presencia-de-celsia-en-el-tolima-3929914) | No: dato vencido; sí sirve la explicación de la tarifa del sitio |
| Sin fecha confirmada | Portafolio, El Tiempo, El Colombiano, Valora Analitik | Tarifas de energía en Valle y Tolima y acuerdos de reducción. | [Portafolio](https://www.portafolio.co/negocios/empresas/celsia-tambien-llego-a-acuerdos-para-disminuir-tarifas-de-energia-572280), [El Colombiano](https://www.elcolombiano.com/negocios/empresas/celsia-baja-tarifas-de-energia-en-valle-y-tolima-CP25081425) | No: vencido |

Índices por medio: [La República](https://www.larepublica.co/celsia), [El País](https://www.elpais.com.co/noticias/celsia/).
**Entrevistas:** no se encontró ninguna entrevista a directivos de Celsia sobre atención al cliente; las apariciones encontradas son noticias.

**Conclusión:** la prensa cubre hechos corporativos, regulatorios, financieros y de emergencia, y casi nada sobre trámites o atención de un cliente nuevo. Se usa como **contexto citado**, no como corpus (también por derechos de autor). Cuidado: algunos artículos con fecha 2026 narran hechos de 2022 o 2023.

## 5. Entidades y datos externos

- **Superservicios:** vigilancia y tarifas trimestrales.
- **SUI y Datos.gov.co:** datos estructurados, útiles para el enrutador de consultas SQL/CSV del Módulo 2.
- **Grupo Argos:** historia y reportes. Celsia fue Colinversiones y cambió de nombre en 2012.
