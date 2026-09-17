import hashlib
import math
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.project import Project
from app.models.device import Device
from app.models.telemetry import Telemetry
from app.models.alert import Alert
from app.models.user import User
from app.core.config import settings
from app.core.security import hash_password

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def generate_uuid4(key: str) -> uuid.UUID:
    """Generates a deterministic UUID version 4 based on a seed key string.
    
    This ensures both determinism across seed executions and full compatibility
    with Pydantic UUID4 schema validation.
    """
    hash_bytes = bytearray(hashlib.sha256(f"nicegas.seed.{key}".encode("utf-8")).digest()[:16])
    # Set version to 4 (0100)
    hash_bytes[6] = (hash_bytes[6] & 0x0f) | 0x40
    # Set variant to RFC 4122 (10)
    hash_bytes[8] = (hash_bytes[8] & 0x3f) | 0x80
    return uuid.UUID(bytes=bytes(hash_bytes))

def seed_data():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        print(f"[{now.isoformat()}] Starting deterministic seed for NICEGAS development environment...")

        # -------------------------------------------------------------------------
        # 1. PROJECTS (At least 2 realistic Bio-CNG plants)
        # -------------------------------------------------------------------------
        projects_data = [
            {
                "id": generate_uuid4("project:plant-alpha"),
                "name": "Bio-CNG Plant New",
                "location": "Kampar, Riau, Sumatra",
                "created_at": now - timedelta(days=90),
                "updated_at": now - timedelta(minutes=5),
            },
            {
                "id": generate_uuid4("project:plant-beta"),
                "name": "Bio-CNG Plant Beta",
                "location": "Lampung Selatan, Lampung",
                "created_at": now - timedelta(days=60),
                "updated_at": now - timedelta(minutes=15),
            }
        ]

        seeded_project_ids = []
        for p_data in projects_data:
            seeded_project_ids.append(p_data["id"])
            existing_project = db.query(Project).filter_by(id=p_data["id"]).first()
            if existing_project:
                existing_project.name = p_data["name"]
                existing_project.location = p_data["location"]
                existing_project.updated_at = p_data["updated_at"]
            else:
                project = Project(
                    id=p_data["id"],
                    name=p_data["name"],
                    location=p_data["location"],
                    created_at=p_data["created_at"],
                    updated_at=p_data["updated_at"]
                )
                db.add(project)

        db.flush()

        # -------------------------------------------------------------------------
        # 2. DEVICES (Multiple per project, machine-readable MQTT names)
        # -------------------------------------------------------------------------
        devices_data = [
            # Plant Alpha devices (Primary complete plant)
            {
                "id": generate_uuid4("device:alpha:digester-01"),
                "project_id": generate_uuid4("project:plant-alpha"),
                "name": "DIGESTER-01",
                "type": "biodigester",
                "status": "online",
                "firmware": "v1.2.4",
                "last_seen": now - timedelta(minutes=1),
                "created_at": now - timedelta(days=90),
                "updated_at": now - timedelta(minutes=1),
            },
            {
                "id": generate_uuid4("device:alpha:purify-01"),
                "project_id": generate_uuid4("project:plant-alpha"),
                "name": "PURIFY-01",
                "type": "purifikasi",
                "status": "online",
                "firmware": "v1.2.4",
                "last_seen": now - timedelta(minutes=2),
                "created_at": now - timedelta(days=90),
                "updated_at": now - timedelta(minutes=2),
            },
            {
                "id": generate_uuid4("device:alpha:comp-01"),
                "project_id": generate_uuid4("project:plant-alpha"),
                "name": "COMP-01",
                "type": "kompresi",
                "status": "online",
                "firmware": "v1.2.1",
                "last_seen": now - timedelta(minutes=5),
                "created_at": now - timedelta(days=90),
                "updated_at": now - timedelta(minutes=5),
            },
            {
                "id": generate_uuid4("device:alpha:storage-01"),
                "project_id": generate_uuid4("project:plant-alpha"),
                "name": "STORAGE-01",
                "type": "storage",
                "status": "offline",
                "firmware": "v1.1.0",
                "last_seen": now - timedelta(hours=3),
                "created_at": now - timedelta(days=90),
                "updated_at": now - timedelta(hours=3),
            },
            {
                "id": generate_uuid4("device:alpha:edge-ai-01"),
                "project_id": generate_uuid4("project:plant-alpha"),
                "name": "EDGE-AI-01",
                "type": "edge_ai",
                "status": "online",
                "firmware": "v1.0.0",
                "last_seen": now - timedelta(minutes=1),
                "created_at": now - timedelta(days=90),
                "updated_at": now - timedelta(minutes=1),
            },

            # Plant Beta devices (Secondary facility)
            {
                "id": generate_uuid4("device:beta:digester-02"),
                "project_id": generate_uuid4("project:plant-beta"),
                "name": "DIGESTER-02",
                "type": "biodigester",
                "status": "online",
                "firmware": "v1.2.4",
                "last_seen": now - timedelta(minutes=2),
                "created_at": now - timedelta(days=60),
                "updated_at": now - timedelta(minutes=2),
            },
            {
                "id": generate_uuid4("device:beta:purify-02"),
                "project_id": generate_uuid4("project:plant-beta"),
                "name": "PURIFY-02",
                "type": "purifikasi",
                "status": "online",
                "firmware": "v1.2.4",
                "last_seen": now - timedelta(minutes=3),
                "created_at": now - timedelta(days=60),
                "updated_at": now - timedelta(minutes=3),
            },
            {
                "id": generate_uuid4("device:beta:comp-02"),
                "project_id": generate_uuid4("project:plant-beta"),
                "name": "COMP-02",
                "type": "kompresi",
                "status": "offline",
                "firmware": "v1.2.0",
                "last_seen": now - timedelta(hours=6),
                "created_at": now - timedelta(days=60),
                "updated_at": now - timedelta(hours=6),
            }
        ]

        seeded_device_ids = []
        for d_data in devices_data:
            seeded_device_ids.append(d_data["id"])
            existing_device = db.query(Device).filter_by(id=d_data["id"]).first()
            if existing_device:
                existing_device.project_id = d_data["project_id"]
                existing_device.name = d_data["name"]
                existing_device.type = d_data["type"]
                existing_device.status = d_data["status"]
                existing_device.firmware = d_data["firmware"]
                existing_device.last_seen = d_data["last_seen"]
                existing_device.updated_at = d_data["updated_at"]
            else:
                device = Device(
                    id=d_data["id"],
                    project_id=d_data["project_id"],
                    name=d_data["name"],
                    type=d_data["type"],
                    status=d_data["status"],
                    firmware=d_data["firmware"],
                    last_seen=d_data["last_seen"],
                    created_at=d_data["created_at"],
                    updated_at=d_data["updated_at"]
                )
                db.add(device)

        db.flush()

        # -------------------------------------------------------------------------
        # 3. TELEMETRY (Idempotent: clean old seed records for these devices, reinsert)
        # -------------------------------------------------------------------------
        db.query(Telemetry).filter(Telemetry.device_id.in_(seeded_device_ids)).delete(synchronize_session=False)

        telemetry_records = []

        # 3a. DIGESTER-01 (Plant Alpha) - 36 historical points over the last 18 hours (every 30 mins)
        # Primary device for main dashboard charts (pressure, methane, temperature, gas_flow)
        dev_alpha_digester = generate_uuid4("device:alpha:digester-01")
        for i in range(36):
            t_time = now - timedelta(minutes=(35 - i) * 30)
            temp_val = round(37.6 + 0.6 * math.sin(i * 0.35), 2)
            pressure_val = round(1.24 + 0.14 * math.cos(i * 0.28), 2)
            methane_val = round(62.8 + 2.2 * math.sin(i * 0.30), 1)
            gas_flow_val = round(23.8 + 2.4 * math.cos(i * 0.32), 1)
            ph_val = round(7.22 + 0.08 * math.sin(i * 0.25), 2)

            telemetry_records.append(
                Telemetry(
                    id=generate_uuid4(f"telemetry:alpha:digester-01:{i}"),
                    device_id=dev_alpha_digester,
                    timestamp=t_time,
                    component="biodigester",
                    metrics={
                        "temperature": {"v": temp_val, "u": "°C"},
                        "pressure": {"v": pressure_val, "u": "bar"},
                        "methane": {"v": methane_val, "u": "%"},
                        "gas_flow": {"v": gas_flow_val, "u": "Nm³/h"},
                        "ph": {"v": ph_val, "u": "pH"}
                    },
                    status="optimal"
                )
            )

        # 3b. PURIFY-01 (Plant Alpha) - 24 points over last 12 hours (every 30 mins)
        dev_alpha_purify = generate_uuid4("device:alpha:purify-01")
        for i in range(24):
            t_time = now - timedelta(minutes=(23 - i) * 30)
            methane_purified = round(96.2 + 0.8 * math.sin(i * 0.3), 1)
            co2_val = round(2.8 + 0.4 * math.cos(i * 0.3), 1)
            h2s_val = round(5.2 + 1.8 * math.sin(i * 0.4), 1)
            humidity_val = round(12.5 + 2.0 * math.cos(i * 0.25), 1)
            flow_rate_val = round(22.4 + 1.6 * math.sin(i * 0.3), 1)

            telemetry_records.append(
                Telemetry(
                    id=generate_uuid4(f"telemetry:alpha:purify-01:{i}"),
                    device_id=dev_alpha_purify,
                    timestamp=t_time,
                    component="purifikasi",
                    metrics={
                        "methane": {"v": methane_purified, "u": "%"},
                        "co2": {"v": co2_val, "u": "%"},
                        "h2s": {"v": h2s_val, "u": "ppm"},
                        "humidity": {"v": humidity_val, "u": "ppm"},
                        "flow_rate": {"v": flow_rate_val, "u": "Nm³/h"}
                    },
                    status="optimal"
                )
            )

        # 3c. COMP-01 (Plant Alpha) - 24 points over last 12 hours (every 30 mins)
        dev_alpha_comp = generate_uuid4("device:alpha:comp-01")
        for i in range(24):
            t_time = now - timedelta(minutes=(23 - i) * 30)
            inlet_p = round(1.18 + 0.05 * math.sin(i * 0.3), 2)
            discharge_p = round(205.0 + 5.5 * math.cos(i * 0.2), 1)
            motor_t = round(64.2 + 3.2 * math.sin(i * 0.35), 1)
            vibration_val = round(1.75 + 0.25 * math.cos(i * 0.4), 2)

            telemetry_records.append(
                Telemetry(
                    id=generate_uuid4(f"telemetry:alpha:comp-01:{i}"),
                    device_id=dev_alpha_comp,
                    timestamp=t_time,
                    component="kompresi",
                    metrics={
                        "inlet_pressure": {"v": inlet_p, "u": "bar"},
                        "discharge_pressure": {"v": discharge_p, "u": "bar"},
                        "motor_temperature": {"v": motor_t, "u": "°C"},
                        "vibration": {"v": vibration_val, "u": "mm/s"}
                    },
                    status="optimal"
                )
            )

        # 3d. STORAGE-01 (Plant Alpha) - 10 points earlier in day
        dev_alpha_storage = generate_uuid4("device:alpha:storage-01")
        for i in range(10):
            t_time = now - timedelta(minutes=(9 - i) * 30 + 180)
            storage_p = round(194.0 - i * 0.2, 1)
            tank_lvl = round(84.0 - i * 0.3, 1)
            amb_t = round(29.0 + 1.5 * math.sin(i * 0.4), 1)

            telemetry_records.append(
                Telemetry(
                    id=generate_uuid4(f"telemetry:alpha:storage-01:{i}"),
                    device_id=dev_alpha_storage,
                    timestamp=t_time,
                    component="storage",
                    metrics={
                        "storage_pressure": {"v": storage_p, "u": "bar"},
                        "tank_level": {"v": tank_lvl, "u": "%"},
                        "ambient_temperature": {"v": amb_t, "u": "°C"}
                    },
                    status="offline"
                )
            )

        # 3e. DIGESTER-02 (Plant Beta) - 36 historical points over last 18 hours
        dev_beta_digester = generate_uuid4("device:beta:digester-02")
        for i in range(36):
            t_time = now - timedelta(minutes=(35 - i) * 30)
            temp_val = round(38.1 + 0.4 * math.sin(i * 0.30), 2)
            pressure_val = round(1.27 + 0.09 * math.cos(i * 0.25), 2)
            methane_val = round(59.6 + 1.6 * math.sin(i * 0.35), 1)
            gas_flow_val = round(20.8 + 1.8 * math.cos(i * 0.30), 1)
            ph_val = round(7.18 + 0.06 * math.sin(i * 0.20), 2)

            telemetry_records.append(
                Telemetry(
                    id=generate_uuid4(f"telemetry:beta:digester-02:{i}"),
                    device_id=dev_beta_digester,
                    timestamp=t_time,
                    component="biodigester",
                    metrics={
                        "temperature": {"v": temp_val, "u": "°C"},
                        "pressure": {"v": pressure_val, "u": "bar"},
                        "methane": {"v": methane_val, "u": "%"},
                        "gas_flow": {"v": gas_flow_val, "u": "Nm³/h"},
                        "ph": {"v": ph_val, "u": "pH"}
                    },
                    status="optimal"
                )
            )

        # 3f. PURIFY-02 (Plant Beta) - 20 points
        dev_beta_purify = generate_uuid4("device:beta:purify-02")
        for i in range(20):
            t_time = now - timedelta(minutes=(19 - i) * 30)
            methane_purified = round(95.4 + 0.7 * math.sin(i * 0.3), 1)
            co2_val = round(3.4 + 0.4 * math.cos(i * 0.3), 1)
            h2s_val = round(6.5 + 1.2 * math.sin(i * 0.4), 1)
            humidity_val = round(14.0 + 1.8 * math.cos(i * 0.25), 1)

            telemetry_records.append(
                Telemetry(
                    id=generate_uuid4(f"telemetry:beta:purify-02:{i}"),
                    device_id=dev_beta_purify,
                    timestamp=t_time,
                    component="purifikasi",
                    metrics={
                        "methane": {"v": methane_purified, "u": "%"},
                        "co2": {"v": co2_val, "u": "%"},
                        "h2s": {"v": h2s_val, "u": "ppm"},
                        "humidity": {"v": humidity_val, "u": "ppm"}
                    },
                    status="optimal"
                )
            )

        # 3g. COMP-02 (Plant Beta) - 8 points
        dev_beta_comp = generate_uuid4("device:beta:comp-02")
        for i in range(8):
            t_time = now - timedelta(minutes=(7 - i) * 30 + 360)
            telemetry_records.append(
                Telemetry(
                    id=generate_uuid4(f"telemetry:beta:comp-02:{i}"),
                    device_id=dev_beta_comp,
                    timestamp=t_time,
                    component="kompresi",
                    metrics={
                        "inlet_pressure": {"v": 1.12, "u": "bar"},
                        "discharge_pressure": {"v": 178.5, "u": "bar"}
                    },
                    status="offline"
                )
            )

        db.add_all(telemetry_records)
        db.flush()

        # -------------------------------------------------------------------------
        # 4. ALERTS (ACTIVE, RESOLVED, WARNING, CRITICAL, INFO)
        # -------------------------------------------------------------------------
        db.query(Alert).filter(Alert.device_id.in_(seeded_device_ids)).delete(synchronize_session=False)

        alerts_data = [
            # Plant Alpha Alerts
            {
                "id": generate_uuid4("alert:alpha:digester-01:1"),
                "device_id": generate_uuid4("device:alpha:digester-01"),
                "component": "biodigester",
                "severity": "WARNING",
                "status": "ACTIVE",
                "message": "Digester pressure approaching upper operational boundary (1.42 bar)",
                "timestamp": now - timedelta(minutes=45)
            },
            {
                "id": generate_uuid4("alert:alpha:digester-01:2"),
                "device_id": generate_uuid4("device:alpha:digester-01"),
                "component": "biodigester",
                "severity": "WARNING",
                "status": "RESOLVED",
                "message": "Slurry temperature drop detected (36.2°C) - heating jacket restored nominal range",
                "timestamp": now - timedelta(hours=6)
            },
            {
                "id": generate_uuid4("alert:alpha:purify-01:1"),
                "device_id": generate_uuid4("device:alpha:purify-01"),
                "component": "purifikasi",
                "severity": "CRITICAL",
                "status": "ACTIVE",
                "message": "H2S scrubber media saturation reached (19.8 ppm exceeds safety threshold)",
                "timestamp": now - timedelta(minutes=20)
            },
            {
                "id": generate_uuid4("alert:alpha:purify-01:2"),
                "device_id": generate_uuid4("device:alpha:purify-01"),
                "component": "purifikasi",
                "severity": "CRITICAL",
                "status": "RESOLVED",
                "message": "Moisture separator high liquid level - automated drain cycle completed",
                "timestamp": now - timedelta(hours=14)
            },
            {
                "id": generate_uuid4("alert:alpha:storage-01:1"),
                "device_id": generate_uuid4("device:alpha:storage-01"),
                "component": "storage",
                "severity": "WARNING",
                "status": "ACTIVE",
                "message": "Telemetry heartbeat lost: Buffer Storage 01 communication timed out",
                "timestamp": now - timedelta(hours=3)
            },
            {
                "id": generate_uuid4("alert:alpha:comp-01:1"),
                "device_id": generate_uuid4("device:alpha:comp-01"),
                "component": "kompresi",
                "severity": "WARNING",
                "status": "RESOLVED",
                "message": "Compressor lubrication oil temperature elevated (71.5°C) - cooling fan engaged",
                "timestamp": now - timedelta(hours=10)
            },
            {
                "id": generate_uuid4("alert:alpha:comp-01:2"),
                "device_id": generate_uuid4("device:alpha:comp-01"),
                "component": "kompresi",
                "severity": "INFO",
                "status": "RESOLVED",
                "message": "Routine 500-hour preventive maintenance inspection completed successfully",
                "timestamp": now - timedelta(hours=22)
            },

            # Plant Beta Alerts
            {
                "id": generate_uuid4("alert:beta:digester-02:1"),
                "device_id": generate_uuid4("device:beta:digester-02"),
                "component": "biodigester",
                "severity": "WARNING",
                "status": "ACTIVE",
                "message": "Feedstock substrate pH lower than optimal (6.85 pH) - buffer dosing scheduled",
                "timestamp": now - timedelta(hours=1)
            },
            {
                "id": generate_uuid4("alert:beta:digester-02:2"),
                "device_id": generate_uuid4("device:beta:digester-02"),
                "component": "biodigester",
                "severity": "CRITICAL",
                "status": "RESOLVED",
                "message": "Gas overpressure safety relief valve engaged briefly - pressure stabilized",
                "timestamp": now - timedelta(hours=18)
            },
            {
                "id": generate_uuid4("alert:beta:comp-02:1"),
                "device_id": generate_uuid4("device:beta:comp-02"),
                "component": "kompresi",
                "severity": "CRITICAL",
                "status": "ACTIVE",
                "message": "Compressor motor excessive vibration detected (4.8 mm/s) - safety interlock triggered",
                "timestamp": now - timedelta(hours=6)
            }
        ]

        alert_records = [Alert(**a) for a in alerts_data]
        db.add_all(alert_records)

        # -------------------------------------------------------------------------
        # 5. USERS (Deterministic development accounts with bcrypt hashed passwords)
        # -------------------------------------------------------------------------
        users_data = [
            {
                "id": generate_uuid4("user:admin"),
                "username": "admin",
                "email": "admin@nicegas.local",
                "name": "Administrator",
                "role": "admin",
                "password_plain": "admin123",
                "is_active": True,
            },
            {
                "id": generate_uuid4("user:operator1"),
                "username": "operator1",
                "email": "operator1@nicegas.local",
                "name": "Operator Lapangan",
                "role": "operator",
                "password_plain": "niceg4s",
                "is_active": True,
            },
            {
                "id": generate_uuid4("user:operator_real"),
                "username": "operator_real",
                "email": "operator@nicegas.local",
                "name": "Budi Operator",
                "role": "operator",
                "password_plain": "secret123",
                "is_active": True,
            }
        ]

        seeded_user_count = 0
        for u_data in users_data:
            existing_user = db.query(User).filter(
                (User.id == u_data["id"]) | 
                (User.username == u_data["username"]) | 
                (User.email == u_data["email"])
            ).first()

            if existing_user:
                existing_user.username = u_data["username"]
                existing_user.email = u_data["email"]
                existing_user.name = u_data["name"]
                existing_user.role = u_data["role"]
                existing_user.hashed_password = hash_password(u_data["password_plain"])
                existing_user.is_active = u_data["is_active"]
                existing_user.updated_at = now
            else:
                user = User(
                    id=u_data["id"],
                    username=u_data["username"],
                    email=u_data["email"],
                    name=u_data["name"],
                    role=u_data["role"],
                    hashed_password=hash_password(u_data["password_plain"]),
                    is_active=u_data["is_active"],
                    created_at=now - timedelta(days=90),
                    updated_at=now
                )
                db.add(user)
            seeded_user_count += 1

        db.commit()

        print(f"Deterministic seed completed successfully:")
        print(f"  - Projects created/updated : {len(projects_data)}")
        print(f"  - Devices created/updated  : {len(devices_data)}")
        print(f"  - Telemetry points seeded  : {len(telemetry_records)}")
        print(f"  - Alerts seeded            : {len(alerts_data)}")
        print(f"  - Users seeded             : {seeded_user_count}")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
