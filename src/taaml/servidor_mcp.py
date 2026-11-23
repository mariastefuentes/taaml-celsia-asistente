"""Servidor MCP propio: expone las herramientas de solo lectura del agente de Celsia a cualquier cliente MCP.

Son diez: la búsqueda en el texto oficial y las nueve consultas de datos y de información manual (sedes, contactos, catálogo,
puntos de pago, tiendas, canales, cobertura, trámites en línea y política de datos). No escribe nada, no manda mensajes y no
toca la memoria ni los reclamos. Se enciende con `make mcp` (transporte stdio: el cliente lo lanza como proceso hijo, así no
queda ningún puerto abierto hacia internet).
"""

from mcp.server.mcpserver import MCPServer

from taaml.agente import (
    buscar_en_base,
    consultar_canales_de_atencion,
    consultar_catalogo,
    consultar_contactos,
    consultar_cobertura,
    consultar_politica_de_datos,
    consultar_puntos_de_pago,
    consultar_sedes,
    consultar_tiendas,
    consultar_tramite_en_linea,
)

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
def consultar_sedes_celsia(ciudad: str = "", departamento: str = "", tipo: str = "") -> str:
    """Sedes, tiendas y puntos de atención de Celsia con dirección, teléfono y horario. Termina con «Total: N»."""
    return str(consultar_sedes.invoke({"ciudad": ciudad, "departamento": departamento, "tipo": tipo}))


@servidor.tool()
def consultar_contactos_celsia(tipo: str = "", tema: str = "") -> str:
    """Teléfonos, WhatsApp, correos y enlaces oficiales de atención, con para qué sirve cada uno. Termina con «Total: N»."""
    return str(consultar_contactos.invoke({"tipo": tipo, "tema": tema}))


@servidor.tool()
def consultar_catalogo_celsia(texto: str = "", seccion: str = "", categoria: str = "") -> str:
    """Páginas del sitio de Celsia por título, sección o categoría, con su enlace oficial."""
    return str(consultar_catalogo.invoke({"texto": texto, "seccion": seccion, "categoria": categoria}))


@servidor.tool()
def consultar_puntos_de_pago_celsia(ciudad: str = "") -> str:
    """Puntos de recaudo y pago de Celsia donde se paga la factura. Termina con «Total: N»."""
    return str(consultar_puntos_de_pago.invoke({"ciudad": ciudad}))


@servidor.tool()
def consultar_tiendas_celsia(ciudad: str = "") -> str:
    """Tiendas Celsia con dirección, teléfono y horario. Termina con «Total: N»."""
    return str(consultar_tiendas.invoke({"ciudad": ciudad}))


@servidor.tool()
def consultar_canales_de_atencion_celsia(necesidad: str = "", tipo: str = "") -> str:
    """Canal oficial (teléfono, WhatsApp, correo o enlace) que sirve para una necesidad del cliente."""
    return str(consultar_canales_de_atencion.invoke({"necesidad": necesidad, "tipo": tipo}))


@servidor.tool()
def consultar_cobertura_celsia(ciudad: str) -> str:
    """Dice si Celsia tiene atención presencial en una ciudad y cuántos puntos de cada tipo hay."""
    return str(consultar_cobertura.invoke({"ciudad": ciudad}))


@servidor.tool()
def consultar_tramite_en_linea_celsia(tramite: str = "", tipo: str = "") -> str:
    """Enlace oficial para pagar, reportar un daño, registrar la factura digital, presentar una PQR o entrar a la Zona Clientes."""
    return str(consultar_tramite_en_linea.invoke({"tramite": tramite, "tipo": tipo}))


@servidor.tool()
def consultar_politica_de_datos_celsia(tema: str = "") -> str:
    """Lo que dice la política de privacidad del asistente sobre el tratamiento de los datos del cliente."""
    return str(consultar_politica_de_datos.invoke({"tema": tema}))


if __name__ == "__main__":
    servidor.run(transport="stdio")
