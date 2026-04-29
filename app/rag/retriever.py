"""
RakshaSetu — RAG Retrieval System
Composes relevant past context from weather + detection history
and formats it for consumption by the Zone Analyst and other agents.

This module provides the high-level retrieval interface that agents use
to get enriched context before making decisions.
"""


import logging
from typing import Optional

from app.rag.memory import get_memory_store

logger = logging.getLogger("raksha.rag.retriever")


class RAGRetriever:
    """
    High-level retrieval system that combines weather and detection
    history into a unified context package for agent consumption.

    Usage:
        retriever = RAGRetriever()
        context = retriever.get_zone_context(
            zone_id="zone_001",
            current_weather={"severity": "HIGH", "rainfall": 80},
            current_detection={"crowd_density": 0.6, "flood_level": 0.4},
        )
        # context is a dict with 'weather_history', 'detection_history',
        # 'zone_events', and 'summary' fields ready for LLM prompts.
    """

    def __init__(self):
        self._store = get_memory_store()

    def get_zone_context(
        self,
        zone_id: str,
        current_weather: Optional[dict] = None,
        current_detection: Optional[dict] = None,
        n_weather: int = 5,
        n_detection: int = 5,
        n_events: int = 3,
    ) -> dict:
        """
        Retrieve comprehensive historical context for a zone.

        Combines:
          1. Similar past weather events
          2. Similar past detection events
          3. Past zone analysis decisions

        Args:
            zone_id: Target zone identifier.
            current_weather: Current weather data (used to find similar past events).
            current_detection: Current detection data (used to find similar events).
            n_weather: Max weather history results.
            n_detection: Max detection history results.
            n_events: Max zone event results.

        Returns:
            Dict with structured context ready for LLM consumption.
        """
        context = {
            "weather_history": [],
            "detection_history": [],
            "zone_events": [],
            "summary": "",
        }

        # ── 1. Retrieve weather history ──────────────────────
        weather_query = self._build_weather_query(zone_id, current_weather)
        try:
            weather_results = self._store.retrieve_weather_history(
                query=weather_query,
                n_results=n_weather,
                zone_filter=zone_id,
            )
            context["weather_history"] = self._format_results(weather_results)
        except Exception as e:
            logger.warning(f"Weather history retrieval failed: {e}")

        # ── 2. Retrieve detection history ────────────────────
        detection_query = self._build_detection_query(zone_id, current_detection)
        try:
            detection_results = self._store.retrieve_detection_history(
                query=detection_query,
                n_results=n_detection,
                zone_filter=zone_id,
            )
            context["detection_history"] = self._format_results(detection_results)
        except Exception as e:
            logger.warning(f"Detection history retrieval failed: {e}")

        # ── 3. Retrieve past zone events ─────────────────────
        events_query = f"Past disaster analysis decisions for zone {zone_id}"
        try:
            events_results = self._store.retrieve_zone_events(
                query=events_query,
                n_results=n_events,
                zone_filter=zone_id,
            )
            context["zone_events"] = self._format_results(events_results)
        except Exception as e:
            logger.warning(f"Zone events retrieval failed: {e}")

        # ── 4. Build summary ─────────────────────────────────
        context["summary"] = self._build_summary(context)

        logger.info(
            f"RAG context assembled for zone {zone_id}: "
            f"weather={len(context['weather_history'])}, "
            f"detection={len(context['detection_history'])}, "
            f"events={len(context['zone_events'])}"
        )

        return context

    def get_similar_weather(
        self,
        severity: str,
        rainfall: float,
        zone_id: Optional[str] = None,
        n_results: int = 5,
    ) -> list[dict]:
        """
        Find past weather events similar to a given weather profile.

        Useful for the Weather Agent to compare current conditions
        with historical patterns.
        """
        query = (
            f"Weather event: severity={severity}, rainfall={rainfall}mm"
            + (f" in zone {zone_id}" if zone_id else "")
        )

        results = self._store.retrieve_weather_history(
            query=query,
            n_results=n_results,
            zone_filter=zone_id,
            severity_filter=severity,
        )
        return self._format_results(results)

    def get_similar_detections(
        self,
        crowd_density: float,
        flood_level: float,
        zone_id: Optional[str] = None,
        n_results: int = 5,
    ) -> list[dict]:
        """
        Find past detection events similar to given detection data.
        """
        query = (
            f"Detection event: crowd_density={crowd_density:.2f}, "
            f"flood_level={flood_level:.2f}"
            + (f" in zone {zone_id}" if zone_id else "")
        )

        results = self._store.retrieve_detection_history(
            query=query,
            n_results=n_results,
            zone_filter=zone_id,
        )
        return self._format_results(results)

    def format_context_for_prompt(self, context: dict) -> str:
        """
        Format a context dict into a string suitable for LLM prompts.

        Converts the structured context into human-readable text
        that can be injected into agent system/user prompts.
        """
        sections = []

        if context.get("weather_history"):
            sections.append("## Past Weather Events (most similar)")
            for i, item in enumerate(context["weather_history"], 1):
                sections.append(f"  {i}. {item['document']}")
                if item.get("metadata", {}).get("timestamp"):
                    sections.append(f"     (recorded: {item['metadata']['timestamp']})")

        if context.get("detection_history"):
            sections.append("\n## Past Detection Events (most similar)")
            for i, item in enumerate(context["detection_history"], 1):
                sections.append(f"  {i}. {item['document']}")

        if context.get("zone_events"):
            sections.append("\n## Past Zone Analysis Decisions")
            for i, item in enumerate(context["zone_events"], 1):
                sections.append(f"  {i}. {item['document']}")

        if context.get("summary"):
            sections.append(f"\n## Context Summary\n{context['summary']}")

        return "\n".join(sections) if sections else "No historical context available."

    # ── Private Helpers ──────────────────────────────────────

    @staticmethod
    def _build_weather_query(zone_id: str, current_weather: Optional[dict]) -> str:
        """Build a natural language query for weather similarity search."""
        if current_weather:
            severity = current_weather.get("severity", "UNKNOWN")
            rainfall = current_weather.get("rainfall", 0)
            wind = current_weather.get("wind_speed", 0)
            return (
                f"Weather in zone {zone_id}: severity={severity}, "
                f"rainfall={rainfall}mm, wind_speed={wind}km/h"
            )
        return f"Weather history for zone {zone_id}"

    @staticmethod
    def _build_detection_query(zone_id: str, current_detection: Optional[dict]) -> str:
        """Build a natural language query for detection similarity search."""
        if current_detection:
            crowd = current_detection.get("crowd_density", 0)
            flood = current_detection.get("flood_level", 0)
            damage = current_detection.get("structural_damage", 0)
            return (
                f"Detection in zone {zone_id}: "
                f"crowd_density={crowd:.2f}, flood_level={flood:.2f}, "
                f"structural_damage={damage:.2f}"
            )
        return f"Detection history for zone {zone_id}"

    @staticmethod
    def _format_results(results: dict) -> list[dict]:
        """Convert ChromaDB query results to a list of structured dicts."""
        formatted = []
        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        for doc, dist, meta in zip(documents, distances, metadatas):
            formatted.append({
                "document": doc,
                "similarity": round(1.0 - dist, 4),  # ChromaDB cosine distance → similarity
                "metadata": meta,
            })

        return formatted

    @staticmethod
    def _build_summary(context: dict) -> str:
        """Build a concise summary of the retrieved context."""
        parts = []

        n_weather = len(context.get("weather_history", []))
        n_detection = len(context.get("detection_history", []))
        n_events = len(context.get("zone_events", []))

        if n_weather == 0 and n_detection == 0 and n_events == 0:
            return "No historical context available — this may be the first event for this zone."

        if n_weather > 0:
            severities = [
                item.get("metadata", {}).get("severity", "?")
                for item in context["weather_history"]
            ]
            parts.append(
                f"Found {n_weather} similar weather events "
                f"(severities: {', '.join(severities)})"
            )

        if n_detection > 0:
            parts.append(f"Found {n_detection} similar detection events")

        if n_events > 0:
            decisions = [
                item.get("metadata", {}).get("decision", "?")
                for item in context["zone_events"]
            ]
            parts.append(
                f"Found {n_events} past analysis decisions "
                f"(outcomes: {', '.join(decisions)})"
            )

        return ". ".join(parts) + "."


# ── Module-level convenience ─────────────────────────────────

_retriever_instance: RAGRetriever | None = None


def get_retriever() -> RAGRetriever:
    """Get or create the global RAGRetriever singleton."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = RAGRetriever()
    return _retriever_instance
