"""NICEGAS Agent Tool Definitions (OpenAI Function Calling Format).

Priority #4: Tools are READ-ONLY.
Priority #7: NEXA cannot control actuators.
Priority #8: Start with ONE tool (get_plant_overview).
"""

from typing import List, Dict, Any

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_plant_overview",
            "description": (
                "Get overview of Bio-CNG plant projects including device count, "
                "online/offline device status, and active alert count. "
                "Strictly read-only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": (
                            "Optional UUID string of a specific project. "
                            "If omitted, returns an overview of all projects accessible to the user."
                        ),
                    }
                },
                "required": [],
            },
        },
    }
]
