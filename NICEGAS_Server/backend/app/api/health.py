from fastapi import APIRouter, Response, status
from app.db.database import check_db_connection

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
def health_check(response: Response):
    """
    Health check endpoint.
    Verifies that the API is running and that PostgreSQL is accessible.
    """
    is_db_connected = check_db_connection()
    
    if not is_db_connected:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "error",
            "service": "nicegas-api",
            "database": "disconnected"
        }
    
    return {
        "status": "ok",
        "service": "nicegas-api",
        "database": "connected"
    }
