"""
RakshaSetu — RAG Memory Store
Central ChromaDB-based memory system with dedicated collections for
weather history and detection history.

Uses the custom sentence-transformers EmbeddingPipeline instead of
ChromaDB's default embeddings for consistent vector representations.

Collections:
  - weather_history:   Past weather events per zone (severity, rainfall, etc.)
  - detection_history: Past YOLO detection events per zone (crowd, flood, fire, etc.)
  - zone_events:       High-level zone analysis decisions (kept for backward compat)
"""

import logging
import threading
from datetime import datetime
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.rag.embeddings import get_embedding_pipeline

logger = logging.getLogger("raksha.rag.memory")


class RAGMemoryStore:
    """
    Centralized RAG memory backed by ChromaDB with sentence-transformers.

    Provides separate collections for weather and detection events,
    each with custom embedding functions for semantic similarity search.
    """

    def __init__(self):
        self._pipeline = get_embedding_pipeline()
        self._persist_dir = settings.chroma.persist_dir

        # Initialize ChromaDB with persistent storage
        self._client = chromadb.PersistentClient(
            path=self._persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # Create embedding function adapter for ChromaDB
        self._embed_fn = SentenceTransformerEmbeddingFunction(self._pipeline)

        # Initialize collections
        self._weather_collection = self._client.get_or_create_collection(
            name="weather_history",
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine", "description": "Historical weather events per zone"},
        )

        self._detection_collection = self._client.get_or_create_collection(
            name="detection_history",
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine", "description": "Historical YOLO detection events"},
        )

        self._zone_events_collection = self._client.get_or_create_collection(
            name="zone_events",
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine", "description": "Zone analysis decisions"},
        )

        logger.info(
            f"RAGMemoryStore initialized: persist_dir='{self._persist_dir}', "
            f"weather_docs={self._weather_collection.count()}, "
            f"detection_docs={self._detection_collection.count()}, "
            f"zone_event_docs={self._zone_events_collection.count()}"
        )

    # ── Weather History ──────────────────────────────────────

    def ingest_weather_event(self, event: dict) -> str:
        """
        Store a weather event in the weather_history collection.

        Args:
            event: Dict with zone_id, severity, rainfall, wind_speed, humidity,
                   temperature, reasoning_steps, confidence, etc.

        Returns:
            The document ID assigned to this event.
        """
        zone_id = event.get("zone", event.get("zone_id", "unknown"))
        doc_id = f"weather_{zone_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"

        document = self._weather_to_document(event)
        metadata = {
            "zone_id": str(zone_id),
            "severity": event.get("severity", "UNKNOWN"),
            "rainfall": float(event.get("rainfall", 0)),
            "wind_speed": float(event.get("wind_speed", 0)),
            "humidity": float(event.get("humidity", 0)),
            "temperature": float(event.get("temperature", 0)),
            "confidence": float(event.get("confidence", 0)),
            "timestamp": datetime.utcnow().isoformat(),
            "source": "weather_agent",
        }

        self._weather_collection.add(
            documents=[document],
            ids=[doc_id],
            metadatas=[metadata],
        )

        logger.info(f"RAG ingested weather event: {doc_id} (severity={metadata['severity']})")
        return doc_id

    def retrieve_weather_history(
        self,
        query: str,
        n_results: int = 5,
        zone_filter: Optional[str] = None,
        severity_filter: Optional[str] = None,
    ) -> dict:
        """
        Retrieve similar past weather events via semantic search.

        Args:
            query: Natural language description of the weather situation.
            n_results: Max number of results.
            zone_filter: Optional zone_id to scope results.
            severity_filter: Optional severity level to filter by.

        Returns:
            ChromaDB query results with documents, distances, metadatas.
        """
        if self._weather_collection.count() == 0:
            return {"documents": [[]], "distances": [[]], "metadatas": [[]]}

        query_params = {
            "query_texts": [query],
            "n_results": min(n_results, self._weather_collection.count()),
        }

        # Build where filter
        where_clauses = {}
        if zone_filter:
            where_clauses["zone_id"] = zone_filter
        if severity_filter:
            where_clauses["severity"] = severity_filter

        if where_clauses:
            query_params["where"] = where_clauses

        results = self._weather_collection.query(**query_params)
        logger.info(
            f"RAG weather retrieval: {len(results.get('documents', [[]])[0])} results"
        )
        return results

    # ── Detection History ────────────────────────────────────

    def ingest_detection_event(self, event: dict) -> str:
        """
        Store a YOLO detection event in the detection_history collection.

        Args:
            event: Dict with zone_id, crowd_density, flood_level, structural_damage,
                   fire_detected, vehicle_count, confidence, etc.

        Returns:
            The document ID assigned to this event.
        """
        zone_id = event.get("zone_id", "unknown")
        doc_id = f"detection_{zone_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"

        document = self._detection_to_document(event)
        metadata = {
            "zone_id": str(zone_id),
            "crowd_density": float(event.get("crowd_density", 0)),
            "flood_level": float(event.get("flood_level", 0)),
            "structural_damage": float(event.get("structural_damage", 0)),
            "fire_detected": bool(event.get("fire_detected", False)),
            "vehicle_count": int(event.get("vehicle_count", 0)),
            "confidence": float(event.get("confidence", 0)),
            "timestamp": datetime.utcnow().isoformat(),
            "source": "yolo_detection",
        }

        self._detection_collection.add(
            documents=[document],
            ids=[doc_id],
            metadatas=[metadata],
        )

        logger.info(f"RAG ingested detection event: {doc_id}")
        return doc_id

    def retrieve_detection_history(
        self,
        query: str,
        n_results: int = 5,
        zone_filter: Optional[str] = None,
    ) -> dict:
        """
        Retrieve similar past detection events via semantic search.

        Args:
            query: Natural language description of the detection situation.
            n_results: Max number of results.
            zone_filter: Optional zone_id to scope results.

        Returns:
            ChromaDB query results with documents, distances, metadatas.
        """
        if self._detection_collection.count() == 0:
            return {"documents": [[]], "distances": [[]], "metadatas": [[]]}

        query_params = {
            "query_texts": [query],
            "n_results": min(n_results, self._detection_collection.count()),
        }

        if zone_filter:
            query_params["where"] = {"zone_id": zone_filter}

        results = self._detection_collection.query(**query_params)
        logger.info(
            f"RAG detection retrieval: {len(results.get('documents', [[]])[0])} results"
        )
        return results

    # ── Zone Events (backward-compatible) ────────────────────

    def ingest_zone_event(self, event_data: dict) -> str:
        """
        Ingest a zone-level analysis event (decision + context).
        Backward compatible with the existing ZoneRAG.ingest_event().
        """
        zone_id = event_data.get("zone_id", "unknown")
        doc_id = f"event_{zone_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"

        document = self._zone_event_to_document(event_data)
        metadata = {
            "zone_id": str(zone_id),
            "decision": event_data.get("decision", "unknown"),
            "weather_severity": str(event_data.get("weather_severity", "unknown")),
            "priority": float(event_data.get("priority", 0.0)),
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._zone_events_collection.add(
            documents=[document],
            ids=[doc_id],
            metadatas=[metadata],
        )

        logger.info(f"RAG ingested zone event: {doc_id}")
        return doc_id

    def retrieve_zone_events(
        self,
        query: str,
        n_results: int = 5,
        zone_filter: Optional[str] = None,
    ) -> dict:
        """Retrieve similar past zone analysis events."""
        if self._zone_events_collection.count() == 0:
            return {"documents": [[]], "distances": [[]], "metadatas": [[]]}

        query_params = {
            "query_texts": [query],
            "n_results": min(n_results, self._zone_events_collection.count()),
        }

        if zone_filter:
            query_params["where"] = {"zone_id": zone_filter}

        results = self._zone_events_collection.query(**query_params)
        logger.info(
            f"RAG zone event retrieval: {len(results.get('documents', [[]])[0])} results"
        )
        return results

    # ── Statistics ────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Return collection statistics for monitoring."""
        return {
            "persist_dir": self._persist_dir,
            "embedding_dimension": self._pipeline.dimension,
            "collections": {
                "weather_history": self._weather_collection.count(),
                "detection_history": self._detection_collection.count(),
                "zone_events": self._zone_events_collection.count(),
            },
            "total_documents": (
                self._weather_collection.count()
                + self._detection_collection.count()
                + self._zone_events_collection.count()
            ),
        }

    # ── Document Formatters ──────────────────────────────────

    @staticmethod
    def _weather_to_document(event: dict) -> str:
        """Convert a weather event dict to a searchable text document."""
        zone = event.get("zone", event.get("zone_id", "unknown"))
        parts = [
            f"Zone: {zone}",
            f"Weather severity: {event.get('severity', 'UNKNOWN')}",
            f"Rainfall: {event.get('rainfall', 0)}mm",
            f"Wind speed: {event.get('wind_speed', 0)}km/h",
            f"Humidity: {event.get('humidity', 0)}%",
            f"Temperature: {event.get('temperature', 0)}°C",
            f"Confidence: {event.get('confidence', 0):.2f}",
        ]
        if event.get("routing_decision"):
            parts.append(f"Routing: {event['routing_decision']}")
        return " | ".join(parts)

    @staticmethod
    def _detection_to_document(event: dict) -> str:
        """Convert a detection event dict to a searchable text document."""
        parts = [
            f"Zone: {event.get('zone_id', 'unknown')}",
            f"Crowd density: {event.get('crowd_density', 0):.3f}",
            f"Flood level: {event.get('flood_level', 0):.3f}",
            f"Structural damage: {event.get('structural_damage', 0):.3f}",
            f"Fire detected: {event.get('fire_detected', False)}",
            f"Vehicle count: {event.get('vehicle_count', 0)}",
            f"Detection confidence: {event.get('confidence', 0):.3f}",
        ]
        return " | ".join(parts)

    @staticmethod
    def _zone_event_to_document(event_data: dict) -> str:
        """Convert zone event dict to a searchable text document."""
        parts = [f"Zone: {event_data.get('zone_id', 'unknown')}"]

        if event_data.get("decision"):
            parts.append(f"Decision: {event_data['decision']}")

        if event_data.get("detection"):
            det = event_data["detection"]
            parts.append(
                f"Detection: crowd_density={det.get('crowd_density', 0):.2f}, "
                f"flood_level={det.get('flood_level', 0):.2f}, "
                f"structural_damage={det.get('structural_damage', 0):.2f}, "
                f"fire={det.get('fire_detected', False)}"
            )

        if event_data.get("weather_severity"):
            parts.append(f"Weather severity: {event_data['weather_severity']}")

        if event_data.get("priority"):
            parts.append(f"Priority score: {event_data['priority']:.2f}")

        return " | ".join(parts)


# ── ChromaDB Embedding Function Adapter ──────────────────────


class SentenceTransformerEmbeddingFunction:
    """
    Adapter that wraps our EmbeddingPipeline to conform to
    ChromaDB's EmbeddingFunction protocol.
    """

    def name(self) -> str:
        return "raksha_sentence_transformer"

    def __init__(self, pipeline):
        self._pipeline = pipeline

    def __call__(self, input: list[str]) -> list[list[float]]:
        """Embed a list of documents (ChromaDB protocol)."""
        # Flatten nested lists that ChromaDB may pass
        flat_input = []
        for item in input:
            if isinstance(item, list):
                flat_input.extend(item)
            else:
                flat_input.append(item)
        return self._pipeline.embed_batch(flat_input)

    def embed_query(self, query: str = "", **kwargs) -> list[float]:
        """Embed a single query string (used by ChromaDB during .query())."""
        text = query or kwargs.get("input", "")
        # Handle case where text is a list
        if isinstance(text, list):
            text = text[0] if text else ""
        return self._pipeline.embed_text(text)


# ── Module-level Singleton ───────────────────────────────────

_store_instance: RAGMemoryStore | None = None
_store_lock = threading.Lock()


def get_memory_store() -> RAGMemoryStore:
    """Get or create the global RAGMemoryStore singleton."""
    global _store_instance
    if _store_instance is None:
        with _store_lock:
            if _store_instance is None:
                _store_instance = RAGMemoryStore()
    return _store_instance
