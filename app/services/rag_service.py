"""
RAG Service – Retrieval-Augmented Generation using pgvector.

Provides:
  • Vector embedding generation (sentence-transformers)
  • Similarity search against a `documents` table with pgvector
  • Context retrieval for agent decision-making

NOTE: The `documents` table and pgvector extension must be set up
      via the SQL migration (see migrations/001_initial.sql).
"""

from __future__ import annotations

import asyncio
from functools import partial
from typing import Any, Optional


import structlog

from app.config import get_settings
from app.db.supabase_client import get_pg_pool

logger = structlog.get_logger(__name__)
settings = get_settings()

# ── Lazy-loaded embedding model ─────────────
_model = None


def _get_model():
    """Lazy-load the sentence transformer model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.rag.embedding_model)
        logger.info("rag.model_loaded", model=settings.rag.embedding_model)
    return _model


async def generate_embedding(text: str) -> list[float]:
    """
    Generate a vector embedding for the given text.
    Runs the model inference in a thread to avoid blocking the event loop.
    """
    loop = asyncio.get_running_loop()
    model = await loop.run_in_executor(None, _get_model)
    embedding = await loop.run_in_executor(
        None, partial(model.encode, text, normalize_embeddings=True)
    )
    return embedding.tolist()


async def store_document(
    content: str,
    metadata: Optional[dict[str, Any]] = None,
    doc_type: str = "general",
) -> str:
    """
    Embed and store a document in the pgvector-backed `documents` table.
    
    Returns the document ID.
    """
    import json as _json

    embedding = await generate_embedding(content)
    pool = await get_pg_pool()

    query = """
        INSERT INTO documents (content, embedding, metadata, doc_type)
        VALUES ($1, $2::vector, $3::jsonb, $4)
        RETURNING id;
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            query,
            content,
            str(embedding),
            _json.dumps(metadata or {}),
            doc_type,
        )
        doc_id = str(row["id"])
        logger.info("rag.document_stored", doc_id=doc_id, doc_type=doc_type)
        return doc_id


async def search_similar(
    query_text: str,
    top_k: int = 5,
    doc_type: Optional[str] = None,
    similarity_threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """
    Perform a cosine similarity search against stored documents.
    
    Args:
        query_text:            Text to search for
        top_k:                 Number of results to return
        doc_type:              Optional filter by document type
        similarity_threshold:  Minimum similarity score (0-1)
    
    Returns:
        List of matching documents with similarity scores.
    """
    embedding = await generate_embedding(query_text)
    pool = await get_pg_pool()

    # pgvector cosine distance: <=> operator
    # 1 - distance = similarity
    if doc_type:
        query = """
            SELECT id, content, metadata, doc_type,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM documents
            WHERE doc_type = $3
              AND 1 - (embedding <=> $1::vector) >= $4
            ORDER BY embedding <=> $1::vector
            LIMIT $2;
        """
        params = (str(embedding), top_k, doc_type, similarity_threshold)
    else:
        query = """
            SELECT id, content, metadata, doc_type,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM documents
            WHERE 1 - (embedding <=> $1::vector) >= $3
            ORDER BY embedding <=> $1::vector
            LIMIT $2;
        """
        params = (str(embedding), top_k, similarity_threshold)

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            results = [dict(row) for row in rows]
            logger.info("rag.search_completed", query=query_text[:50], results=len(results))
            return results
    except Exception as exc:
        logger.error("rag.search_failed", error=str(exc))
        return []


async def get_context_for_zone(zone_id: str, query: str = "") -> str:
    """
    Retrieve relevant context about a zone for agent decision-making.
    
    Combines the query with zone-specific document search.
    """
    search_query = f"zone {zone_id} {query}".strip()
    docs = await search_similar(search_query, top_k=3)

    if not docs:
        return f"No additional context found for zone {zone_id}."

    context_parts = []
    for doc in docs:
        sim = doc.get("similarity", 0)
        content = doc.get("content", "")
        context_parts.append(f"[relevance: {sim:.2f}] {content}")

    return "\n---\n".join(context_parts)
