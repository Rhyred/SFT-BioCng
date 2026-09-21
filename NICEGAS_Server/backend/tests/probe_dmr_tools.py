"""DMR Tool Calling Probe — Run manually, not part of CI.

Usage (from inside backend container):
    python tests/probe_dmr_tools.py

Or from host with Docker:
    docker compose exec backend python tests/probe_dmr_tools.py

Verifies:
    1. DMR /v1/chat/completions accepts 'tools' parameter without HTTP error.
    2. Model returns finish_reason containing 'tool_calls' and parseable tool_calls array.
    3. Multi-round: tool result can be sent back and model produces final text.

This script does NOT modify any production code or database state.
"""

import json
import sys
import time
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Install with: pip install httpx")
    sys.exit(1)


BASE_URL = "http://model-runner.docker.internal/v1"

MODELS_TO_TEST = [
    "docker.io/ai/qwen3:8b-q4_K_M",
    "docker.io/ai/qwen3.5:latest",
]

PROBE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_plant_overview",
        "description": "Get overview of Bio-CNG plant projects including device count, online/offline status, and active alert count.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

PROBE_SYSTEM = (
    "You are NEXA, a Bio-CNG plant monitoring assistant. "
    "When the user asks about plant status or condition, you MUST use the get_plant_overview tool to get real data. "
    "Do not guess or fabricate plant data."
)

PROBE_USER_MESSAGE = "Bagaimana kondisi plant Bio-CNG saat ini?"

SIMULATED_TOOL_RESULT = json.dumps({
    "projects": [
        {
            "project_name": "Bio-CNG Plant Alpha",
            "location": "Kampar, Riau",
            "devices_total": 5,
            "devices_online": 4,
            "devices_offline": 1,
            "active_alerts": 2,
        }
    ]
})


def probe_step1_tool_call(model: str) -> Optional[Dict[str, Any]]:
    """Step 1: Send message with tools, check if model returns tool_calls."""
    print(f"\n  Step 1: Sending message with tools definition...")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": PROBE_SYSTEM},
            {"role": "user", "content": PROBE_USER_MESSAGE},
        ],
        "tools": [PROBE_TOOL],
        "tool_choice": "auto",
        "temperature": 0.2,
        "max_tokens": 256,
    }

    try:
        start = time.perf_counter()
        resp = httpx.post(
            f"{BASE_URL}/chat/completions",
            json=payload,
            timeout=120.0,
        )
        latency = (time.perf_counter() - start) * 1000
        resp.raise_for_status()
        data = resp.json()

        choice = data.get("choices", [{}])[0]
        finish_reason = choice.get("finish_reason", "unknown")
        message = choice.get("message", {})
        content = message.get("content", "")
        tool_calls = message.get("tool_calls")

        print(f"    HTTP Status:   {resp.status_code}")
        print(f"    Latency:       {latency:.0f}ms")
        print(f"    Finish reason: {finish_reason}")
        if content:
            print(f"    Content:       {content[:150]}...")
        if tool_calls:
            print(f"    Tool calls:    {json.dumps(tool_calls, indent=6)}")

        return {
            "success": True,
            "finish_reason": finish_reason,
            "tool_calls": tool_calls,
            "content": content,
            "message": message,
            "latency_ms": latency,
        }

    except httpx.HTTPStatusError as e:
        print(f"    ❌ HTTP Error {e.response.status_code}")
        print(f"    Response: {e.response.text[:300]}")
        return {"success": False, "error": f"HTTP {e.response.status_code}"}
    except httpx.ConnectError as e:
        print(f"    ❌ Connection error: {e}")
        print(f"    Is Docker Model Runner running? Is the model loaded?")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"    ❌ Unexpected error: {e}")
        return {"success": False, "error": str(e)}


def probe_step2_tool_result(model: str, step1_result: Dict) -> Optional[Dict[str, Any]]:
    """Step 2: Send tool result back and verify model produces final text."""
    tool_calls = step1_result.get("tool_calls")
    if not tool_calls:
        print(f"\n  Step 2: SKIPPED (no tool_calls in Step 1)")
        return None

    print(f"\n  Step 2: Sending tool result back to model...")

    tool_call = tool_calls[0]
    tool_call_id = tool_call.get("id", "call_probe_0")

    messages = [
        {"role": "system", "content": PROBE_SYSTEM},
        {"role": "user", "content": PROBE_USER_MESSAGE},
        {
            "role": "assistant",
            "content": step1_result.get("content") or None,
            "tool_calls": tool_calls,
        },
        {
            "role": "tool",
            "content": SIMULATED_TOOL_RESULT,
            "tool_call_id": tool_call_id,
        },
    ]

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 512,
    }

    try:
        start = time.perf_counter()
        resp = httpx.post(
            f"{BASE_URL}/chat/completions",
            json=payload,
            timeout=120.0,
        )
        latency = (time.perf_counter() - start) * 1000
        resp.raise_for_status()
        data = resp.json()

        choice = data.get("choices", [{}])[0]
        finish_reason = choice.get("finish_reason", "unknown")
        message = choice.get("message", {})
        content = message.get("content", "")

        print(f"    HTTP Status:   {resp.status_code}")
        print(f"    Latency:       {latency:.0f}ms")
        print(f"    Finish reason: {finish_reason}")
        print(f"    Content:       {content[:300]}")

        return {
            "success": True,
            "finish_reason": finish_reason,
            "content": content,
            "latency_ms": latency,
        }

    except Exception as e:
        print(f"    ❌ Error in Step 2: {e}")
        return {"success": False, "error": str(e)}


def probe_model(model: str) -> str:
    """Runs full probe sequence for one model. Returns verdict."""
    print(f"\n{'=' * 64}")
    print(f"  PROBING: {model}")
    print(f"{'=' * 64}")

    # Step 1: Tool call request
    step1 = probe_step1_tool_call(model)
    if not step1 or not step1.get("success"):
        return "FAILED"

    tool_calls = step1.get("tool_calls")
    finish_reason = step1.get("finish_reason", "")

    if not tool_calls:
        if "tool" in finish_reason.lower():
            print(f"\n  ⚠️  finish_reason indicates tools but tool_calls is empty.")
            return "UNCERTAIN"
        else:
            print(f"\n  ⚠️  Model responded directly without calling tools.")
            print(f"     The model may support tools but chose not to use them.")
            print(f"     Consider using tool_choice='required' to force tool use.")
            return "UNCERTAIN"

    # Validate tool call structure
    tc = tool_calls[0]
    tc_function = tc.get("function", {})
    tc_name = tc_function.get("name", "")

    if tc_name != "get_plant_overview":
        print(f"\n  ⚠️  Model called '{tc_name}' instead of 'get_plant_overview'.")
        return "UNCERTAIN"

    print(f"\n  ✅ Step 1 PASSED: Model returned tool_call for '{tc_name}'")

    # Step 2: Multi-round
    step2 = probe_step2_tool_result(model, step1)
    if not step2 or not step2.get("success"):
        print(f"\n  ⚠️  Step 2 failed. Tool calling works but multi-round may not.")
        return "PARTIAL"

    if step2.get("content"):
        print(f"\n  ✅ Step 2 PASSED: Model produced final response from tool result")
        return "SUPPORTED"
    else:
        print(f"\n  ⚠️  Step 2 returned empty content.")
        return "PARTIAL"


def main():
    print("=" * 64)
    print("  NICEGAS — DMR Tool Calling Probe")
    print("  Target: Docker Model Runner at")
    print(f"  {BASE_URL}")
    print("=" * 64)

    # Check DMR is reachable first
    print("\nChecking DMR connectivity...")
    try:
        resp = httpx.get(f"{BASE_URL}/models", timeout=10.0)
        resp.raise_for_status()
        models_data = resp.json()
        available = models_data.get("data", [])
        print(f"  DMR reachable. {len(available)} model(s) available.")
        for m in available:
            print(f"    - {m.get('id', 'unknown')}")
    except Exception as e:
        print(f"  ❌ Cannot reach DMR: {e}")
        print(f"  Make sure Docker Desktop is running and models are loaded.")
        sys.exit(1)

    # Probe each model
    results = {}
    for model in MODELS_TO_TEST:
        results[model] = probe_model(model)

    # Summary
    print(f"\n{'=' * 64}")
    print("  PROBE RESULTS SUMMARY")
    print(f"{'=' * 64}")

    verdict_symbols = {
        "SUPPORTED": "✅",
        "PARTIAL": "⚠️ ",
        "UNCERTAIN": "⚠️ ",
        "FAILED": "❌",
    }

    for model, verdict in results.items():
        symbol = verdict_symbols.get(verdict, "❓")
        print(f"  {symbol} {model}: {verdict}")

    all_supported = all(v == "SUPPORTED" for v in results.values())
    any_failed = any(v == "FAILED" for v in results.values())

    print()
    if all_supported:
        print("  ✅ ALL MODELS CONFIRMED TOOL CALLING.")
        print("     Safe to proceed to Phase 1.")
        sys.exit(0)
    elif any_failed:
        print("  ❌ ONE OR MORE MODELS FAILED.")
        print("     Do NOT proceed until failures are resolved.")
        sys.exit(1)
    else:
        print("  ⚠️  PARTIAL / UNCERTAIN results.")
        print("     Review output carefully before proceeding.")
        print("     Consider testing with tool_choice='required'.")
        sys.exit(2)


if __name__ == "__main__":
    main()
