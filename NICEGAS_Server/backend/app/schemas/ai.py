from pydantic import BaseModel, Field, UUID4, ConfigDict
from typing import Optional, List, Dict, Any, Literal


class TokenUsage(BaseModel):
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class AIModelMetadata(BaseModel):
    provider: str
    model: str
    context_window: Optional[int] = None
    supported_features: List[str] = Field(default_factory=list)


class AIHealthStatus(BaseModel):
    provider: str
    status: Literal["ready", "degraded", "unavailable"]
    model: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User prompt message")
    system: Optional[str] = Field(None, description="Optional system guidance context")
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0, description="Sampling temperature (bounded 0.0 - 1.0)")
    max_tokens: Optional[int] = Field(None, ge=1, le=2048, description="Maximum completion tokens (bounded 1 - 2048)")


class AIChatResponse(BaseModel):
    content: Optional[str] = ""
    model: str
    provider: str
    latency_ms: float
    usage: Optional[TokenUsage] = None
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ToolInvocation(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    result: Any


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User prompt message")
    system: Optional[str] = Field(None, description="Optional system guidance context override")
    project_id: Optional[UUID4] = Field(None, description="Optional target project ID context scope")
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0, description="Sampling temperature (0.0 - 1.0)")
    max_tokens: Optional[int] = Field(None, ge=1, le=2048, description="Maximum tokens per step")
    max_rounds: Optional[int] = Field(None, ge=1, le=10, description="Maximum agent tool rounds (default from config)")
    model: Optional[str] = Field(None, description="Optional model ID override (e.g. docker.io/ai/qwen3:8b-q4_K_M or docker.io/ai/qwen3.5:latest)")


class AgentChatResponse(BaseModel):
    content: str
    model: str
    provider: str
    latency_ms: float
    tool_invocations: List[ToolInvocation] = Field(default_factory=list)
    usage: Optional[TokenUsage] = None
    finish_reason: Optional[str] = None


class AIHealthResponse(BaseModel):
    provider: str
    status: Literal["ready", "degraded", "unavailable"]
    model: str
    latency_ms: Optional[float] = None


class TelemetryAnalysisRequest(BaseModel):
    project_id: Optional[UUID4] = None
    device_id: Optional[UUID4] = None
    component: Optional[str] = None
    telemetry: Dict[str, Any] = Field(..., description="Telemetry metric dictionary")


class TelemetryAnalysisResult(BaseModel):
    status: Literal["normal", "warning", "critical", "unknown"] = "unknown"
    observations: List[str] = Field(default_factory=list, description="Factual observed parameters")
    possible_causes: List[str] = Field(default_factory=list, description="Inferred potential process causes")
    recommended_checks: List[str] = Field(default_factory=list, description="Recommended safe operator checks")
    summary: str = Field(..., description="Concise advisory summary")


class TelemetryAnalysisResponse(BaseModel):
    result: TelemetryAnalysisResult
    model: str
    provider: str
    latency_ms: float
    raw_content: Optional[str] = None
