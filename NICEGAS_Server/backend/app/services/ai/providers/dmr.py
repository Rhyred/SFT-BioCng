import logging
import time
from typing import List, Optional
import httpx

from app.core.config import settings
from app.core.exceptions import (
    AIProviderUnavailableException,
    AIRequestTimeoutException,
    AIResponseInvalidException,
)
from app.schemas.ai import AIChatResponse, AIHealthStatus, AIModelMetadata, TokenUsage
from app.services.ai.base import AIProvider, ChatMessage

logger = logging.getLogger(__name__)


class DMRProvider(AIProvider):
    """Docker Model Runner (DMR) Provider implementation.
    
    Connects to the OpenAI-compatible REST API exposed by Docker Model Runner.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self.base_url = (base_url or settings.AI_BASE_URL).rstrip("/")
        self.model = model or settings.AI_MODEL
        self.timeout_seconds = timeout_seconds or settings.AI_TIMEOUT_SECONDS

    async def chat(
        self,
        messages: List[ChatMessage],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AIChatResponse:
        start_time = time.perf_counter()
        
        # Build OpenAI-compatible chat payload
        payload_messages = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        for msg in messages:
            payload_messages.append({"role": msg.role, "content": msg.content})

        payload = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature if temperature is not None else settings.AI_TEMPERATURE,
            "max_tokens": max_tokens if max_tokens is not None else settings.AI_MAX_TOKENS,
        }

        endpoint = f"{self.base_url}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            logger.error("DMR request timed out after %.1fs: %s", self.timeout_seconds, exc)
            raise AIRequestTimeoutException(
                f"DMR request timed out after {self.timeout_seconds}s"
            ) from exc
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            logger.error("DMR connection failure to %s: %s", self.base_url, exc)
            raise AIProviderUnavailableException(
                "Unable to connect to Docker Model Runner"
            ) from exc
        except httpx.HTTPStatusError as exc:
            logger.error("DMR returned HTTP error status %s: %s", exc.response.status_code, exc)
            raise AIProviderUnavailableException(
                f"DMR returned HTTP error {exc.response.status_code}"
            ) from exc
        except Exception as exc:
            logger.error("Unexpected error contacting DMR: %s", exc)
            raise AIResponseInvalidException(f"Failed to communicate with DMR: {str(exc)}") from exc

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Parse OpenAI-compatible structure safely
        try:
            choices = data.get("choices")
            if not choices or not isinstance(choices, list):
                raise ValueError("Response choices array is empty or missing")
            
            message_obj = choices[0].get("message") or {}
            content = message_obj.get("content", "")
            if not content:
                # Handle possible alternative choices format or empty string
                content = choices[0].get("text", "")
            
            usage_data = data.get("usage")
            usage = None
            if usage_data and isinstance(usage_data, dict):
                usage = TokenUsage(
                    input_tokens=usage_data.get("prompt_tokens"),
                    output_tokens=usage_data.get("completion_tokens"),
                    total_tokens=usage_data.get("total_tokens"),
                )

            return AIChatResponse(
                content=content,
                model=data.get("model", self.model),
                provider="dmr",
                latency_ms=latency_ms,
                usage=usage,
            )
        except Exception as exc:
            logger.error("Failed to parse DMR response payload: %s", exc)
            raise AIResponseInvalidException("Malformed response payload from DMR") from exc

    async def health(self) -> AIHealthStatus:
        start_time = time.perf_counter()
        endpoint = f"{self.base_url}/models"
        
        try:
            # Health check uses a short 5.0s timeout
            async with httpx.AsyncClient(timeout=min(self.timeout_seconds, 5.0)) as client:
                response = await client.get(endpoint)
                response.raise_for_status()
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return AIHealthStatus(
                    provider="dmr",
                    status="ready",
                    model=self.model,
                    latency_ms=latency_ms,
                )
        except httpx.TimeoutException:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return AIHealthStatus(
                provider="dmr",
                status="degraded",
                model=self.model,
                latency_ms=latency_ms,
                error="Health check timed out",
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return AIHealthStatus(
                provider="dmr",
                status="unavailable",
                model=self.model,
                latency_ms=latency_ms,
                error="Provider unreachable",
            )

    async def metadata(self) -> AIModelMetadata:
        return AIModelMetadata(
            provider="dmr",
            model=self.model,
            supported_features=["chat", "telemetry_analysis"],
        )
