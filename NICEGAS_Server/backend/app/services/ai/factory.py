import logging
from typing import Optional

from app.core.config import settings
from app.services.ai.base import AIProvider
from app.services.ai.providers.dmr import DMRProvider

logger = logging.getLogger(__name__)


def get_ai_provider(provider_type: Optional[str] = None) -> AIProvider:
    """Factory function resolving the configured AI provider."""
    provider_name = (provider_type or settings.AI_PROVIDER).lower()
    
    if provider_name == "dmr":
        return DMRProvider(
            base_url=settings.AI_BASE_URL,
            model=settings.AI_MODEL,
            timeout_seconds=settings.AI_TIMEOUT_SECONDS,
        )
    # Future providers will be registered here (e.g., android, ollama, cloud)
    elif provider_name == "android":
        raise NotImplementedError("Android local provider is not yet enabled in this environment")
    elif provider_name == "ollama":
        raise NotImplementedError("Ollama provider is not yet enabled in this environment")
    elif provider_name == "cloud":
        raise NotImplementedError("Cloud LLM provider is not yet enabled in this environment")
    else:
        logger.warning(
            "Unknown AI provider '%s' requested. Falling back to DMR provider.",
            provider_name,
        )
        return DMRProvider(
            base_url=settings.AI_BASE_URL,
            model=settings.AI_MODEL,
            timeout_seconds=settings.AI_TIMEOUT_SECONDS,
        )
