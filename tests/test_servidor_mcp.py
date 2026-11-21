"""El servidor MCP propio, probado con un cliente MCP real por stdio (como lo usaría OpenClaw)."""

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def _sesion(accion):
    parametros = StdioServerParameters(command=sys.executable, args=["-m", "taaml.servidor_mcp"])
    async with stdio_client(parametros) as (leer, escribir):
        async with ClientSession(leer, escribir) as sesion:
            await sesion.initialize()
            return await accion(sesion)


def test_expone_solo_las_dos_herramientas_de_lectura():
    async def accion(sesion):
        return {t.name for t in (await sesion.list_tools()).tools}

    assert asyncio.run(_sesion(accion)) == {"buscar_informacion_celsia", "consultar_datos_celsia"}


def test_consultar_datos_devuelve_contactos_con_total():
    async def accion(sesion):
        return await sesion.call_tool("consultar_datos_celsia", {"tabla": "contactos", "tipo": "teléfono"})

    texto = asyncio.run(_sesion(accion)).content[0].text
    assert "Total:" in texto and "01 8000 112 115" in texto
