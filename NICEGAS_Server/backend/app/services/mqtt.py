import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from gmqtt import Client as MQTTClient
from gmqtt.mqtt.constants import MQTTv311

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.telemetry import Telemetry
from app.models.device import Device
from app.models.project import Project
from app.models.alert import Alert

logger = logging.getLogger(__name__)

class MQTTService:
    def __init__(self):
        self.client: MQTTClient = None
        self._running = False
        self._reconnect_interval = settings.MQTT_RECONNECT_DELAY

    async def start(self):
        """Initializes and connects the MQTT client."""
        if self._running:
            return

        self.client = MQTTClient(settings.MQTT_CLIENT_ID)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_subscribe = self.on_subscribe

        if settings.MQTT_USER and settings.MQTT_PASSWORD:
            self.client.set_auth_credentials(settings.MQTT_USER, settings.MQTT_PASSWORD)

        try:
            await self.client.connect(
                settings.MQTT_HOST,
                settings.MQTT_PORT,
                keepalive=settings.MQTT_KEEPALIVE,
                version=MQTTv311
            )
            self._running = True
            logger.info(f"MQTT Service started. Connected to {settings.MQTT_HOST}:{settings.MQTT_PORT}")
        except Exception as e:
            logger.error(f"Failed to start MQTT Service: {e}")
            # Reconnection is handled by gmqtt or our lifespan retry logic if needed
            self._running = False

    async def stop(self):
        """Gracefully disconnects the MQTT client."""
        if self.client:
            await self.client.disconnect()
        self._running = False
        logger.info("MQTT Service stopped.")

    def on_connect(self, client, flags, rc, properties):
        logger.info(f"Connected to MQTT Broker with result code {rc}")
        # Subscribe to approved topics: nicegas/{site_id}/{device_id}/{category}/{component}
        # Using wildcards to capture all sites and devices for telemetry, status, and events
        client.subscribe("nicegas/+/+/telemetry/+", qos=1)
        client.subscribe("nicegas/+/+/status/+", qos=1)
        client.subscribe("nicegas/+/+/event/+", qos=1)

    def on_subscribe(self, client, mid, qos, properties):
        logger.info(f"Subscribed to topics (mid={mid})")

    def on_disconnect(self, client, packet, exc=None):
        logger.warning(f"Disconnected from MQTT Broker. Exc: {exc}")
        self._running = False

    async def on_message(self, client, topic, payload, qos, properties):
        try:
            payload_str = payload.decode("utf-8")
            logger.info(f"Received message on {topic}: {payload_str}")

            # Parse topic: nicegas/{site_id}/{device_id}/{category}/{component}
            parts = topic.split('/')
            if len(parts) < 5:
                logger.warning(f"Malformed topic: {topic}")
                return

            site_id = parts[1]
            device_id_str = parts[2]
            category = parts[3]
            component = parts[4]

            data = json.loads(payload_str)

            if category == "telemetry":
                await self.handle_telemetry(site_id, device_id_str, component, data)
            elif category == "status":
                await self.handle_status(site_id, device_id_str, component, data)
            elif category == "event":
                await self.handle_event(site_id, device_id_str, component, data)
            else:
                logger.info(f"Ignored unknown category '{category}' on topic {topic}")

        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON payload on {topic}")
        except Exception as e:
            logger.error(f"Error processing MQTT message on {topic}: {e}", exc_info=True)

    async def handle_telemetry(self, site_id: str, device_id_str: str, component: str, data: Dict[str, Any]):
        """Validates and persists telemetry data."""
        timestamp_str = data.get("timestamp")
        metrics = data.get("metrics")

        if not timestamp_str or not isinstance(metrics, dict):
            logger.warning(f"Invalid telemetry payload structure on {site_id}/{device_id_str}")
            return

        try:
            # Handle 'Z' suffix for ISO format compatibility
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Invalid timestamp format: {timestamp_str}")
            return

        # Use to_thread to avoid blocking the event loop with synchronous DB calls
        await asyncio.to_thread(self._persist_telemetry, site_id, device_id_str, component, dt, metrics, data.get("status"))

    def _persist_telemetry(self, site_id: str, device_id_str: str, component: str, dt: datetime, metrics: dict, status: str):
        with SessionLocal() as db:
            try:
                # Find device by name and its project by name
                device = db.query(Device).join(Project).filter(
                    Project.name == site_id,
                    Device.name == device_id_str
                ).first()

                if not device:
                    logger.warning(f"Telemetry ignored: Device '{device_id_str}' at Site '{site_id}' not found in database.")
                    return

                # Deduplication: check if telemetry with same device, component and timestamp already exists
                existing = db.query(Telemetry).filter(
                    Telemetry.device_id == device.id,
                    Telemetry.timestamp == dt,
                    Telemetry.component == component
                ).first()

                if existing:
                    logger.info(f"Duplicate telemetry skipped for {device_id_str} at {dt}")
                    return

                telemetry = Telemetry(
                    device_id=device.id,
                    timestamp=dt,
                    component=component,
                    metrics=metrics,
                    status=status
                )
                db.add(telemetry)

                # Update device state
                device.last_seen = datetime.now(timezone.utc)
                if device.status != "online":
                    device.status = "online"

                db.commit()
                logger.info(f"Telemetry persisted: {site_id}/{device_id_str}/{component}")
            except Exception as e:
                db.rollback()
                logger.error(f"Database error while persisting telemetry: {e}")

    async def handle_status(self, site_id: str, device_id_str: str, component: str, data: Dict[str, Any]):
        """Handles device status updates (e.g., LWT)."""
        if component != "connection":
            return

        status = data.get("status")
        if status not in ["online", "offline"]:
            logger.warning(f"Invalid connection status received: {status}")
            return

        await asyncio.to_thread(self._update_device_status, site_id, device_id_str, status)

    def _update_device_status(self, site_id: str, device_id_str: str, status: str):
        with SessionLocal() as db:
            try:
                device = db.query(Device).join(Project).filter(
                    Project.name == site_id,
                    Device.name == device_id_str
                ).first()

                if not device:
                    logger.warning(f"Status update ignored: Device '{device_id_str}' not found.")
                    return

                device.status = status
                device.last_seen = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"Device status updated: {site_id}/{device_id_str} is now {status}")
            except Exception as e:
                db.rollback()
                logger.error(f"Database error while updating status: {e}")

    async def handle_event(self, site_id: str, device_id_str: str, component: str, data: Dict[str, Any]):
        """Logs and optionally persists event data."""
        logger.info(f"Event received: {site_id}/{device_id_str}/{component} -> {data}")

        severity = data.get("severity")
        message = data.get("message")
        timestamp_str = data.get("timestamp")

        if severity and message and timestamp_str:
            try:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                await asyncio.to_thread(self._persist_event, site_id, device_id_str, component, dt, severity, message)
            except ValueError:
                logger.warning(f"Invalid timestamp in event: {timestamp_str}")

    def _persist_event(self, site_id: str, device_id_str: str, component: str, dt: datetime, severity: str, message: str):
        with SessionLocal() as db:
            try:
                device = db.query(Device).join(Project).filter(
                    Project.name == site_id,
                    Device.name == device_id_str
                ).first()

                if device:
                    alert = Alert(
                        device_id=device.id,
                        component=component,
                        severity=severity,
                        message=message,
                        timestamp=dt,
                        status="active"
                    )
                    db.add(alert)
                    db.commit()
                    logger.info(f"Alert persisted for {device_id_str}")
            except Exception as e:
                db.rollback()
                logger.error(f"Database error while persisting alert: {e}")

# Global instance
mqtt_service = MQTTService()
