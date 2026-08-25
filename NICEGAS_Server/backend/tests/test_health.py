import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

@patch("app.api.health.check_db_connection")
def test_health_check_db_connected(mock_check_db_connection):
    # Arrange
    mock_check_db_connection.return_value = True

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "nicegas-api",
        "database": "connected"
    }

@patch("app.api.health.check_db_connection")
def test_health_check_db_disconnected(mock_check_db_connection):
    # Arrange
    mock_check_db_connection.return_value = False

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "service": "nicegas-api",
        "database": "disconnected"
    }
