"""Piezas nativas de LangChain para buscar por significado: los embeddings (Ollama) y el vectorstore (Qdrant).

`EmbeddingsCelsia` es un `OllamaEmbeddings` que además agrega el prefijo que pide nomic-embed-text-v2-moe («search_document: » o
«search_query: ») y normaliza los vectores. `almacen_langchain` envuelve una colección de Qdrant en un `QdrantVectorStore`, la clase
estándar de LangChain para guardar y consultar vectores con filtros. Este módulo no conoce el corpus: lo usa `recuperacion.py`.
"""

from typing import Any

import numpy as np
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

PREFIJO_DOCUMENTO = "search_document: "
PREFIJO_CONSULTA = "search_query: "
CAMPO_TEXTO = "page_content"  # dónde guarda LangChain el texto en el payload de Qdrant
CAMPO_METADATOS = "metadata"  # y dónde sus metadatos


class EmbeddingsCelsia(OllamaEmbeddings):
    """Embeddings de Ollama con el prefijo de tarea del modelo y vectores normalizados (norma 1, para que el producto punto sea el coseno)."""

    def incrustar(self, textos: list[str], tipo: str) -> list[list[float]]:
        """Embeddings de `textos`; `tipo` es «document» o «query»."""
        prefijo = PREFIJO_DOCUMENTO if tipo == "document" else PREFIJO_CONSULTA
        vectores = np.array(super().embed_documents([prefijo + t for t in textos]), dtype=np.float32)
        return (vectores / np.linalg.norm(vectores, axis=1, keepdims=True)).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.incrustar(texts, "document")

    def embed_query(self, text: str) -> list[float]:
        return self.incrustar([text], "query")[0]


def embeddings_celsia(modelo: str, timeout: int = 300) -> EmbeddingsCelsia:
    # keep_alive: Ollama descarga el modelo tras 5 minutos sin uso y la siguiente búsqueda tarda ~7 s en cargarlo; 1800 s = 30 minutos en memoria
    return EmbeddingsCelsia(model=modelo, keep_alive=1800, client_kwargs={"timeout": timeout})


def almacen_langchain(cliente: QdrantClient, coleccion: str, embedding: Any = None) -> QdrantVectorStore:
    """El vectorstore de LangChain sobre una colección de Qdrant (o su alias).

    No valida la colección al crearlo (`validate_*=False`): esa validación llamaría a Ollama para medir los vectores y aquí solo
    se consulta por vector ya calculado (`similarity_search_with_score_by_vector`).
    """
    return QdrantVectorStore(
        client=cliente,
        collection_name=coleccion,
        embedding=embedding,
        content_payload_key=CAMPO_TEXTO,
        metadata_payload_key=CAMPO_METADATOS,
        validate_embeddings=False,
        validate_collection_config=False,
    )
