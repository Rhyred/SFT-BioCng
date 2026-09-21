"""NICEGAS Agent Tool Executor.

Priority #4: Tools are READ-ONLY (SELECT queries only).
Priority #5: Tools must respect authenticated user's project scope.
Priority #6: LLM cannot select or bypass authorization scope.
Priority #7: NEXA cannot control actuators.
Priority #8: Start with ONE tool (get_plant_overview).
"""

import logging
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.project import Project
from app.models.device import Device
from app.models.alert import Alert
from app.models.user import User

logger = logging.getLogger(__name__)


def execute_tool(
    name: str,
    arguments: Dict[str, Any],
    db: Session,
    user: User,
    scoped_project_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """Dispatches and executes a registered tool in a safe, read-only manner.
    
    Authorization enforcement:
    - If scoped_project_id is provided, it ALWAYS overrides any project_id passed by the LLM (Priority #6).
    - All database queries are read-only SELECTs (Priority #4).
    """
    logger.info(
        "[ToolExecutor] executing tool=%s user=%s scoped_project_id=%s args=%s",
        name,
        user.username,
        scoped_project_id,
        arguments,
    )

    if name == "get_plant_overview":
        return _execute_get_plant_overview(
            arguments=arguments,
            db=db,
            user=user,
            scoped_project_id=scoped_project_id,
        )

    logger.warning("[ToolExecutor] unrecognized tool: %s", name)
    return {
        "error": f"Tool '{name}' is not recognized or permitted.",
    }


def _execute_get_plant_overview(
    arguments: Dict[str, Any],
    db: Session,
    user: User,
    scoped_project_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """Gathers high-level operational statistics for Bio-CNG projects."""
    # Priority #6: Authenticated scope takes precedence over LLM arguments
    target_project_id: Optional[uuid.UUID] = scoped_project_id

    if target_project_id is None:
        raw_id = arguments.get("project_id")
        if raw_id:
            try:
                target_project_id = uuid.UUID(str(raw_id))
            except (ValueError, TypeError):
                return {"error": f"Invalid project_id format: '{raw_id}'"}

    query = db.query(Project)
    if target_project_id:
        query = query.filter(Project.id == target_project_id)

    projects = query.all()

    if target_project_id and not projects:
        return {
            "error": f"Project with ID '{target_project_id}' not found.",
            "projects": [],
        }

    results = []
    for proj in projects:
        # Fetch devices under this project
        devices = db.query(Device).filter(Device.project_id == proj.id).all()
        total_devices = len(devices)
        online_devices = sum(1 for d in devices if d.status == "online")
        offline_devices = sum(1 for d in devices if d.status == "offline")

        # Fetch active alerts for devices under this project
        device_ids = [d.id for d in devices]
        active_alerts_count = 0
        if device_ids:
            active_alerts_count = (
                db.query(func.count(Alert.id))
                .filter(
                    Alert.device_id.in_(device_ids),
                    Alert.status == "active",
                )
                .scalar()
                or 0
            )

        results.append({
            "project_id": str(proj.id),
            "project_name": proj.name,
            "location": proj.location or "Unspecified",
            "devices_total": total_devices,
            "devices_online": online_devices,
            "devices_offline": offline_devices,
            "active_alerts": active_alerts_count,
        })

    return {
        "projects_count": len(results),
        "projects": results,
    }
