import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from app.services.mqtt import MQTTService
from app.models.project import Project
from app.models.device import Device
from app.models.telemetry import Telemetry
from app.models.alert import Alert

@pytest.fixture
def mqtt_service():
    service = MQTTService()
    service.client = MagicMock()
    return service

@pytest.mark.asyncio
async def test_on_message_telemetry(mqtt_service, db_session):
    # Setup mock data
    project = Project(name="plant-alpha")
    db_session.add(project)
    db_session.flush()
    
    device = Device(project_id=project.id, name="esp32-001", type="sensor", status="offline")
    db_session.add(device)
    db_session.commit()
    device_id = device.id
    
    payload = {
        "timestamp": "2026-08-28T10:15:00Z",
        "metrics": {
            "temperature": {"v": 38.5, "u": "C"},
            "pressure": {"v": 1.21, "u": "bar"}
        },
        "status": "nominal"
    }
    
    topic = "nicegas/plant-alpha/esp32-001/telemetry/digester"
    
    db_session.__enter__ = MagicMock(return_value=db_session)
    db_session.__exit__ = MagicMock(return_value=None)
    db_session.close = MagicMock()
    
    with patch("app.services.mqtt.SessionLocal", return_value=db_session):
        await mqtt_service.on_message(None, topic, json.dumps(payload).encode(), 0, None)
    
    # Verify persistence
    telemetry = db_session.query(Telemetry).filter_by(device_id=device_id).first()
    assert telemetry is not None
    assert telemetry.metrics["temperature"]["v"] == 38.5
    assert telemetry.component == "digester"
    
    # Verify device status update
    updated_device = db_session.query(Device).filter_by(id=device_id).first()
    assert updated_device.status == "online"
    assert updated_device.last_seen is not None

@pytest.mark.asyncio
async def test_on_message_status(mqtt_service, db_session):
    # Setup mock data
    project = Project(name="plant-beta")
    db_session.add(project)
    db_session.flush()
    
    device = Device(project_id=project.id, name="esp32-002", type="sensor", status="online")
    db_session.add(device)
    db_session.commit()
    device_id = device.id
    
    payload = {"status": "offline"}
    topic = "nicegas/plant-beta/esp32-002/status/connection"
    
    db_session.__enter__ = MagicMock(return_value=db_session)
    db_session.__exit__ = MagicMock(return_value=None)
    db_session.close = MagicMock()
    
    with patch("app.services.mqtt.SessionLocal", return_value=db_session):
        await mqtt_service.on_message(None, topic, json.dumps(payload).encode(), 1, None)
    
    updated_device = db_session.query(Device).filter_by(id=device_id).first()
    assert updated_device.status == "offline"

@pytest.mark.asyncio
async def test_on_message_event(mqtt_service, db_session):
    # Setup mock data
    project = Project(name="plant-gamma")
    db_session.add(project)
    db_session.flush()
    
    device = Device(project_id=project.id, name="esp32-003", type="sensor", status="online")
    db_session.add(device)
    db_session.commit()
    device_id = device.id
    
    payload = {
        "severity": "high",
        "message": "Critical pressure leak",
        "timestamp": "2026-08-28T10:20:00Z"
    }
    topic = "nicegas/plant-gamma/esp32-003/event/leakage"
    
    db_session.__enter__ = MagicMock(return_value=db_session)
    db_session.__exit__ = MagicMock(return_value=None)
    db_session.close = MagicMock()
    
    with patch("app.services.mqtt.SessionLocal", return_value=db_session):
        await mqtt_service.on_message(None, topic, json.dumps(payload).encode(), 1, None)
    
    # Verify alert persistence
    alert = db_session.query(Alert).filter_by(device_id=device_id).first()
    assert alert is not None
    assert alert.severity == "high"
    assert alert.message == "Critical pressure leak"

@pytest.mark.asyncio
async def test_on_message_duplicate(mqtt_service, db_session):
    project = Project(name="plant-delta")
    db_session.add(project)
    db_session.flush()
    
    device = Device(project_id=project.id, name="esp32-004", type="sensor")
    db_session.add(device)
    db_session.commit()
    device_id = device.id
    
    payload = {
        "timestamp": "2026-08-28T10:30:00Z",
        "metrics": {"v": 1},
        "status": "ok"
    }
    topic = "nicegas/plant-delta/esp32-004/telemetry/test"
    
    db_session.__enter__ = MagicMock(return_value=db_session)
    db_session.__exit__ = MagicMock(return_value=None)
    db_session.close = MagicMock()
    
    with patch("app.services.mqtt.SessionLocal", return_value=db_session):
        # First delivery
        await mqtt_service.on_message(None, topic, json.dumps(payload).encode(), 1, None)
        # Second delivery (duplicate)
        await mqtt_service.on_message(None, topic, json.dumps(payload).encode(), 1, None)
        
    # Should only have one telemetry record
    count = db_session.query(Telemetry).filter_by(device_id=device_id).count()
    assert count == 1

@pytest.mark.asyncio
async def test_on_message_invalid_payload(mqtt_service, db_session):
    topic = "nicegas/a/b/telemetry/c"
    # Invalid JSON
    await mqtt_service.on_message(None, topic, b"not-json", 0, None)
    # Missing fields
    await mqtt_service.on_message(None, topic, b"{}", 0, None)
    # Malformed topic
    await mqtt_service.on_message(None, "invalid/topic", b"{}", 0, None)
    # No crash expected
