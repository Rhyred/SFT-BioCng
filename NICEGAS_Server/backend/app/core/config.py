from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    ENVIRONMENT: str = "local"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # PostgreSQL config
    DATABASE_HOST: str
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str

    # MQTT config
    MQTT_HOST: str = "mqtt"
    MQTT_PORT: int = 1883
    MQTT_USER: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    MQTT_CLIENT_ID: str = "nicegas-backend-consumer"
    MQTT_KEEPALIVE: int = 60
    MQTT_RECONNECT_DELAY: int = 5

    # JWT / Auth config (Environment-driven, development fallback for local testing)
    JWT_SECRET_KEY: str = "nicegas-insecure-dev-secret-key-change-in-env-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # AI Service config
    AI_PROVIDER: str = "dmr"
    AI_BASE_URL: str = "http://model-runner.docker.internal/v1"
    AI_MODEL: str = "huggingface.co/huggingfacetb/smollm2-1.7b-instruct-gguf:latest"
    AI_TIMEOUT_SECONDS: float = 30.0
    AI_MAX_TOKENS: int = 512
    AI_TEMPERATURE: float = 0.2

    # Multi-model routing (empty string falls back to AI_MODEL)
    AI_MODEL_CHAT: str = ""
    AI_MODEL_ANALYSIS: str = ""
    AI_MODEL_GENERAL: str = ""

    # Agent settings (Phase 2+)
    AI_AGENT_MAX_TOOL_ROUNDS: int = 5

    def resolve_model(self, task: str = "chat") -> str:
        """Resolves the model ID for a given task, falling back to AI_MODEL."""
        if task == "chat" and self.AI_MODEL_CHAT:
            return self.AI_MODEL_CHAT
        elif task == "analysis" and self.AI_MODEL_ANALYSIS:
            return self.AI_MODEL_ANALYSIS
        elif task == "general" and self.AI_MODEL_GENERAL:
            return self.AI_MODEL_GENERAL
        return self.AI_MODEL

    @property
    def database_url(self) -> str:
        return f"postgresql+psycopg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
