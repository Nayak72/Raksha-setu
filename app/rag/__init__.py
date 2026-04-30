"""
RakshaSetu — RAG Memory System
Centralized Retrieval-Augmented Generation using ChromaDB + sentence-transformers.

Public API:
    get_embedding_pipeline()  → EmbeddingPipeline singleton
    get_memory_store()        → RAGMemoryStore singleton
    get_retriever()           → RAGRetriever singleton

Collections managed:
    - weather_history:   Past weather events per zone
    - detection_history: Past YOLO detection events per zone
    - zone_events:       High-level zone analysis decisions
"""

from app.rag.embeddings import EmbeddingPipeline, get_embedding_pipeline
from app.rag.memory import RAGMemoryStore, get_memory_store
from app.rag.retriever import RAGRetriever, get_retriever

__all__ = [
    "EmbeddingPipeline",
    "get_embedding_pipeline",
    "RAGMemoryStore",
    "get_memory_store",
    "RAGRetriever",
    "get_retriever",
]
