"""Piezas nativas de LangChain para buscar por significado: los embeddings (Gemini, en la nube) y el vectorstore (Qdrant).

`EmbeddingsCelsia` es un `GoogleGenerativeAIEmbeddings` que además indica el tipo de tarea (documento o consulta) y normaliza los vectores. `almacen_langchain` envuelve una colección de Qdrant en un `QdrantVectorStore`, la clase
estándar de LangChain para guardar y consultar vectores con filtros. Este módulo no conoce el corpus: lo usa `recuperacion.py`.
"""

import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

load_dotenv(Path(__file__).resolve().parents[2] / ".env")  # la clave de Google puede no estar cargada si solo se importa este módulo

# Contrato con LangChain: nuestro almacén es un `VectorStore` estándar (langchain_core.vectorstores) y nuestros embeddings, un `Embeddings`.
# Si una versión futura de las librerías rompiera esto, el módulo falla al importarse y no en medio de una demostración.
assert issubclass(QdrantVectorStore, VectorStore) and issubclass(GoogleGenerativeAIEmbeddings, Embeddings)

DIMENSIONES = 768  # gemini-embedding-001 admite recortar el vector; 768 pesa cuatro veces menos que los 3.072 originales y mide igual de bien
TAREA = {"document": "RETRIEVAL_DOCUMENT", "query": "RETRIEVAL_QUERY"}  # el modelo distingue el texto que se guarda del que se pregunta
CAMPO_TEXTO = "page_content"  # dónde guarda LangChain el texto en el payload de Qdrant
CAMPO_METADATOS = "metadata"  # y dónde sus metadatos


class EmbeddingsCelsia(GoogleGenerativeAIEmbeddings):
    """Embeddings de Gemini (API en la nube, sin modelos locales) con el tipo de tarea y vectores normalizados (norma 1, para que el producto punto sea el coseno)."""

    def incrustar(self, textos: list[str], tipo: str, reintentos: int = 4) -> list[list[float]]:
        """Embeddings de `textos`; `tipo` es «document» o «query». Reintenta con espera si la API limita el ritmo."""
        for intento in range(reintentos):
            try:
                crudo = super().embed_documents(textos, task_type=TAREA[tipo], output_dimensionality=DIMENSIONES)
                break
            except Exception:  # noqa: BLE001  límite de cuota o corte de red: se espera y se reintenta
                if intento == reintentos - 1:
                    raise
                time.sleep(2**intento)
        vectores = np.array(crudo, dtype=np.float32)
        return (vectores / np.linalg.norm(vectores, axis=1, keepdims=True)).tolist()

    def embed_documents(self, texts: list[str], **kwargs) -> list[list[float]]:
        return self.incrustar(texts, "document")

    def embed_query(self, text: str, **kwargs) -> list[float]:
        return self.incrustar([text], "query")[0]


def embeddings_celsia(modelo: str, timeout: int = 300) -> EmbeddingsCelsia:
    return EmbeddingsCelsia(model=modelo, request_options={"timeout": timeout})


def almacen_langchain(cliente: QdrantClient, coleccion: str, embedding: Embeddings | None = None) -> QdrantVectorStore:
    """El vectorstore de LangChain sobre una colección de Qdrant (o su alias).

    No valida la colección al crearlo (`validate_*=False`): esa validación llamaría a la API para medir los vectores y aquí solo
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
