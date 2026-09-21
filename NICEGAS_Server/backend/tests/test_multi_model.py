import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.config import Settings
from app.schemas.ai import AIChatResponse, TokenUsage
from app.services.ai.base import ChatMessage
from app.services.ai.providers.dmr import DMRProvider
from app.services.ai.service import AIService


# ==========================================
# 1. Config Model Resolution Tests
# ==========================================

def test_resolve_model_defaults():
    """When task-specific models are not configured, fallback to AI_MODEL."""
    cfg = Settings(
        AI_MODEL="fallback-model:latest",
        AI_MODEL_CHAT="",
        AI_MODEL_ANALYSIS="",
        AI_MODEL_GENERAL="",
    )
    assert cfg.resolve_model("chat") == "fallback-model:latest"
    assert cfg.resolve_model("analysis") == "fallback-model:latest"
    assert cfg.resolve_model("general") == "fallback-model:latest"
    assert cfg.resolve_model("unknown_task") == "fallback-model:latest"


def test_resolve_model_task_specific():
    """When task-specific models are set, resolve_model returns the specific one."""
    cfg = Settings(
        AI_MODEL="fallback:latest",
        AI_MODEL_CHAT="chat-model:latest",
        AI_MODEL_ANALYSIS="analysis-model:latest",
        AI_MODEL_GENERAL="general-model:latest",
    )
    assert cfg.resolve_model("chat") == "chat-model:latest"
    assert cfg.resolve_model("analysis") == "analysis-model:latest"
    assert cfg.resolve_model("general") == "general-model:latest"
    assert cfg.resolve_model("unknown") == "fallback:latest"


# ==========================================
# 2. DMRProvider Model Override Tests
# ==========================================

@pytest.mark.asyncio
async def test_dmr_provider_uses_default_model_when_no_override():
    provider = DMRProvider(base_url="http://mock-dmr/v1", model="default-model:latest")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "1",
        "model": "default-model:latest",
        "choices": [{"message": {"role": "assistant", "content": "hello"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    }
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = await provider.chat(messages=[ChatMessage(role="user", content="hi")])
        
        sent_payload = mock_post.call_args[1]["json"]
        assert sent_payload["model"] == "default-model:latest"
        assert res.model == "default-model:latest"


@pytest.mark.asyncio
async def test_dmr_provider_uses_model_override():
    provider = DMRProvider(base_url="http://mock-dmr/v1", model="default-model:latest")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "2",
        "model": "special-override-model:latest",
        "choices": [{"message": {"role": "assistant", "content": "override hello"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    }
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = await provider.chat(
            messages=[ChatMessage(role="user", content="hi")],
            model_override="special-override-model:latest",
        )
        
        sent_payload = mock_post.call_args[1]["json"]
        assert sent_payload["model"] == "special-override-model:latest"
        assert res.model == "special-override-model:latest"


# ==========================================
# 3. AIService Routing Tests
# ==========================================

@pytest.mark.asyncio
async def test_ai_service_chat_routing_to_chat_model():
    mock_provider = AsyncMock()
    mock_provider.chat.return_value = AIChatResponse(
        content="mock answer",
        model="resolved-chat-model",
        provider="mock",
        latency_ms=10.0,
    )
    
    service = AIService(provider=mock_provider)
    
    with patch("app.services.ai.service.settings") as mock_settings:
        mock_settings.AI_PROVIDER = "mock"
        mock_settings.AI_MAX_TOKENS = 512
        mock_settings.resolve_model.return_value = "resolved-chat-model"
        
        resp = await service.chat(message="Halo NEXA")
        
        mock_settings.resolve_model.assert_called_with("chat")
        assert mock_provider.chat.call_args.kwargs["model_override"] == "resolved-chat-model"
        assert resp.content == "mock answer"


@pytest.mark.asyncio
async def test_ai_service_analyze_telemetry_routes_to_analysis_model():
    mock_provider = AsyncMock()
    valid_json = """
    {
      "status": "normal",
      "observations": ["Temperature 37.5 C is normal."],
      "possible_causes": [],
      "recommended_checks": ["Continue normal operation."],
      "summary": "Biodigester operating normally."
    }
    """
    mock_provider.chat.return_value = AIChatResponse(
        content=valid_json,
        model="analysis-model-8b",
        provider="mock",
        latency_ms=15.0,
    )
    
    service = AIService(provider=mock_provider)
    
    with patch("app.services.ai.service.settings") as mock_settings:
        mock_settings.AI_PROVIDER = "mock"
        mock_settings.AI_MAX_TOKENS = 512
        mock_settings.resolve_model.return_value = "analysis-model-8b"
        
        raw_telemetry = {"temperature": 37.5, "pressure": 1.25, "methane": 60.0, "ph": 7.1}
        resp = await service.analyze_telemetry(
            telemetry=raw_telemetry,
            component="biodigester",
            device_name="DIGESTER-01",
        )
        
        mock_settings.resolve_model.assert_called_with("analysis")
        assert mock_provider.chat.call_args.kwargs["model_override"] == "analysis-model-8b"
        assert resp.result.status == "normal"
