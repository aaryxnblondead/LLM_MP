"""RAG engine for VidhaanAI using ChromaDB and LangChain."""

from __future__ import annotations

import os
from typing import Dict, List

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv


class RAGEngine:
    """Retrieval engine backed by ChromaDB collections."""

    def __init__(self, persist_directory: str = "./vector_store") -> None:
        """Initialize the ChromaDB stores and embeddings."""
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            os.environ.setdefault("GOOGLE_API_KEY", api_key)
        self.persist_directory = persist_directory
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
        self.ipc_store = Chroma(
            collection_name="ipc_corpus",
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
        )
        self.bns_store = Chroma(
            collection_name="bns_corpus",
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
        )

    def is_index_built(self) -> bool:
        """Check whether any documents exist in the vector store."""
        try:
            return self.ipc_store._collection.count() > 0 or self.bns_store._collection.count() > 0
        except Exception:
            return False

    def build_index(self, documents: List[Dict]) -> None:
        """Embed and store documents in the appropriate collections.

        Args:
            documents: List of dictionaries with keys content, metadata, law_type.
        """
        ipc_docs = [doc for doc in documents if doc.get("law_type") == "IPC"]
        bns_docs = [doc for doc in documents if doc.get("law_type") == "BNS"]

        try:
            if ipc_docs:
                self.ipc_store.add_texts(
                    texts=[doc["content"] for doc in ipc_docs],
                    metadatas=[doc["metadata"] for doc in ipc_docs],
                )
            if bns_docs:
                self.bns_store.add_texts(
                    texts=[doc["content"] for doc in bns_docs],
                    metadatas=[doc["metadata"] for doc in bns_docs],
                )

        except Exception as exc:
            raise RuntimeError(
                "Failed to build the vector index. Please check your API key and try again."
            ) from exc

    def query(self, query_text: str, law_type: str = "both", k: int = 5) -> List[Dict]:
        """Retrieve top-k relevant chunks.

        Args:
            query_text: Query string.
            law_type: "IPC", "BNS", or "both".
            k: Number of results per store.

        Returns:
            List of retrieved documents with metadata.
        """
        results: List[Dict] = []
        try:
            if law_type in ("IPC", "both"):
                ipc_hits = self.ipc_store.similarity_search(query_text, k=k)
                results.extend(
                    {"content": doc.page_content, "metadata": doc.metadata, "law_type": "IPC"}
                    for doc in ipc_hits
                )
            if law_type in ("BNS", "both"):
                bns_hits = self.bns_store.similarity_search(query_text, k=k)
                results.extend(
                    {"content": doc.page_content, "metadata": doc.metadata, "law_type": "BNS"}
                    for doc in bns_hits
                )
        except Exception:
            return []

        return results
