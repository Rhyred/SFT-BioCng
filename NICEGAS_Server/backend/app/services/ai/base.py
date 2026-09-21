from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.schemas.ai import AIChatResponse, AIHealthStatus, AIModelMetadata


class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class AIProvider(ABC):
    """Abstract interface for all NICEGAS AI providers."""

    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model_override: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
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
