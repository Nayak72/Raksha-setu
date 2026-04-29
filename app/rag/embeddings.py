"""
RakshaSetu — Embedding Pipeline
Sentence-transformers based embedding engine for the RAG memory system.

Uses a thread-safe singleton to avoid loading the model multiple times.
The embedding model is configured via the EMBEDDING_MODEL env variable
(default: all-MiniLM-L6-v2, 384 dimensions).
"""

import logging
import threading
from typing import Union

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger("raksha.rag.embeddings")

# ── Thread-safe Singleton ─────────────────────────────────────

_lock = threading.Lock()
_model_instance: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Lazy-load and cache the embedding model (thread-safe)."""
    global _model_instance
    if _model_instance is None:
        with _lock:
            if _model_instance is None:
                model_name = settings.rag.embedding_model or "all-MiniLM-L6-v2"
                logger.info(f"Loading sentence-transformer model: {model_name}")
                _model_instance = SentenceTransformer(model_name)
                logger.info(
                    f"Model loaded: dim={_model_instance.get_embedding_dimension()}"
                )
    return _model_instance


# ── Public API ────────────────────────────────────────────────


class EmbeddingPipeline:
    """
    High-level embedding interface for the RAG memory system.

    Wraps sentence-transformers with:
      - Singleton model management
      - Batch encoding support
      - Numpy array output (compatible with ChromaDB and pgvector)
      - Dimension validation
    """

    def __init__(self):
        self._model = _get_model()
        self._dimension = self._model.get_embedding_dimension()
        logger.info(f"EmbeddingPipeline ready: dim={self._dimension}")

    @property
    def dimension(self) -> int:
        """Return the embedding dimensionality (e.g. 384 for MiniLM)."""
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        """
        Embed a single text string.

        Args:
            text: Input text to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        if not text or not text.strip():
            logger.warning("Empty text passed to embed_text, returning zero vector.")
            return [0.0] * self._dimension

        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """
        Embed a batch of texts efficiently.

        Args:
            texts: List of input texts.
            batch_size: Number of texts to encode per batch.

        Returns:
            List of embedding vectors (each a list of floats).
        """
        if not texts:
            return []

        # Flatten nested lists (ChromaDB sometimes passes [["text"]])
        flat_texts = []
        for t in texts:
            if isinstance(t, list):
                flat_texts.extend(t)
            else:
                flat_texts.append(t)
        texts = flat_texts

        # Filter empty strings but track positions
        valid_indices = []
        valid_texts = []
        for i, t in enumerate(texts):
            if t and isinstance(t, str) and t.strip():
                valid_indices.append(i)
                valid_texts.append(t)

        if not valid_texts:
            return [[0.0] * self._dimension for _ in texts]

        embeddings = self._model.encode(
            valid_texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True
        )

        # Ensure embeddings is 2D even if only one text was encoded
        if len(valid_texts) == 1 and len(embeddings.shape) == 1:
            embeddings = embeddings[np.newaxis, :]

        # Reconstruct full results with zero vectors for empty inputs
        results = [[0.0] * self._dimension for _ in texts]
        for idx, emb in zip(valid_indices, embeddings):
            results[idx] = emb.tolist()

        return results

    def similarity(self, text_a: str, text_b: str) -> float:
        """
        Compute cosine similarity between two texts.

        Returns:
            Float between -1.0 and 1.0 (1.0 = identical meaning).
        """
        emb_a = np.array(self.embed_text(text_a))
        emb_b = np.array(self.embed_text(text_b))

        dot = np.dot(emb_a, emb_b)
        norm_a = np.linalg.norm(emb_a)
        norm_b = np.linalg.norm(emb_b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot / (norm_a * norm_b))


# ── Module-level singleton ────────────────────────────────────

_pipeline_instance: EmbeddingPipeline | None = None
_pipeline_lock = threading.Lock()


def get_embedding_pipeline() -> EmbeddingPipeline:
    """Get or create the global EmbeddingPipeline singleton."""
    global _pipeline_instance
    if _pipeline_instance is None:
        with _pipeline_lock:
            if _pipeline_instance is None:
                _pipeline_instance = EmbeddingPipeline()
    return _pipeline_instance
