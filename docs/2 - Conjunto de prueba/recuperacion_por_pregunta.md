# Recuperación por pregunta

En qué posición de los 12 fragmentos recuperados aparece la respuesta (1 = primer fragmento; «–» = no aparece). Se genera con `scripts/10_evaluar_recuperacion.py --solo-tabla` desde `resultados/recuperacion_k12.csv`.

| Id | Pregunta | palabras | embeddings | hibrido |
|---|---|---|---|---|
| P01 | ¿Cuál es el teléfono y el WhatsApp de atención al cliente de Celsia? | 2 | 1 | 2 |
| P02 | ¿Hasta qué hora puedo llamar? ¿Atienden los domingos? | – | 1 | 1 |
| P03 | oficina en Palmira | – | 1 | 3 |
| P04 | ¿Atienden los sábados en Planadas? | 7 | 1 | 1 |
| P05 | Vivo en Cali, ¿tienen alguna oficina cerca? | – | – | – |
| P06 | ¿Cuál es el Instagram oficial de Celsia? | 3 | 1 | 1 |
| P07 | ¿Qué es Celsia y a qué se dedica? | – | 12 | – |
| P08 | ¿Desde cuándo existe Celsia? ¿Antes se llamaba distinto? | 1 | 1 | 1 |
| P09 | ¿Es lo mismo EPSA que Celsia? | – | 1 | – |
| P10 | ¿Celsia puede cobrar lo que quiera por la luz? | 10 | 11 | 3 |
| P11 | ¿Cuánto cuesta el internet de Celsia y qué velocidades tiene? | – | 1 | 7 |
| P12 | ¿Qué ofrece Celsia en internet para la casa? | – | – | – |
| P13 | tengo un negocio chiquito, ¿qué me ofrecen para ahorrar energía? | – | 2 | 9 |
| P14 | Tengo una fábrica y quiero que Celsia me venda la energía, ¿se puede? | – | – | 6 |
| P15 | ¿Qué papeles necesito para pedir el servicio de energía en mi casa nueva? | – | 5 | – |
| P16 | Quiero cancelar mi servicio de energía en Ibagué, ¿cómo hago? | – | 1 | – |
| P17 | ¿Ustedes instalan cargadores para carro eléctrico en la casa? | 1 | 1 | 1 |
| P18 | Tengo una finca sin red eléctrica, ¿puedo usar paneles solares? | – | 1 | 9 |
| P19 | Se me quemó la nevera por un bajón de luz, ¿Celsia responde? | 1 | 1 | 1 |
| P20 | Vivo en arriendo en Ibagué, ¿puedo recibir la factura digital? | 1 | 1 | 1 |
| P21 | ¿Por qué ahora me piden registrarme en la Zona Clientes? | 7 | 1 | 1 |
| P22 | ¿Qué pasa si me atraso con el pago de la factura? | 1 | 9 | 4 |
| P23 | ¿Qué es la represa de Salvajina y qué capacidad tiene? | 1 | 1 | 1 |
| P24 | ¿Cuánto descuento me da el subsidio de energía si soy estrato 1, 2 o 3? | 2 | 1 | 1 |
| P25 | ¿Cómo compro acciones de Celsia? | 2 | 1 | 1 |
| P26 | ¿Cuántos árboles ha sembrado Celsia? | 3 | 4 | 1 |
| P27 | ¿Quiénes están en la junta directiva de Celsia? | 1 | 1 | 1 |
| P28 | ¿Qué es el distrito térmico de Serena del Mar? | 1 | 1 | 1 |
| P29 | ¿Quién presenta el pódcast de Celsia? | 1 | 1 | 1 |
| P30 | Si pongo paneles solares en mi casa, ¿puedo vender la energía que me sobra? | 2 | – | – |
| P31 | Puse una queja, ¿en cuánto tiempo me tienen que responder? | – | 7 | 12 |
| P32 | ¿Quién es el dueño de Celsia? | – | 5 | – |
| P33 | ¿Cuántas personas trabajan en Celsia? | – | 2 | – |
| P34 | ¿Qué es Luz I.A.? | – | 1 | 2 |
| P35 | ¿Cuáles son los valores de Celsia? | 1 | 3 | 1 |

| Total | hit@1 | hit@3 | hit@12 |
|---|---|---|---|
| palabras | 10 de 35 | 16 de 35 | 19 de 35 (54%) |
| embeddings | 21 de 35 | 24 de 35 | 31 de 35 (89%) |
| hibrido | 16 de 35 | 20 de 35 | 26 de 35 (74%) |
