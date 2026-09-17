from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from app.schemas.ai import AIChatResponse, AIHealthStatus, AIModelMetadata


class ChatMessage(BaseModel):
    role: str
    content: str


class AIProvider(ABC):
    """Abstract interface for all NICEGAS AI providers."""

    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AIChatResponse:
        """Sends a conversation history to the AI provider and returns a normalized response."""
        pass

    @abstractmethod
    async def health(self) -> AIHealthStatus:
        """Performs a health check on the underlying model and provider runtime."""
        pass

    @abstractmethod
    async def metadata(self) -> AIModelMetadata:
        """Returns metadata about the active provider and loaded model."""
        pass
