import uuid
from datetime import datetime, timezone, timedelta
from app.models.project import Project
from app.models.device import Device
from app.models.telemetry import Telemetry

def seed_test_data(db_session):
    project_id = uuid.uuid4()
    project = Project(id=project_id, name="Test Project")
    db_session.add(project)
    
    device_id = uuid.uuid4()
    device = Device(id=device_id, project_id=project_id, name="Test Device", type="sensor")
    db_session.add(device)
    
    db_session.commit()
    return project_id, device_id

def test_get_projects_unauthenticated(client):
    response = client.get("/projects")
    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["code"] == "UNAUTHORIZED"

def test_get_projects(client, db_session, auth_headers):
    seed_test_data(db_session)
    response = client.get("/projects", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert len(data["data"]) >= 1

def test_get_devices(client, db_session, auth_headers):
    project_id, _ = seed_test_data(db_session)
    response = client.get(f"/devices?project_id={project_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 1

def test_get_device(client, db_session, auth_headers):
    _, device_id = seed_test_data(db_session)
    response = client.get(f"/devices/{device_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(device_id)

def test_get_device_not_found(client, auth_headers):
    response = client.get(f"/devices/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"]["code"] == "DEVICE_NOT_FOUND"

def test_get_telemetry_missing_filters(client, auth_headers):
    response = client.get("/telemetry", headers=auth_headers)
    assert response.status_code == 422 # FastAPI validation error for missing query params

def test_get_telemetry_invalid_time_range(client, db_session, auth_headers):
    _, device_id = seed_test_data(db_session)
    now = datetime.now(timezone.utc)
    start_time = now.isoformat()
    end_time = (now - timedelta(hours=1)).isoformat()
    
    response = client.get("/telemetry", params={
        "device_id": str(device_id),
        "start_time": start_time,
        "end_time": end_time
    }, headers=auth_headers)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["code"] == "INVALID_TIME_RANGE"

def test_get_telemetry_success(client, db_session, auth_headers):
    _, device_id = seed_test_data(db_session)
    now = datetime.now(timezone.utc)
    t = Telemetry(device_id=device_id, timestamp=now, metrics={"temp": 1})
    db_session.add(t)
    db_session.commit()
    
    start_time = (now - timedelta(hours=1)).isoformat()
    end_time = (now + timedelta(hours=1)).isoformat()
    
    response = client.get("/telemetry", params={
        "device_id": str(device_id),
        "start_time": start_time,
        "end_time": end_time
    }, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 1

def test_get_alerts(client, db_session, auth_headers):
    _, device_id = seed_test_data(db_session)
    response = client.get(f"/alerts?device_id={device_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
