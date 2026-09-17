"""NICEGAS Deterministic Pre-Analysis Engine.

Executes rule-based domain evaluation prior to LLM synthesis.
Ensures factual domain grounding and computes immutable baseline status.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.ai.domain_rules import (
    evaluate_metric,
    DOMAIN_THRESHOLDS,
    MetricStatus,
    MetricThreshold,
)
from app.services.ai.normalization import (
    NormalizedTelemetryContext,
    NormalizedMetric,
)


class DeterministicEvaluation(BaseModel):
    status: str = Field("unknown", description="Deterministic baseline status (normal, warning, critical, unknown)")
    observations: List[str] = Field(default_factory=list, description="Factual domain observations")
    possible_causes: List[str] = Field(default_factory=list, description="Rule-based potential operational causes")
    recommended_checks: List[str] = Field(default_factory=list, description="Safe advisory operator inspections")
    is_fully_normal: bool = False
    has_unknowns: bool = False


# Domain cause-and-check heuristics for abnormal conditions
ANOMALY_HEURISTICS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "biodigester": {
        "temperature_high": {
            "causes": ["Substrate heating loop over-temperature", "Excess external thermal load on digester jacket"],
            "checks": ["Inspect biodigester heating circulation valve", "Verify PT100 temperature transmitter calibration"],
        },
        "temperature_low": {
            "causes": ["Heating system failure or insufficient hot water circulation", "Cold feedstock batch shock"],
            "checks": ["Check heat exchanger inlet temperature", "Verify heating loop pump operation"],
        },
        "methane_low": {
            "causes": ["Volatile fatty acid (VFA) accumulation / organic shock load", "Substrate retention time too short"],
            "checks": ["Verify feedstock loading rate and dry matter content", "Measure FOS/TAC (VFA/alkalinity) ratio", "Check slurry pH level"],
        },
        "methane_high": {
            "causes": ["Stable, high-yield methanogenesis with optimal organic loading"],
            "checks": ["Maintain current feeding regime and monitor gas production"],
        },
        "pressure_high": {
            "causes": ["Downstream gas line valve closed or partially throttled", "Purification intake restriction", "Biogas production exceeding take-off capacity"],
            "checks": ["Verify gas line isolation valves", "Check mechanical dome pressure relief valve (PRV)", "Inspect purifikasi suction line"],
        },
        "pressure_low": {
            "causes": ["Dome membrane leak or sampling port open", "Sudden gas over-extraction", "Under-production of biogas"],
            "checks": ["Inspect digester seals and piping connections for leakage", "Verify gas booster blower speed"],
        },
        "ph_low": {
            "causes": ["Acidosis / excessive organic acid formation", "Buffer capacity exhaustion"],
            "checks": ["Temporarily reduce or pause fresh feedstock feeding", "Check buffer dosing system", "Verify laboratory slurry pH"],
        },
        "ph_high": {
            "causes": ["Ammonia accumulation / high protein feedstock", "Alkaline chemical over-dosing"],
            "checks": ["Check nitrogen/protein content of recent feedstock batches", "Verify buffer dosing setpoint"],
        },
        "gas_flow_high": {
            "causes": ["High methanogenic activity following active substrate batch"],
            "checks": ["Monitor dome pressure and purifikasi receiving buffer capacity"],
        },
        "gas_flow_low": {
            "causes": ["Reduced microbial kinetics", "Feedstock starvation", "Gas line condensation trap blockage"],
            "checks": ["Inspect condensate water drain traps along piping", "Check digester slurry feeding log"],
        },
    },
    "purifikasi": {
        "h2s_high": {
            "causes": ["Desulfurization media saturation", "Increased sulfur content in raw biogas feed"],
            "checks": ["Check biological desulfurizer air injection / iron sponge media bed saturation", "Inspect scrubber differential pressure"],
        },
        "co2_high": {
            "causes": ["Membrane / PSA separation efficiency decline", "Scrubber column water recirculation rate low"],
            "checks": ["Inspect membrane separator inlet pressure and differential", "Verify PSA cycle timing and wash column pump"],
        },
        "methane_low": {
            "causes": ["Incomplete CO2/H2S separation in purification unit", "Upstream raw biogas quality degradation"],
            "checks": ["Check purification separation stage pressures", "Inspect off-gas vent line to ensure no Bio-CNG loss", "Verify inline gas analyzer calibration"],
        },
        "pressure_high": {
            "causes": ["Compressor suction regulator restricted", "Downstream pipeline backpressure"],
            "checks": ["Inspect purification discharge pressure regulating valve", "Check compressor suction filter"],
        },
        "pressure_low": {
            "causes": ["Feed gas booster blower failure", "Purification pre-filter clogging"],
            "checks": ["Inspect pre-filters for particulate loading", "Check feed blower discharge pressure"],
        },
    },
    "kompresi": {
        "pressure_high": {
            "causes": ["Bio-CNG storage cascade approaching full capacity", "Discharge check valve restriction"],
            "checks": ["Inspect storage cascade manifold valves", "Verify compressor automated high-pressure cutoff switch"],
        },
        "pressure_low": {
            "causes": ["Suction gas starvation", "Compressor stage valve leakage", "High downstream consumption"],
            "checks": ["Inspect compressor stage valves and piston rings", "Verify purifikasi delivery pressure"],
        },
        "temperature_high": {
            "causes": ["Intercooler or aftercooler fouling", "Cooling fan failure or high ambient temperature", "Low lubrication oil level"],
            "checks": ["Inspect compressor radiator core for debris", "Check compressor oil level and lubrication circuit", "Verify cooling fan airflow"],
        },
        "motor_current_high": {
            "causes": ["High mechanical compression load", "Mechanical binding or bearing wear", "Electrical supply voltage unbalance"],
            "checks": ["Check compressor mechanical free rotation", "Measure electrical supply voltage across all three phases", "Inspect motor thermal overload relay"],
        },
    },
    "storage": {
        "pressure_high": {
            "causes": ["Storage cascade overfilling beyond nominal working limit"],
            "checks": ["Verify cascade relief valves and automated compressor interlocks"],
        },
        "pressure_low": {
            "causes": ["High dispensing demand or depleted buffer inventory"],
            "checks": ["Verify dispensing schedule and compressor replenishment cycle"],
        },
    },
}


def run_deterministic_pre_analysis(
    normalized_ctx: NormalizedTelemetryContext,
) -> DeterministicEvaluation:
    """Evaluates normalized telemetry deterministically against Bio-CNG rules."""
    observations: List[str] = []
    possible_causes: List[str] = []
    recommended_checks: List[str] = []

    statuses: List[MetricStatus] = []
    has_unknowns = False

    component = normalized_ctx.component

    # If component is unknown or missing
    if not component:
        observations.append("Component/subsystem not specified or unrecognized. Operating thresholds cannot be verified.")
        return DeterministicEvaluation(
            status="unknown",
            observations=observations,
            possible_causes=[],
            recommended_checks=["Specify valid component ('biodigester', 'purifikasi', 'kompresi', 'storage', 'edge_ai')."],
            is_fully_normal=False,
            has_unknowns=True,
        )

    # Process any structural validation errors from normalization
    if normalized_ctx.has_invalid:
        has_unknowns = True
        for reason in normalized_ctx.invalid_reasons:
            observations.append(f"Data issue: {reason}")

    if not normalized_ctx.metrics:
        observations.append("No metric data provided in telemetry payload.")
        return DeterministicEvaluation(
            status="unknown",
            observations=observations,
            possible_causes=[],
            recommended_checks=["Ensure telemetry payload contains valid sensor key-value pairs."],
            is_fully_normal=False,
            has_unknowns=True,
        )

    for m in normalized_ctx.metrics:
        if not m.is_valid or m.value is None:
            has_unknowns = True
            observations.append(f"Metric '{m.raw_name}' cannot be evaluated: {m.error or 'Invalid numeric value'}")
            statuses.append(MetricStatus.UNKNOWN)
            continue

        eval_status, th, explanation = evaluate_metric(component, m.name, m.value)
        statuses.append(eval_status)
        observations.append(explanation)

        # Lookup cause & check heuristics for anomalies
        if eval_status in (MetricStatus.WARNING, MetricStatus.CRITICAL) and th:
            anomaly_key = f"{m.name}_high" if m.value > th.max_normal else f"{m.name}_low"
            comp_heuristics = ANOMALY_HEURISTICS.get(component, {})
            h_data = comp_heuristics.get(anomaly_key)
            if h_data:
                for c in h_data.get("causes", []):
                    if c not in possible_causes:
                        possible_causes.append(c)
                for chk in h_data.get("checks", []):
                    if chk not in recommended_checks:
                        recommended_checks.append(chk)

    # Compute baseline status
    if MetricStatus.CRITICAL in statuses:
        overall_status = "critical"
    elif MetricStatus.WARNING in statuses:
        overall_status = "warning"
    elif MetricStatus.UNKNOWN in statuses or has_unknowns:
        # If there are no warnings or criticals but there are unknown/invalid metrics
        if all(s == MetricStatus.NORMAL for s in statuses if s != MetricStatus.UNKNOWN) and not statuses:
            overall_status = "unknown"
        elif any(s == MetricStatus.NORMAL for s in statuses) and not any(s in (MetricStatus.WARNING, MetricStatus.CRITICAL) for s in statuses):
            # Partial normal with some unknown
            overall_status = "unknown"
        else:
            overall_status = "unknown"
    else:
        overall_status = "normal"

    is_fully_normal = overall_status == "normal" and not has_unknowns

    # Default preventive check for 100% normal state
    if is_fully_normal and not recommended_checks:
        recommended_checks.append("Maintain routine sensor surveillance and scheduled maintenance intervals.")

    return DeterministicEvaluation(
        status=overall_status,
        observations=observations,
        possible_causes=possible_causes,
        recommended_checks=recommended_checks,
        is_fully_normal=is_fully_normal,
        has_unknowns=has_unknowns,
    )


def build_system_telemetry_context(
    node_telemetries: Dict[str, Dict[str, Any]],
) -> str:
    """Builds a unified multi-node telemetry context for system-level analysis.
    
    Consumes latest telemetry per node:
    DIGESTER -> PURIFIKASI -> KOMPRESI -> STORAGE
    """
    lines = ["NICEGAS Multi-Node Plant System Context:"]
    pipeline_order = ["biodigester", "purifikasi", "kompresi", "storage", "edge_ai"]

    for comp in pipeline_order:
        if comp in node_telemetries:
            raw_data = node_telemetries[comp]
            lines.append(f"\n--- Node: {comp.upper()} ---")
            for k, v in raw_data.items():
                if isinstance(v, dict):
                    val = v.get('v', 'N/A')
                    unit = v.get('u', '')
                    lines.append(f"- {k}: {val} {unit}")
                else:
                    lines.append(f"- {k}: {v}")

    return "\n".join(lines)
