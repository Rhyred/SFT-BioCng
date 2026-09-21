import uuid
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.project import Project
from app.models.device import Device
from app.models.alert import Alert
from app.models.user import User
from app.schemas.ai import AIChatResponse, TokenUsage
from app.services.ai.agent import NexaAgent
from app.services.ai.tools.executor import execute_tool
from app.services.ai.tools.definitions import TOOL_DEFINITIONS
from datetime import datetime, timezone


# ==========================================
# 1. Tool Executor Unit Tests (Read-Only & Scope)
# ==========================================

def test_execute_tool_unrecognized():
    mock_db = MagicMock()
    user = User(id=uuid.uuid4(), username="operator1", email="op@example.com", name="Operator 1")
    
    result = execute_tool("unknown_tool", {}, mock_db, user)
    assert "error" in result
    assert "not recognized" in result["error"]


def test_execute_get_plant_overview_success(db_session):
    # Setup test DB entities
    proj1 = Project(id=uuid.uuid4(), name="Plant Alpha", location="Riau")
    proj2 = Project(id=uuid.uuid4(), name="Plant Beta", location="Sumatra")
    db_session.add_all([proj1, proj2])
    db_session.commit()

    dev1 = Device(id=uuid.uuid4(), project_id=proj1.id, name="DEV-01", type="biodigester", status="online")
    dev2 = Device(id=uuid.uuid4(), project_id=proj1.id, name="DEV-02", type="compressor", status="offline")
    dev3 = Device(id=uuid.uuid4(), project_id=proj2.id, name="DEV-03", type="purifikasi", status="online")
    db_session.add_all([dev1, dev2, dev3])
    db_session.commit()

    alert1 = Alert(
        id=uuid.uuid4(),
        device_id=dev1.id,
        severity="warning",
        status="active",
        message="High temperature",
        timestamp=datetime.now(timezone.utc),
    )
    alert2 = Alert(
        id=uuid.uuid4(),
        device_id=dev1.id,
        severity="info",
        status="resolved",  # Resolved, should not count towards active
        message="Normalized",
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add_all([alert1, alert2])
    db_session.commit()

    user = User(id=uuid.uuid4(), username="operator1", email="op@example.com", name="Operator 1")

    # 1. Test query all projects
    res_all = execute_tool("get_plant_overview", {}, db_session, user)
    assert res_all["projects_count"] >= 2
    
    alpha = next(p for p in res_all["projects"] if p["project_id"] == str(proj1.id))
    assert alpha["project_name"] == "Plant Alpha"
    assert alpha["devices_total"] == 2
    assert alpha["devices_online"] == 1
    assert alpha["devices_offline"] == 1
    assert alpha["active_alerts"] == 1  # only active alert


def test_execute_get_plant_overview_scoped_precedence(db_session):
    """Priority #6: Scoped project_id in context MUST override LLM arguments."""
    proj1 = Project(id=uuid.uuid4(), name="Authorized Plant", location="Site A")
    proj2 = Project(id=uuid.uuid4(), name="Unauthorized Plant", location="Site B")
    db_session.add_all([proj1, proj2])
    db_session.commit()

    user = User(id=uuid.uuid4(), username="operator1", email="op@example.com", name="Operator 1")

    # LLM tries to query proj2 via argument, but auth context scopes to proj1
    res = execute_tool(
        "get_plant_overview",
        {"project_id": str(proj2.id)},  # LLM argument
        db_session,
        user,
        scoped_project_id=proj1.id,  # Enforced scope
    )

    assert res["projects_count"] == 1
    assert res["projects"][0]["project_id"] == str(proj1.id)
    assert res["projects"][0]["project_name"] == "Authorized Plant"


# ==========================================
# 2. NexaAgent Multi-Round Loop Tests
# ==========================================

@pytest.mark.asyncio
async def test_agent_direct_text_response():
    mock_service = MagicMock()
    mock_provider = AsyncMock()
    mock_provider.chat.return_value = AIChatResponse(
        content="Halo, ada yang bisa dibantu?",
        model="test-model",
        provider="mock",
        latency_ms=10.0,
        finish_reason="stop",
        tool_calls=None,
    )
    mock_service.provider = mock_provider

    agent = NexaAgent(ai_service=mock_service)
    mock_db = MagicMock()
    user = User(id=uuid.uuid4(), username="op", email="op@example.com", name="Operator")

    res = await agent.run(message="Halo", db=mock_db, user=user)

    assert res.content == "Halo, ada yang bisa dibantu?"
    assert len(res.tool_invocations) == 0
    assert mock_provider.chat.call_count == 1


@pytest.mark.asyncio
async def test_agent_tool_calling_round_trip(db_session):
    proj = Project(id=uuid.uuid4(), name="Bio-CNG Kampar", location="Riau")
    db_session.add(proj)
    db_session.commit()

    mock_service = MagicMock()
    mock_provider = AsyncMock()

    # Round 1: Model asks for tool call
    round1_resp = AIChatResponse(
        content="",
        model="qwen3:8b",
        provider="dmr",
        latency_ms=100.0,
        finish_reason="tool_calls",
        tool_calls=[
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "get_plant_overview",
                    "arguments": "{}",
                },
            }
        ],
    )

    # Round 2: Model uses tool result to generate answer
    round2_resp = AIChatResponse(
        content="Kondisi plant Bio-CNG Kampar saat ini beroperasi dengan normal.",
        model="qwen3:8b",
        provider="dmr",
        latency_ms=120.0,
        finish_reason="stop",
        tool_calls=None,
    )

    mock_provider.chat.side_effect = [round1_resp, round2_resp]
    mock_service.provider = mock_provider

    agent = NexaAgent(ai_service=mock_service)
    user = User(id=uuid.uuid4(), username="op", email="op@example.com", name="Operator")

    res = await agent.run(message="Bagaimana kondisi plant?", db=db_session, user=user)

    assert mock_provider.chat.call_count == 2
    assert len(res.tool_invocations) == 1
    assert res.tool_invocations[0].tool_name == "get_plant_overview"
    assert "Kondisi plant Bio-CNG Kampar" in res.content


# ==========================================
# 3. Agent API Endpoint Tests
# ==========================================

def test_agent_chat_unauthenticated(client):
    response = client.post("/ai/agent/chat", json={"message": "Kondisi plant?"})
    assert response.status_code == 401


def test_agent_chat_invalid_project(client, auth_headers):
    fake_uuid = str(uuid.uuid4())
    response = client.post(
        "/ai/agent/chat",
        headers=auth_headers,
        json={"message": "Kondisi plant?", "project_id": fake_uuid},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "PROJECT_NOT_FOUND"


def test_agent_chat_authenticated_success(client, db_session, auth_headers):
    proj = Project(id=uuid.uuid4(), name="Plant Test", location="Test Location")
    db_session.add(proj)
    db_session.commit()

    with patch("app.services.ai.agent.nexa_agent.run", new_callable=AsyncMock) as mock_agent_run:
        from app.schemas.ai import AgentChatResponse, ToolInvocation
        mock_agent_run.return_value = AgentChatResponse(
            content="Semua sistem berjalan lancar.",
            model="qwen3:8b",
            provider="dmr",
            latency_ms=250.0,
            tool_invocations=[
                ToolInvocation(
                    tool_name="get_plant_overview",
                    arguments={},
                    result={"projects_count": 1},
                )
            ],
        )

        response = client.post(
            "/ai/agent/chat",
            headers=auth_headers,
            json={"message": "Cek plant status", "project_id": str(proj.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Semua sistem berjalan lancar."
        assert len(data["tool_invocations"]) == 1
        assert data["tool_invocations"][0]["tool_name"] == "get_plant_overview"
