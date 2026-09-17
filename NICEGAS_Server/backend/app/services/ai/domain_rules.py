"""NICEGAS Bio-CNG Domain Rules & Operating Ranges.

IMPORTANT DISCLAIMER:
The threshold ranges defined here are DEVELOPMENT & SIMULATION reference baselines
for the NICEGAS prototype project. They are NOT certified industrial safety limits.
"""

from typing import Dict, Any, Optional, Tuple, NamedTuple
from enum import Enum


class MetricStatus(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MetricThreshold(NamedTuple):
    metric: str
    unit: str
    min_normal: float
    max_normal: float
    min_warning: Optional[float] = None
    max_warning: Optional[float] = None
    min_critical: Optional[float] = None
    max_critical: Optional[float] = None
    description: str = ""


# Component name aliases mapping to canonical component IDs
COMPONENT_ALIASES: Dict[str, str] = {
    "biodigester": "biodigester",
    "digester": "biodigester",
    "anaerobic digester": "biodigester",
    "anaerobic_digester": "biodigester",
    "digester-01": "biodigester",
    "purifikasi": "purifikasi",
    "purification": "purifikasi",
    "gas_cleaning": "purifikasi",
    "purify-01": "purifikasi",
    "kompresi": "kompresi",
    "compression": "kompresi",
    "compressor": "kompresi",
    "comp-01": "kompresi",
    "storage": "storage",
    "gas_storage": "storage",
    "storage-01": "storage",
    "edge_ai": "edge_ai",
    "edge-ai": "edge_ai",
    "edge_ai_01": "edge_ai",
    "edge-ai-01": "edge_ai",
}

# Metric name aliases mapping to canonical metric IDs
METRIC_ALIASES: Dict[str, str] = {
    "temperature": "temperature",
    "temp": "temperature",
    "temperature_c": "temperature",
    "t": "temperature",
    "pressure": "pressure",
    "press": "pressure",
    "pressure_bar": "pressure",
    "pressure_kpa": "pressure",
    "p": "pressure",
    "methane": "methane",
    "methane_percent": "methane",
    "methane_pct": "methane",
    "ch4": "methane",
    "ch4_percent": "methane",
    "gas_flow": "gas_flow",
    "flow": "gas_flow",
    "flow_rate": "gas_flow",
    "gas_flow_nm3h": "gas_flow",
    "ph": "ph",
    "ph_level": "ph",
    "ph_val": "ph",
    "h2s": "h2s",
    "h2s_ppm": "h2s",
    "co2": "co2",
    "co2_pct": "co2",
    "co2_percent": "co2",
    "motor_current": "motor_current",
    "current": "motor_current",
    "motor_curr": "motor_current",
    "motor_current_a": "motor_current",
    "inference_ms": "inference_ms",
    "latency": "inference_ms",
    "inference_latency": "inference_ms",
}

# Standard accepted units for canonical metrics
STANDARD_UNITS: Dict[str, str] = {
    "temperature": "°C",
    "pressure": "bar",
    "methane": "%",
    "gas_flow": "Nm³/h",
    "ph": "pH",
    "h2s": "ppm",
    "co2": "%",
    "motor_current": "A",
    "inference_ms": "ms",
}

# Unit equivalence mappings
UNIT_ALIASES: Dict[str, str] = {
    "°c": "°C",
    "c": "°C",
    "celsius": "°C",
    "degc": "°C",
    "bar": "bar",
    "bars": "bar",
    "kpa": "kPa",
    "%": "%",
    "percent": "%",
    "pct": "%",
    "nm³/h": "Nm³/h",
    "nm3/h": "Nm³/h",
    "m3/h": "Nm³/h",
    "ph": "pH",
    "ppm": "ppm",
    "a": "A",
    "amp": "A",
    "amps": "A",
    "amperes": "A",
    "ms": "ms",
    "millis": "ms",
}

# Component domain development operating thresholds
DOMAIN_THRESHOLDS: Dict[str, Dict[str, MetricThreshold]] = {
    "biodigester": {
        "temperature": MetricThreshold(
            metric="temperature",
            unit="°C",
            min_normal=36.5,
            max_normal=38.5,
            min_warning=35.0,
            max_warning=40.0,
            min_critical=33.0,
            max_critical=42.0,
            description="Mesophilic anaerobic digestion temperature",
        ),
        "pressure": MetricThreshold(
            metric="pressure",
            unit="bar",
            min_normal=1.20,
            max_normal=1.40,
            min_warning=1.10,
            max_warning=1.55,
            min_critical=1.00,
            max_critical=1.70,
            description="Biodigester dome operating pressure",
        ),
        "methane": MetricThreshold(
            metric="methane",
            unit="%",
            min_normal=60.0,
            max_normal=64.0,
            min_warning=55.0,
            max_warning=70.0,
            min_critical=50.0,
            max_critical=75.0,
            description="Raw biogas methane concentration",
        ),
        "gas_flow": MetricThreshold(
            metric="gas_flow",
            unit="Nm³/h",
            min_normal=23.0,
            max_normal=28.0,
            min_warning=18.0,
            max_warning=32.0,
            min_critical=15.0,
            max_critical=35.0,
            description="Biogas generation flow rate",
        ),
        "ph": MetricThreshold(
            metric="ph",
            unit="pH",
            min_normal=6.90,
            max_normal=7.40,
            min_warning=6.60,
            max_warning=7.80,
            min_critical=6.40,
            max_critical=8.20,
            description="Digester slurry pH stability",
        ),
    },
    "purifikasi": {
        "h2s": MetricThreshold(
            metric="h2s",
            unit="ppm",
            min_normal=0.5,
            max_normal=3.0,
            min_warning=0.0,
            max_warning=5.0,
            min_critical=0.0,
            max_critical=10.0,
            description="Hydrogen sulfide contaminant level after scrubber",
        ),
        "co2": MetricThreshold(
            metric="co2",
            unit="%",
            min_normal=1.0,
            max_normal=5.0,
            min_warning=0.5,
            max_warning=7.0,
            min_critical=0.0,
            max_critical=10.0,
            description="Carbon dioxide content remaining in scrubbed biomethane",
        ),
        "methane": MetricThreshold(
            metric="methane",
            unit="%",
            min_normal=94.0,
            max_normal=98.0,
            min_warning=90.0,
            max_warning=99.5,
            min_critical=88.0,
            max_critical=100.0,
            description="Upgraded Bio-CNG methane purity",
        ),
        "gas_flow": MetricThreshold(
            metric="gas_flow",
            unit="Nm³/h",
            min_normal=20.0,
            max_normal=27.0,
            min_warning=15.0,
            max_warning=30.0,
            min_critical=10.0,
            max_critical=35.0,
            description="Purification column throughput",
        ),
        "pressure": MetricThreshold(
            metric="pressure",
            unit="bar",
            min_normal=8.0,
            max_normal=12.0,
            min_warning=6.0,
            max_warning=14.0,
            min_critical=5.0,
            max_critical=16.0,
            description="Downstream purification delivery pressure",
        ),
    },
    "kompresi": {
        "pressure": MetricThreshold(
            metric="pressure",
            unit="bar",
            min_normal=180.0,
            max_normal=220.0,
            min_warning=160.0,
            max_warning=235.0,
            min_critical=140.0,
            max_critical=250.0,
            description="High pressure Bio-CNG compression discharge",
        ),
        "temperature": MetricThreshold(
            metric="temperature",
            unit="°C",
            min_normal=28.0,
            max_normal=40.0,
            min_warning=20.0,
            max_warning=48.0,
            min_critical=15.0,
            max_critical=55.0,
            description="Compressor stage operating temperature",
        ),
        "methane": MetricThreshold(
            metric="methane",
            unit="%",
            min_normal=94.0,
            max_normal=98.0,
            min_warning=90.0,
            max_warning=99.5,
            min_critical=88.0,
            max_critical=100.0,
            description="Compressed gas methane purity",
        ),
        "gas_flow": MetricThreshold(
            metric="gas_flow",
            unit="Nm³/h",
            min_normal=20.0,
            max_normal=27.0,
            min_warning=15.0,
            max_warning=30.0,
            min_critical=10.0,
            max_critical=35.0,
            description="Compressor delivery flow rate",
        ),
        "motor_current": MetricThreshold(
            metric="motor_current",
            unit="A",
            min_normal=8.0,
            max_normal=18.0,
            min_warning=6.0,
            max_warning=21.0,
            min_critical=4.0,
            max_critical=24.0,
            description="Compressor electric motor draw",
        ),
    },
    "storage": {
        "pressure": MetricThreshold(
            metric="pressure",
            unit="bar",
            min_normal=150.0,
            max_normal=250.0,
            min_warning=100.0,
            max_warning=265.0,
            min_critical=50.0,
            max_critical=280.0,
            description="Bio-CNG storage cascade pressure",
        ),
        "temperature": MetricThreshold(
            metric="temperature",
            unit="°C",
            min_normal=20.0,
            max_normal=40.0,
            min_warning=10.0,
            max_warning=48.0,
            min_critical=5.0,
            max_critical=55.0,
            description="Storage cascade ambient/vessel temperature",
        ),
        "methane": MetricThreshold(
            metric="methane",
            unit="%",
            min_normal=94.0,
            max_normal=98.0,
            min_warning=90.0,
            max_warning=99.5,
            min_critical=88.0,
            max_critical=100.0,
            description="Stored Bio-CNG methane quality",
        ),
    },
    "edge_ai": {
        "temperature": MetricThreshold(
            metric="temperature",
            unit="°C",
            min_normal=30.0,
            max_normal=65.0,
            min_warning=20.0,
            max_warning=75.0,
            min_critical=10.0,
            max_critical=85.0,
            description="Edge microcontroller board temperature",
        ),
        "inference_ms": MetricThreshold(
            metric="inference_ms",
            unit="ms",
            min_normal=10.0,
            max_normal=200.0,
            min_warning=5.0,
            max_warning=500.0,
            min_critical=1.0,
            max_critical=1000.0,
            description="Edge inference loop latency",
        ),
    },
}


def normalize_component_name(raw_name: Optional[str]) -> Optional[str]:
    """Normalizes arbitrary component/device strings to canonical component ID."""
    if not raw_name:
        return None
    cleaned = str(raw_name).strip().lower()
    return COMPONENT_ALIASES.get(cleaned, cleaned)


def normalize_metric_name(raw_name: str) -> str:
    """Normalizes metric key to canonical metric ID."""
    cleaned = str(raw_name).strip().lower()
    return METRIC_ALIASES.get(cleaned, cleaned)


def normalize_unit(raw_unit: Optional[str]) -> Optional[str]:
    """Normalizes unit strings to standard representations."""
    if not raw_unit:
        return None
    cleaned = str(raw_unit).strip().lower()
    return UNIT_ALIASES.get(cleaned, raw_unit)


def evaluate_metric(
    component: str,
    metric_name: str,
    value: float,
) -> Tuple[MetricStatus, Optional[MetricThreshold], str]:
    """Evaluates a single numeric metric value against component domain thresholds."""
    canonical_comp = normalize_component_name(component)
    canonical_metric = normalize_metric_name(metric_name)

    if not canonical_comp or canonical_comp not in DOMAIN_THRESHOLDS:
        return MetricStatus.UNKNOWN, None, f"Component '{component}' has no configured domain threshold rules."

    thresholds = DOMAIN_THRESHOLDS[canonical_comp]
    if canonical_metric not in thresholds:
        return MetricStatus.UNKNOWN, None, f"Metric '{metric_name}' is not in configured domain rules for {canonical_comp}."

    th = thresholds[canonical_metric]

    # Check normal band
    if th.min_normal <= value <= th.max_normal:
        return (
            MetricStatus.NORMAL,
            th,
            f"{th.metric.capitalize()} is {value:.2f} {th.unit}, within normal {canonical_comp} development band ({th.min_normal}–{th.max_normal} {th.unit}).",
        )

    # Check critical band
    if (th.min_critical is not None and value < th.min_critical) or (
        th.max_critical is not None and value > th.max_critical
    ):
        bound_desc = f"below critical minimum ({th.min_critical} {th.unit})" if (th.min_critical is not None and value < th.min_critical) else f"above critical maximum ({th.max_critical} {th.unit})"
        return (
            MetricStatus.CRITICAL,
            th,
            f"{th.metric.capitalize()} is {value:.2f} {th.unit}, which is {bound_desc} for {canonical_comp}.",
        )

    # Otherwise warning
    bound_desc = f"below normal range ({th.min_normal}–{th.max_normal} {th.unit})" if value < th.min_normal else f"above normal range ({th.min_normal}–{th.max_normal} {th.unit})"
    return (
        MetricStatus.WARNING,
        th,
        f"{th.metric.capitalize()} is {value:.2f} {th.unit}, which is {bound_desc} for {canonical_comp}.",
    )
