from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.repositories import device as device_repo
from app.schemas.ai import (
    AIChatRequest,
    AIChatResponse,
    AIHealthResponse,
    TelemetryAnalysisRequest,
    TelemetryAnalysisResponse,
)
from app.services.ai.service import ai_service
from app.core.exceptions import (
    AIProviderUnavailableException,
    AIRequestTimeoutException,
    AIResponseInvalidException,
    AIException,
)

router = APIRouter()


@router.get("/health", response_model=AIHealthResponse)
async def ai_health(
    current_user: User = Depends(get_current_user),
):
    """Health check for AI provider and model readiness.
    
    Requires JWT authentication. Does not expose credentials or internal paths.
    """
    try:
        health_status = await ai_service.health()
        return AIHealthResponse(
            provider=health_status.provider,
            status=health_status.status,
            model=health_status.model,
            latency_ms=health_status.latency_ms,
        )
    except Exception as exc:
        return AIHealthResponse(
            provider="unknown",
            status="unavailable",
            model="unknown",
            latency_ms=None,
        )


@router.post("/chat", response_model=AIChatResponse)
async def ai_chat(
    request: AIChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Generic AI chat endpoint via the provider abstraction layer.
    
    Protected by JWT authentication.
    """
    try:
        response = await ai_service.chat(
            message=request.message,
            system=request.system,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        return response
    except AIRequestTimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"code": "AI_REQUEST_TIMEOUT", "message": str(exc)},
        )
    except AIProviderUnavailableException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "AI_PROVIDER_UNAVAILABLE", "message": str(exc)},
        )
    except AIResponseInvalidException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "AI_RESPONSE_INVALID", "message": str(exc)},
        )
    except AIException as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": exc.code, "message": exc.message},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "AI_INTERNAL_ERROR", "message": "An unexpected error occurred in AI service"},
        )


@router.post("/analyze-telemetry", response_model=TelemetryAnalysisResponse)
async def analyze_telemetry(
    request: TelemetryAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Domain AI endpoint: Analyzes Bio-CNG telemetry and returns structured advisory results.
    
    Protected by JWT authentication. Advisory only.
    """
    device_name = None
    if request.device_id:
        device = device_repo.get(db, id=request.device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "DEVICE_NOT_FOUND", "message": f"Device {request.device_id} not found"},
            )
        if request.project_id and device.project_id != request.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_DEVICE_PROJECT_RELATION",
                    "message": "Device does not belong to specified project",
                },
            )
        device_name = device.name

    try:
        response = await ai_service.analyze_telemetry(
            telemetry=request.telemetry,
            component=request.component,
            device_name=device_name,
        )
        return response
    except AIRequestTimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"code": "AI_REQUEST_TIMEOUT", "message": str(exc)},
        )
    except AIProviderUnavailableException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "AI_PROVIDER_UNAVAILABLE", "message": str(exc)},
        )
    except AIResponseInvalidException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "AI_RESPONSE_INVALID", "message": str(exc)},
        )
    except AIException as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": exc.code, "message": exc.message},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "AI_INTERNAL_ERROR", "message": "An unexpected error occurred in AI service"},
        )
