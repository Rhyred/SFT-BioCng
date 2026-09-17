"""NICEGAS AI Service Orchestrator.

Provides provider-agnostic, domain-grounded AI capabilities to the backend and clients.
"""

import logging
from typing import Optional, Dict, Any

from app.core.config import settings
from app.schemas.ai import (
    AIChatResponse,
    AIHealthStatus,
    AIModelMetadata,
    TelemetryAnalysisResponse,
)
from app.services.ai.base import AIProvider, ChatMessage
from app.services.ai.factory import get_ai_provider
from app.services.ai.normalization import normalize_telemetry_payload
from app.services.ai.pre_analysis import run_deterministic_pre_analysis
from app.services.ai.prompts import (
    CHAT_SYSTEM_PROMPT,
    build_telemetry_system_prompt,
    build_telemetry_prompt,
    parse_telemetry_analysis_json,
)

logger = logging.getLogger(__name__)


class AIService:
    """NICEGAS AI Service orchestrator.
    
    Combines deterministic domain intelligence, telemetry normalization,
    and LLM semantic reasoning.
    """

    def __init__(self, provider: Optional[AIProvider] = None):
        self._provider = provider

    @property
    def provider(self) -> AIProvider:
        if self._provider is None:
            self._provider = get_ai_provider()
        return self._provider

    async def chat(
        self,
        message: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AIChatResponse:
        """Sends a generic chat query through the configured provider."""
        # Enforce parameter bounds
        bounded_temperature = None
        if temperature is not None:
            bounded_temperature = max(0.0, min(1.0, float(temperature)))

        bounded_max_tokens = None
        if max_tokens is not None:
            bounded_max_tokens = max(1, min(2048, int(max_tokens)))

        # Default to domain chat system prompt if not specified
        effective_system = system if system is not None else CHAT_SYSTEM_PROMPT

        messages = [ChatMessage(role="user", content=message)]

        logger.info(
            "[AI] provider=%s action=chat model=%s max_tokens=%s",
            settings.AI_PROVIDER,
            settings.AI_MODEL,
            bounded_max_tokens or settings.AI_MAX_TOKENS,
        )

        response = await self.provider.chat(
            messages=messages,
            system=effective_system,
            temperature=bounded_temperature,
            max_tokens=bounded_max_tokens,
        )

        logger.info(
            "[AI] provider=%s action=chat model=%s latency_ms=%.2f status=success",
            response.provider,
            response.model,
            response.latency_ms,
        )
        return response

    async def health(self) -> AIHealthStatus:
        """Checks the health of the underlying AI provider and model."""
        return await self.provider.health()

    async def metadata(self) -> AIModelMetadata:
        """Retrieves provider and model metadata."""
        return await self.provider.metadata()

    async def analyze_telemetry(
        self,
        telemetry: Dict[str, Any],
        component: Optional[str] = None,
        device_name: Optional[str] = None,
    ) -> TelemetryAnalysisResponse:
        """Analyzes Bio-CNG telemetry and returns a structured advisory response.
        
        Workflow:
        1. Normalize and sanitize raw telemetry inputs.
        2. Run deterministic pre-analysis against component domain rules.
        3. Build grounded component-specific prompt with pre-analysis context.
        4. Invoke LLM for semantic operational interpretation.
        5. Parse JSON and enforce deterministic status reconciliation.
        """
        # Step 1: Normalization
        normalized_ctx = normalize_telemetry_payload(
            telemetry=telemetry,
            component=component,
            device_name=device_name,
        )

        # Step 2: Deterministic Pre-Analysis
        pre_analysis = run_deterministic_pre_analysis(normalized_ctx)

        # Step 3: Component-specific Prompt Generation
        sys_prompt = build_telemetry_system_prompt(component=normalized_ctx.component)
        user_prompt = build_telemetry_prompt(
            telemetry=telemetry,
            component=normalized_ctx.component,
            device_name=normalized_ctx.device_name,
            pre_analysis=pre_analysis,
        )

        input_metrics_count = len(normalized_ctx.metrics)
        logger.info(
            "[AI] provider=%s action=analyze_telemetry component=%s device=%s input_metrics=%d deterministic_status=%s",
            settings.AI_PROVIDER,
            normalized_ctx.component or "unspecified",
            normalized_ctx.device_name or "none",
            input_metrics_count,
            pre_analysis.status,
        )

        # Step 4: LLM invocation
        chat_response = await self.chat(
            message=user_prompt,
            system=sys_prompt,
            temperature=0.1,  # Conservative low temperature for factual grounding
            max_tokens=512,
        )

        # Step 5: JSON parsing & deterministic status reconciliation
        structured_result = parse_telemetry_analysis_json(
            raw_text=chat_response.content,
            pre_analysis=pre_analysis,
        )

        logger.info(
            "[AI] provider=%s component=%s status=%s latency_ms=%.2f input_metrics=%d response_valid=%s",
            chat_response.provider,
            normalized_ctx.component or "unspecified",
            structured_result.status,
            chat_response.latency_ms,
            input_metrics_count,
            structured_result.status != "unknown" or pre_analysis.status == "unknown",
        )

        return TelemetryAnalysisResponse(
            result=structured_result,
            model=chat_response.model,
            provider=chat_response.provider,
            latency_ms=chat_response.latency_ms,
            raw_content=chat_response.content,
        )


# Global singleton instance for application use
ai_service = AIService()
