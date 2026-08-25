import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.project import Project
from app.models.device import Device
from app.models.telemetry import Telemetry
from app.models.alert import Alert
from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_data():
    db = SessionLocal()
    try:
        # Check if project already exists
        existing_project = db.query(Project).first()
        if existing_project:
            print("LOCAL DEVELOPMENT DATA already exists. Skipping seed.")
            return

        print("Seeding LOCAL DEVELOPMENT DATA...")
        
        # Create a project
        project_id = uuid.uuid4()
        project = Project(
            id=project_id,
            name="Demo NICEGAS Project",
            location="Test Facility A"
        )
        db.add(project)
        db.flush() # flush to get the id if generated, though we set it
        
        # Create devices
        device1_id = uuid.uuid4()
        device1 = Device(
            id=device1_id,
            project_id=project_id,
            name="ESP32 Temp Sensor 1",
            type="temperature_sensor",
            status="online",
            firmware="v1.0.0",
            last_seen=datetime.now(timezone.utc)
        )
        db.add(device1)
        
        device2_id = uuid.uuid4()
        device2 = Device(
            id=device2_id,
            project_id=project_id,
            name="ESP32 Pressure Sensor 1",
            type="pressure_sensor",
            status="offline",
            firmware="v1.0.0",
            last_seen=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        db.add(device2)
        db.flush()

        # Create telemetry
        now = datetime.now(timezone.utc)
        for i in range(5):
            t_time = now - timedelta(minutes=(5-i)*10)
            t = Telemetry(
                device_id=device1_id,
                timestamp=t_time,
                component="sensor_module",
                metrics={"temperature": {"v": 38.5 + i*0.2, "u": "C"}},
                status="nominal"
            )
            db.add(t)

        # Create alerts
        alert1 = Alert(
            device_id=device2_id,
            component="connection",
            severity="high",
            status="active",
            message="Device went offline unexpectedly",
            timestamp=now - timedelta(hours=2)
        )
        db.add(alert1)

        db.commit()
        print("LOCAL DEVELOPMENT DATA seeded successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
