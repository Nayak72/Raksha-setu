"""
RakshaSetu — Global Settings
Consolidates Phase 1 (FastAPI) and Phase 4 (LangGraph) configuration.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class OllamaSettings(BaseModel):
    """Ollama local LLM configuration."""
    base_url: str = Field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    model: str = Field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen2.5:7b"))
    temperature: float = Field(default_factory=lambda: float(os.getenv("OLLAMA_TEMPERATURE", "0.7")))


class SupabaseSettings(BaseModel):
    """Supabase / PostgreSQL connection configuration."""
    url: str = Field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    anon_key: str = Field(default_factory=lambda: os.getenv("SUPABASE_ANON_KEY", ""))
    service_key: str = Field(default_factory=lambda: os.getenv("SUPABASE_SERVICE_KEY", ""))
    db_host: str = Field(default_factory=lambda: os.getenv("SUPABASE_DB_HOST", "localhost"))
    db_port: int = Field(default_factory=lambda: int(os.getenv("SUPABASE_DB_PORT", "5432")))
    db_name: str = Field(default_factory=lambda: os.getenv("SUPABASE_DB_NAME", "postgres"))
    db_user: str = Field(default_factory=lambda: os.getenv("SUPABASE_DB_USER", "postgres"))
    db_password: str = Field(default_factory=lambda: os.getenv("SUPABASE_DB_PASSWORD", ""))

    @property
    def connection_string(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


class ChromaSettings(BaseModel):
    """ChromaDB vector store configuration."""
    persist_dir: str = Field(default_factory=lambda: os.getenv("CHROMA_PERSIST_DIR", "./data/chromadb"))


class MQTTSettings(BaseModel):
    """Mosquitto MQTT broker configuration."""
    broker_host: str = Field(default_factory=lambda: os.getenv("MQTT_BROKER_HOST", "localhost"))
    broker_port: int = Field(default_factory=lambda: int(os.getenv("MQTT_BROKER_PORT", "1883")))
    username: str = Field(default_factory=lambda: os.getenv("MQTT_USERNAME", ""))
    password: str = Field(default_factory=lambda: os.getenv("MQTT_PASSWORD", ""))
    client_id: str = Field(default_factory=lambda: os.getenv("MQTT_CLIENT_ID", "raksha-sethu-server"))


class RAGSettings(BaseModel):
    """RAG / embedding configuration."""
    embedding_model: str = Field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
    vector_dimension: int = Field(default_factory=lambda: int(os.getenv("VECTOR_DIMENSION", "384")))


class Settings(BaseModel):
    """Master settings aggregator."""
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    supabase: SupabaseSettings = Field(default_factory=SupabaseSettings)
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)
    mqtt: MQTTSettings = Field(default_factory=MQTTSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)
    
    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    app_debug: bool = Field(default_factory=lambda: os.getenv("APP_DEBUG", "True").lower() == "true")
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    @property
    def _embedding_model(self) -> str:
        """Convenience property for the embedding model name."""
        return self.rag.embedding_model

# Global singleton
settings = Settings()

def get_settings() -> Settings:
    return settings
