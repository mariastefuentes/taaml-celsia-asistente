# Vacíos de la base: texto listo, NO aplicado

La base no responde con cifras tres preguntas frecuentes: precio del cargador de carro eléctrico, fecha límite de pago y facturación por estimación. El agente dice «No tengo esa información» y da la línea 01 8000 112 115, que es lo correcto mientras el dato no esté.
Abajo hay un documento manual con solo lo verificable (regla general de la Superservicios y la Ley 142; **no hay precio ni plazo oficial de Celsia**: se buscó y no está publicado). Se probó: agregarlo cambia el corpus a 394 documentos y 1.692 fragmentos, y entonces hay que rehacer el índice de Qdrant y repetir las mediciones del informe (recuperación, t-SNE, HNSW), todas hechas sobre 1.690. Con la sustentación el sábado se decidió no tocar la base (ver D19 en `decisiones.md`). Para aplicarlo: copiar el bloque de abajo a `data/0_manual/facturacion_marco_general.md`, correr `make datos`, `make indice` y repetir las mediciones.

---

---
title: Facturación de energía en Colombia: fecha límite de pago, suspensión y consumo estimado (marco general)
fuente: normas y conceptos de la Superintendencia de Servicios Públicos Domiciliarios (Superservicios) y la Ley 142 de 1994; revisados el 19/11/2026
nota: Documento escrito a mano para cubrir tres preguntas frecuentes que el sitio de Celsia no responde con cifras. Es la regla general del país, NO una política propia de Celsia: las fechas y valores exactos de cada cliente están en su factura.
---

Fecha límite de pago y suspensión
- Cada factura trae su fecha de expedición y su fecha límite de pago; esas fechas exactas son las que valen para el cliente y están impresas en su factura.
- Si no se paga a tiempo, la empresa puede cobrar intereses de mora. El servicio no se suspende de inmediato: la Ley 142 de 1994 dice que el prestador no puede suspender por mora antes de que se acumulen dos períodos de facturación vencidos (cuando la facturación es bimestral) o tres (cuando es mensual), y debe dar aviso previo.
- Para evitar la suspensión o pedir la reconexión, el cliente debe comunicarse con Celsia por la línea 01 8000 112 115.

Facturación por consumo estimado (promedio)
- La regla general es facturar la diferencia entre dos lecturas del medidor.
- Solo de forma excepcional el prestador puede cobrar un promedio del consumo de períodos anteriores del mismo usuario, o de usuarios en condiciones similares. La Superservicios advierte que no debe ser una práctica habitual.
- Si la factura llegó por promedio o el cliente cree que la lectura es errada, puede presentar una petición, queja o reclamo (PQR) a Celsia y pedir que se verifique la lectura; cuando llegue la lectura real, la diferencia debe corregirse. Si la respuesta no lo satisface, puede acudir a la Superservicios.

Cargador de carro eléctrico
- Celsia ofrece cargadores residenciales para vehículos eléctricos, pero no publica su precio en el sitio; la instalación depende de cada vivienda. Para una cotización hay que contactar a Celsia (línea 01 8000 112 115).
