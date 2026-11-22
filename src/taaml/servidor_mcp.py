"""Servidor MCP propio: expone las dos herramientas de consulta del agente de Celsia a cualquier cliente MCP.

Solo lectura: busca en la información pública de Celsia y consulta tablas de datos. No escribe nada, no manda
mensajes y no toca la memoria ni los reclamos. Se enciende con `make mcp` (transporte stdio: el cliente lo lanza
como proceso hijo, así no queda ningún puerto abierto hacia internet).
"""

from mcp.server.mcpserver import MCPServer

from taaml.agente import buscar_en_base, consultar_datos

servidor = MCPServer("celsia")


@servidor.tool()
def buscar_informacion_celsia(pregunta: str, categoria: str = "", region: str = "") -> str:
    """Busca en la información oficial de Celsia los fragmentos que responden la pregunta. Categoría y región son opcionales."""
    datos = {"pregunta": pregunta}
    if categoria:
        datos["categoria"] = categoria
    if region:
        datos["region"] = region
    return str(buscar_en_base.invoke(datos))


@servidor.tool()
def consultar_datos_celsia(
    tabla: str, ciudad: str = "", departamento: str = "", tipo: str = "", tema: str = "", texto: str = ""
) -> str:
    """Datos exactos de Celsia: tabla «sedes», «contactos» o «catalogo». Cada respuesta termina con «Total: N»."""
    return str(
        consultar_datos.invoke(
            {
                "tabla": tabla,
                "ciudad": ciudad,
                "departamento": departamento,
                "tipo": tipo,
                "tema": tema,
                "texto": texto,
            }
        )
    )


if __name__ == "__main__":
    servidor.run(transport="stdio")
