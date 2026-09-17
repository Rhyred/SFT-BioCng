"""NICEGAS Telemetry Normalization Layer.

Converts and validates raw incoming telemetry payloads into clean, typed,
domain-grounded structures suitable for deterministic evaluation and LLM prompts.
Never alters original DB telemetry.
"""

import re
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from app.services.ai.domain_rules import (
    normalize_component_name,
    normalize_metric_name,
    normalize_unit,
    STANDARD_UNITS,
    MetricStatus,
)


class NormalizedMetric(BaseModel):
    name: str = Field(..., description="Canonical metric identifier")
    raw_name: str = Field(..., description="Original metric key")
    value: Optional[float] = Field(None, description="Numeric sensor value")
    unit: Optional[str] = Field(None, description="Physical engineering unit")
    is_valid: bool = Field(True, description="Whether metric is structurally valid and numeric")
    error: Optional[str] = Field(None, description="Validation error explanation if invalid")


class NormalizedTelemetryContext(BaseModel):
    component: Optional[str] = None
    device_name: Optional[str] = None
    metrics: List[NormalizedMetric] = Field(default_factory=list)
    has_invalid: bool = False
    invalid_reasons: List[str] = Field(default_factory=list)


# Pattern to detect suspicious prompt injection keywords in telemetry strings
INJECTION_PATTERN = re.compile(
    r"(ignore\s+previous|system\s+prompt|disregard|you\s+are\s+now|override|sudo|admin|act\s+as)",
    re.IGNORECASE,
)


def sanitize_string(val: str, max_length: int = 120) -> str:
    """Sanitizes strings to prevent prompt injection or formatting corruption."""
    if not isinstance(val, str):
        val = str(val)
    # Strip dangerous characters and clamp length
    cleaned = re.sub(r"[\r\n\t]+", " ", val).strip()
    return cleaned[:max_length]


def normalize_telemetry_payload(
    telemetry: Dict[str, Any],
    component: Optional[str] = None,
    device_name: Optional[str] = None,
) -> NormalizedTelemetryContext:
    """Parses, sanitizes, and normalizes a raw telemetry dictionary.
    
    Supports both nested format {"temperature": {"v": 37.8, "u": "°C"}}
    and flat key-value pairs {"temperature": 37.8}.
    """
    canonical_component = normalize_component_name(component)
    clean_device = sanitize_string(device_name) if device_name else None

    normalized_metrics: List[NormalizedMetric] = []
    has_invalid = False
    invalid_reasons: List[str] = []

    if not isinstance(telemetry, dict) or not telemetry:
        return NormalizedTelemetryContext(
            component=canonical_component,
            device_name=clean_device,
            metrics=[],
            has_invalid=True,
            invalid_reasons=["Telemetry payload is empty or not a valid dictionary."],
        )

    for raw_key, raw_val in telemetry.items():
        clean_key = sanitize_string(str(raw_key), max_length=64)
        canonical_metric = normalize_metric_name(clean_key)

        # Check for prompt injection in key name
        if INJECTION_PATTERN.search(clean_key):
            has_invalid = True
            invalid_reasons.append(f"Metric key '{clean_key}' contains disallowed instructional patterns.")
            normalized_metrics.append(
                NormalizedMetric(
                    name=canonical_metric,
                    raw_name=clean_key,
                    value=None,
                    unit=None,
                    is_valid=False,
                    error="Disallowed pattern in metric key",
                )
            )
            continue

        numeric_value: Optional[float] = None
        unit_str: Optional[str] = None
        is_valid = True
        error_msg: Optional[str] = None

        # Case 1: Nested structure {"v": 37.8, "u": "°C"}
        if isinstance(raw_val, dict):
            raw_v = raw_val.get("v")
            raw_u = raw_val.get("u")

            # Check injection in unit string
            if isinstance(raw_u, str) and INJECTION_PATTERN.search(raw_u):
                is_valid = False
                error_msg = "Disallowed pattern in unit string"
            else:
                unit_str = normalize_unit(raw_u) if raw_u is not None else None

            # Validate numeric value
            if raw_v is None:
                is_valid = False
                error_msg = "Metric value 'v' is missing"
            else:
                try:
                    # Reject string injections in value field
                    if isinstance(raw_v, str):
                        if INJECTION_PATTERN.search(raw_v):
                            raise ValueError("Prompt injection pattern in metric value")
                    numeric_value = float(raw_v)
                except (ValueError, TypeError):
                    is_valid = False
                    error_msg = f"Non-numeric value '{sanitize_string(str(raw_v))}' in metric '{clean_key}'"

        # Case 2: Flat numeric/string structure {"temperature": 37.8}
        else:
            if isinstance(raw_val, str) and INJECTION_PATTERN.search(raw_val):
                is_valid = False
                error_msg = "Disallowed pattern in metric value"
            else:
                try:
                    numeric_value = float(raw_val)
                    # Assign canonical default unit if available
                    unit_str = STANDARD_UNITS.get(canonical_metric)
                except (ValueError, TypeError):
                    is_valid = False
                    error_msg = f"Non-numeric value '{sanitize_string(str(raw_val))}' in metric '{clean_key}'"

        # Fallback default unit if unit was not provided in nested object
        if is_valid and not unit_str and canonical_metric in STANDARD_UNITS:
            unit_str = STANDARD_UNITS[canonical_metric]

        if not is_valid:
            has_invalid = True
            invalid_reasons.append(error_msg or f"Invalid telemetry for {clean_key}")

        normalized_metrics.append(
            NormalizedMetric(
                name=canonical_metric,
                raw_name=clean_key,
                value=numeric_value,
                unit=unit_str,
                is_valid=is_valid,
                error=error_msg,
            )
        )

    return NormalizedTelemetryContext(
        component=canonical_component,
        device_name=clean_device,
        metrics=normalized_metrics,
        has_invalid=has_invalid,
        invalid_reasons=invalid_reasons,
    )
