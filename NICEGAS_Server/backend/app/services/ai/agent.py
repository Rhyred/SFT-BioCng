"""NEXA Industrial AI Agent for NICEGAS Bio-CNG.

Provides multi-round autonomous tool calling with deterministic safety bounds.
Priority #4: Tools are READ-ONLY.
Priority #5: Scoped to authenticated user's permissions.
Priority #6: Scope enforced at executor layer — LLM cannot bypass.
Priority #7: NEXA cannot control actuators.
Priority #8: Initial deployment uses get_plant_overview tool.
"""

import json
import logging
import time
import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.schemas.ai import AgentChatResponse, ToolInvocation, TokenUsage
from app.services.ai.base import ChatMessage
from app.services.ai.prompts import AGENT_SYSTEM_PROMPT
from app.services.ai.tools.definitions import TOOL_DEFINITIONS
from app.services.ai.tools.executor import execute_tool
from app.core.exceptions import AIException

logger = logging.getLogger(__name__)


class NexaAgent:
    """Autonomous agent executing tool calls for Bio-CNG operations queries."""

    def __init__(self, ai_service: Optional[Any] = None):
        self._ai_service = ai_service

    @property
    def ai_service(self):
        if self._ai_service is None:
            from app.services.ai.service import ai_service
            self._ai_service = ai_service
        return self._ai_service

    async def run(
        self,
        message: str,
        db: Session,
        user: User,
        system: Optional[str] = None,
        project_id: Optional[uuid.UUID] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_rounds: Optional[int] = None,
        model_override: Optional[str] = None,
    ) -> AgentChatResponse:
        """Runs the multi-round agent loop with tool calling."""
        start_time = time.perf_counter()
        effective_system = system or AGENT_SYSTEM_PROMPT
        # Resolve model: agent uses AI_MODEL_GENERAL if set, otherwise AI_MODEL
        effective_model = model_override or settings.resolve_model("general")
        max_rounds_limit = min(max_rounds or settings.AI_AGENT_MAX_TOOL_ROUNDS, 10)

        logger.info(
            "[Agent] user=%s message_len=%d model=%s max_rounds=%d scoped_project_id=%s",
            user.username,
            len(message),
            effective_model,
            max_rounds_limit,
            project_id,
        )

        messages: List[ChatMessage] = [
            ChatMessage(role="user", content=message)
        ]
        tool_invocations: List[ToolInvocation] = []
        last_response = None

        for round_idx in range(max_rounds_limit):
            logger.info("[Agent] round=%d requesting completion...", round_idx + 1)

            response = await self.ai_service.provider.chat(
                messages=messages,
                system=effective_system,
                temperature=temperature,
                max_tokens=max_tokens,
                model_override=effective_model,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )
            last_response = response

            # Check if model requested tool calls
            if response.tool_calls:
                logger.info(
                    "[Agent] round=%d received %d tool call(s)",
                    round_idx + 1,
                    len(response.tool_calls),
                )

                # Append assistant message with tool_calls
                messages.append(
                    ChatMessage(
                        role="assistant",
                        content=response.content or "",
                        tool_calls=response.tool_calls,
                    )
                )

                # Execute each tool call and append tool results
                for tc in response.tool_calls:
                    call_id = tc.get("id") or str(uuid.uuid4())
                    fn = tc.get("function", {})
                    fn_name = fn.get("name", "")
                    raw_args = fn.get("arguments", {})

                    # Parse arguments safely
                    if isinstance(raw_args, str):
                        try:
                            args = json.loads(raw_args) if raw_args.strip() else {}
                        except json.JSONDecodeError:
                            logger.warning("[Agent] failed to parse tool args JSON: %s", raw_args)
                            args = {}
                    elif isinstance(raw_args, dict):
                        args = raw_args
                    else:
                        args = {}

                    # Execute read-only tool under authenticated context
                    try:
                        tool_result = execute_tool(
                            name=fn_name,
                            arguments=args,
                            db=db,
                            user=user,
                            scoped_project_id=project_id,
                        )
                    except Exception as exc:
                        logger.error("[Agent] tool execution error (%s): %s", fn_name, exc)
                        tool_result = {"error": f"Tool execution failed: {str(exc)}"}

                    tool_invocations.append(
                        ToolInvocation(
                            tool_name=fn_name,
                            arguments=args,
                            result=tool_result,
                        )
                    )

                    messages.append(
                        ChatMessage(
                            role="tool",
                            tool_call_id=call_id,
                            name=fn_name,
                            content=json.dumps(tool_result),
                        )
                    )
            else:
                # Model finished with text response
                logger.info("[Agent] round=%d completed with text response", round_idx + 1)
                break
        else:
            # Reached max_rounds_limit while still asking for tools.
            # Perform one final completion without tools to obtain text summary.
            logger.warning("[Agent] max rounds (%d) reached, requesting final summary", max_rounds_limit)
            last_response = await self.ai_service.provider.chat(
                messages=messages,
                system=effective_system,
                temperature=temperature,
                max_tokens=max_tokens,
                model_override=effective_model,
                tools=None,
            )

        total_latency = round((time.perf_counter() - start_time) * 1000, 2)

        return AgentChatResponse(
            content=last_response.content if last_response else "",
            model=last_response.model if last_response else effective_model,
            provider=last_response.provider if last_response else settings.AI_PROVIDER,
            latency_ms=total_latency,
            tool_invocations=tool_invocations,
            usage=last_response.usage if last_response else None,
            finish_reason=last_response.finish_reason if last_response else "stop",
        )


nexa_agent = NexaAgent()
