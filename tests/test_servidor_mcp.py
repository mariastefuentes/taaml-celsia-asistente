"""El servidor MCP propio, probado con un cliente MCP real por stdio (como lo usaría OpenClaw)."""

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ESPERADAS = {
    "buscar_informacion_celsia",
    "consultar_sedes_celsia",
    "consultar_contactos_celsia",
    "consultar_catalogo_celsia",
    "consultar_canales_de_atencion_celsia",
    "consultar_cobertura_celsia",
    "consultar_tramite_en_linea_celsia",
    "consultar_politica_de_datos_celsia",
    "verificar_canal_oficial_celsia",
    "calcular_factura_estimada_celsia",
}


async def _sesion(accion):
    parametros = StdioServerParameters(command=sys.executable, args=["-m", "taaml.servidor_mcp"])
    async with stdio_client(parametros) as (leer, escribir):
        async with ClientSession(leer, escribir) as sesion:
            await sesion.initialize()
            return await accion(sesion)


def test_expone_solo_las_herramientas_de_lectura():
    async def accion(sesion):
        return {t.name for t in (await sesion.list_tools()).tools}

    assert asyncio.run(_sesion(accion)) == ESPERADAS


def test_consultar_contactos_devuelve_total():
    async def accion(sesion):
        return await sesion.call_tool("consultar_contactos_celsia", {"tipo": "teléfono"})

    texto = asyncio.run(_sesion(accion)).content[0].text
    assert "Total:" in texto and "01 8000 112 115" in texto


def test_consultar_sedes_devuelve_direcciones():
    async def accion(sesion):
        return await sesion.call_tool("consultar_sedes_celsia", {"ciudad": "Ibagué"})

    texto = asyncio.run(_sesion(accion)).content[0].text
    assert "Dirección" in texto and "Total:" in texto


def test_la_lista_permitida_de_openclaw_coincide_con_las_herramientas_del_servidor():
    """Si el servidor cambia una herramienta y la configuración de OpenClaw no, el gateway la bloquea (o apunta a una que ya no existe)."""
    from taaml.openclaw import configuracion

    entorno = {"OPENCLAW_GATEWAY_TOKEN": "t", "WHATSAPP_ALLOWLIST": "+573001112233", "REPO_CELSIA": "C:/ruta/al/repo"}
    config = configuracion(entorno)
    assert set(config["mcp"]["servers"]["celsia"]["toolFilter"]["include"]) == ESPERADAS
