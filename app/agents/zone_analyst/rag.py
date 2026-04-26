"""
RakshaSetu — Zone Analyst RAG Module
Delegates to the centralized RAG memory system in app.rag.

This module provides the ZoneRAG class as a backward-compatible facade
over the centralized RAGMemoryStore and RAGRetriever.
"""

import logging
from typing import Optional

from app.rag.memory import get_memory_store
from app.rag.retriever import get_retriever

logger = logging.getLogger(__name__)


class ZoneRAG:
    """
    RAG system for the Zone Analyst agent.

    Delegates to the centralized RAGMemoryStore for storage and
    RAGRetriever for retrieval, maintaining the same public API
    for backward compatibility.
    """

    def __init__(self, collection_name: str = "zone_events"):
        self._store = get_memory_store()
        self._retriever = get_retriever()
        logger.info(
            f"ZoneRAG initialized (delegating to centralized RAG), "
            f"existing_docs={self._store.get_stats()['collections'].get(collection_name, 0)}"
        )

    def ingest_event(self, event_data: dict) -> str:
        """
        Ingest a zone event into the centralized RAG memory.

        Args:
            event_data: Dict with zone_id, decision, detection, weather_severity, etc.

        Returns:
            The document ID assigned to this event.
        """
        # Also ingest detection data into the detection collection if present
        if event_data.get("detection"):
            detection = event_data["detection"].copy()
            detection["zone_id"] = event_data.get("zone_id", "unknown")
            try:
                self._store.ingest_detection_event(detection)
            except Exception as e:
                logger.warning(f"Detection ingestion failed: {e}")

        return self._store.ingest_zone_event(event_data)

    def retrieve_similar_events(
        self,
        query: str,
        n_results: int = 5,
        zone_filter: Optional[str] = None,
    ) -> dict:
        """
        Retrieve similar past events using semantic search.
        Delegates to the centralized memory store.
        """
        return self._store.retrieve_zone_events(
            query=query,
            n_results=n_results,
            zone_filter=zone_filter,
        )

    def retrieve_by_zone(self, zone_id: str, n_results: int = 10) -> dict:
        """Retrieve past events for a specific zone."""
        return self.retrieve_similar_events(
            query=f"Historical events for zone {zone_id}",
            n_results=n_results,
            zone_filter=zone_id,
        )

    def get_full_context(
        self,
        zone_id: str,
        current_weather: dict = None,
        current_detection: dict = None,
    ) -> dict:
        """
        Get comprehensive RAG context combining weather, detection,
        and zone event history. Returns structured context dict.
        """
        return self._retriever.get_zone_context(
            zone_id=zone_id,
            current_weather=current_weather,
            current_detection=current_detection,
        )

    def format_context_for_prompt(self, context: dict) -> str:
        """Format the context dict into a string for LLM prompts."""
        return self._retriever.format_context_for_prompt(context)

    def get_stats(self) -> dict:
        """Return collection statistics."""
        return self._store.get_stats()
