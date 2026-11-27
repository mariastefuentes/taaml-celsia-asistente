# Revisión de calidad con Playwright (anuncio 008)

Fecha: 27/11/2026. En un computador del equipo (Windows 11), no en el del bot. Navegador: Microsoft Edge manejado con Playwright
1.65.2. Pruebas: [`tests/e2e/test_qa_navegador.py`](../tests/e2e/test_qa_navegador.py).

## Cómo se corre

```bash
make chat-web    # compila la página
make qa          # servidor propio con agente simulado: gratis, para antes de cada push
```

Contra la aplicación ya encendida (PowerShell). `QA_MODELO_REAL` hace **una** pregunta al modelo, que cuesta centavos:

```powershell
$env:QA_URL="http://127.0.0.1:8000"; $env:QA_MODELO_REAL="1"; make qa
```

`make test` y la revisión de GitHub no incluyen estas pruebas, porque necesitan un navegador instalado.

## Qué se revisa

| Punto del anuncio | Qué se comprueba |
|---|---|
| Flujo del pitch | Preguntar «¿Qué es una granja solar?» y ver la respuesta, la herramienta usada y las fuentes con documento y fragmento |
| Consola y red | Ningún error ni aviso en la consola, ninguna respuesta 400 o mayor y ninguna petición fallida |
| Tamaños | Celular (390 × 844) y escritorio (1366 × 768), sin desplazamiento horizontal en el chat |
| Webhook de WhatsApp | Verificación; un aviso firmado simulado responde 200 y llega a quien lo atiende; sin firma responde 401 |
| Otras pantallas | Portada con su QR, botones de la cabecera, una dirección dañada, el panel y `/api/salud` |

## Errores encontrados y corregidos

| Qué pasaba | Dónde se veía | Arreglo |
|---|---|---|
| Aviso del enrutador en la consola en todas las direcciones del chat | Consola | `frontend/src/main.jsx`: las direcciones hijas declaran `element={null}` |
| Al abrir una dirección dañada (`/c/lo-que-sea`), tres respuestas 422 y **la primera pregunta fallaba** con «No hay conexión» | Red y pantalla | `frontend/src/App.jsx`: un identificador inválido no se guarda como conversación |

Antes de los arreglos: 14 pruebas pasaban su comprobación principal y 8 dejaban errores de consola o de red.

## Resultados después de los arreglos

Servidor propio, agente simulado:

```text
14 passed in 19.92s
```

Aplicación con el índice y el modelo reales (copia corregida, puerto 8010, memoria temporal):

```text
SKIPPED [1] en la app encendida solo se pregunta al modelo real una vez
SKIPPED [3] el webhook se prueba en el servidor propio
10 passed, 4 skipped in 29.68s
```

La pregunta real usó `buscar_en_base` con `deepseek-flash`, mostró 4 fuentes y costó 0,0031 USD.

## Lo que esta revisión no cubre

- Playwright no entra a WhatsApp: la conversación real se prueba desde un teléfono.
- El webhook de Meta no se usa en la demostración (D56); se probó con avisos simulados.
- La pregunta con el modelo real se hizo solo en tamaño escritorio.
- No se revisó la aplicación en el computador del bot.
- En el panel no se escribió la clave: solo se comprobó que la página abre sin errores.
