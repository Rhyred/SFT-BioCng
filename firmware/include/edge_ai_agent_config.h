/**
 * @file edge_ai_agent_config.h
 * @brief NICEGAS Bio-CNG — Edge AI Agent Configuration Schema
 *
 * ============================================================
 * PURPOSE:
 *   Centralized, single-source-of-truth configuration for the
 *   NICEGAS Edge AI Agent running on ESP32 (nicegas_edge_ai_arduino).
 *
 *   This schema defines:
 *   1. Node Identity         — Project, Device, Component
 *   2. Network Config        — WiFi, MQTT Broker
 *   3. MQTT Topic Contract   — Telemetry, Status, AI Event topics
 *   4. Telemetry Mode        — Dummy | Physical Sensor
 *   5. Sensor Metric Schema  — Name, Unit, Simulated Range, Pin
 *   6. Threshold Rules       — Per-metric alarm thresholds for edge inference
 *   7. AI Agent Behavior     — Inference interval, publish behavior
 *   8. Publish Contract      — QoS, Retain, Buffer size
 *   9. Timing Config         — Intervals (ms)
 *
 * USAGE:
 *   #include "edge_ai_agent_config.h"
 *   All identifiers in this file become the single definition used
 *   by nicegas_edge_ai_arduino.ino. Do NOT hardcode values in the .ino
 *
 * IMPORTANT:
 *   PROJECT_NAME, DEVICE_ID, and COMPONENT must EXACTLY match the
 *   database records in PostgreSQL (case-sensitive, whitespace-sensitive).
 * ============================================================
 */

#pragma once

#include <Arduino.h>

// ============================================================
// SECTION 1: TELEMETRY MODE
// ============================================================
// Set to 1 for dummy simulation (no physical sensors).
// Set to 0 when physical sensors are wired and ready.
#define TELEMETRY_MODE_DUMMY    1

// ============================================================
// SECTION 2: NODE IDENTITY
// ============================================================
// These values MUST match exactly what is in the PostgreSQL database.
// Project name: "Bio-CNG Plant New"
// Device name : "DIGESTER-01"
// Component   : "biodigester"

#define AGENT_PROJECT_NAME      "Bio-CNG Plant New"
#define AGENT_DEVICE_ID         "EDGE-01"
#define AGENT_DEVICE_NAME       "ESP32 Edge AI Biodigester Node"
#define AGENT_COMPONENT         "biodigester"
#define AGENT_FIRMWARE_VERSION  "1.0.0-edge-ai"

// ============================================================
// SECTION 3: NETWORK — WiFi
// ============================================================
#define WIFI_SSID               "ICT-LAB WORKSPACE"
#define WIFI_PASSWORD           "ICTLAB2024"
// NOTE: Password is not printed to Serial log.

// ============================================================
// SECTION 4: NETWORK — MQTT BROKER
// ============================================================
// IMPORTANT:
// Set MQTT_BROKER_HOST to the LAN IP of the machine running Mosquitto.
// The same value MUST be used by all four ESP32 nodes.
#define MQTT_BROKER_HOST        "192.168.1.204"
#define MQTT_BROKER_PORT        1883
#define MQTT_USERNAME           ""
#define MQTT_PASSWORD_STR       ""
// QoS: 1 for all publishes (at least once, ensures backend receives data)
#define MQTT_QOS_TELEMETRY      1
#define MQTT_QOS_STATUS         1
#define MQTT_QOS_AI_EVENT       1
// Buffer size: must fit the largest JSON payload
#define MQTT_BUFFER_SIZE        768
#define MQTT_KEEPALIVE_SEC      15

// ============================================================
// SECTION 5: MQTT TOPIC CONTRACT
// ============================================================
// Topic format: nicegas/{PROJECT_NAME}/{DEVICE_ID}/{category}/{component}
//
// Telemetry  : nicegas/Bio-CNG Plant New/DIGESTER-01/telemetry/biodigester
// Status     : nicegas/Bio-CNG Plant New/DIGESTER-01/status/connection
// AI Event   : nicegas/Bio-CNG Plant New/DIGESTER-01/event/ai_inference
//
// Topics are constructed at runtime via helper functions.
// DO NOT hardcode them separately — use the macros above.

// ============================================================
// SECTION 6: SENSOR METRIC SCHEMA
// ============================================================
// Each metric is defined as a struct for runtime use.
// Range defines the valid operational bounds for the Biodigester node.
//
// | Metric Key   | Unit    | Normal Min | Normal Max | Warn Threshold | Alarm Threshold |
// |:------------ |:------- |:---------- |:---------- |:-------------- |:--------------- |
// | temperature  | C       | 36.5       | 38.5       | 38.5           | 39.5            |
// | pressure     | bar     | 1.20       | 1.40       | 1.45           | 1.55            |
// | methane      | %       | 60.0       | 64.0       | 58.0           | 55.0            |
// | gas_flow     | Nm3/h   | 23.0       | 28.0       | 20.0           | 18.0            |
// | ph           | pH      | 6.90       | 7.40       | 6.80 / 7.50    | 6.70 / 7.60     |
//
// Runtime struct for threshold evaluation:
struct MetricConfig {
    const char* key;        // JSON key used in payload "metrics" object
    const char* unit;       // Unit string used in payload {"u": "..."}
    float       simInit;    // Initial simulated value
    float       simMin;     // Simulation lower bound (DUMMY mode)
    float       simMax;     // Simulation upper bound (DUMMY mode)
    float       simStep;    // Simulation max step per interval
    float       warnLow;    // Threshold: warn if below (use -1 to disable)
    float       warnHigh;   // Threshold: warn if above (use -1 to disable)
    float       alarmLow;   // Threshold: alarm if below (use -1 to disable)
    float       alarmHigh;  // Threshold: alarm if above (use -1 to disable)
};

// Biodigester Metric Table — used by edge AI agent for inference
static const MetricConfig BIODIGESTER_METRICS[] = {
    //    key            unit      init   simMin  simMax  step   warnLow  warnHigh  alarmLow  alarmHigh
    { "temperature", "\xC2\xB0""C", 37.5f, 36.5f,  38.5f,  0.08f,  36.5f,   38.5f,    35.5f,    39.5f  },
    { "pressure",    "bar",         1.30f, 1.20f,  1.40f,  0.01f,  1.20f,   1.45f,    1.10f,    1.55f  },
    { "methane",     "%",           62.0f, 60.0f,  64.0f,  0.15f,  58.0f,   -1.0f,    55.0f,    -1.0f  },
    { "gas_flow",    "Nm\xC2\xB3/h",25.5f, 23.0f,  28.0f,  0.20f,  20.0f,   -1.0f,    18.0f,    -1.0f  },
    { "ph",          "pH",          7.15f, 6.90f,  7.40f,  0.02f,  6.80f,   7.50f,    6.70f,    7.60f  },
};

#define BIODIGESTER_METRIC_COUNT (sizeof(BIODIGESTER_METRICS) / sizeof(BIODIGESTER_METRICS[0]))

// ============================================================
// SECTION 7: HARDWARE PIN MAP (Biodigester Node 1)
// ============================================================
// These are reference pin assignments from the wiring diagram.
// Only used when TELEMETRY_MODE_DUMMY == 0.
//
// | Signal          | ESP32 GPIO | Interface     | Sensor         |
// |:--------------- |:---------- |:------------- |:-------------- |
// | DS18B20 Temp    | GPIO2 (D4) | 1-Wire        | Temperature    |
// | MQ-4 CH4        | GPIO34(A0) | ADC1_CH6      | Methane (CH4)  |
// | pH-4502C        | GPIO35(A1) | ADC1_CH7      | pH Sensor      |
//
#define PIN_TEMP_DS18B20        2   // GPIO2  -> 1-Wire Data -> DS18B20
#define PIN_CH4_MQ4            34   // GPIO34 -> ADC1_CH6   -> MQ-4 Methane
#define PIN_PH_METER           35   // GPIO35 -> ADC1_CH7   -> pH-4502C

// ============================================================
// SECTION 8: AI AGENT BEHAVIOR CONFIG
// ============================================================
// The Edge AI Agent performs local rule-based inference
// every AI_INFERENCE_INTERVAL_MS milliseconds.
// On a significant event (warn/alarm), it publishes to the AI event topic.

// Enable/disable edge AI inference engine
#define EDGE_AI_ENABLED         1

// How often to run local inference (ms)
// Default: every telemetry publish (same cycle)
#define AI_INFERENCE_INTERVAL_MS    5000

// Minimum # of consecutive "warn" readings before publishing an AI event
// Prevents flicker/noise from triggering events
#define AI_WARN_DEBOUNCE_COUNT      3

// Minimum # of consecutive "alarm" readings before publishing an AI event
#define AI_ALARM_DEBOUNCE_COUNT     2

// Cooldown between repeated AI event publishes for the same metric (ms)
// Prevents event storm on sustained threshold breach
#define AI_EVENT_COOLDOWN_MS        30000

// AI confidence level reported in event payload (edge rule-based, not ML)
// Range: 0.0 to 1.0
// For rule-based: fixed at 1.0 (deterministic threshold check)
#define AI_RULE_CONFIDENCE          1.0f

// ============================================================
// SECTION 9: AI EVENT PAYLOAD SCHEMA
// ============================================================
// Published to: nicegas/{PROJECT_NAME}/{DEVICE_ID}/event/ai_inference
//
// Payload structure:
// {
//   "device_id":   "DIGESTER-01",
//   "component":   "biodigester",
//   "timestamp":   "2026-09-15T08:10:32Z",
//   "event_type":  "warn" | "alarm" | "normal",
//   "metric":      "temperature",
//   "value":       {"v": 39.2, "u": "degC"},
//   "threshold":   {"warn_high": 38.5, "alarm_high": 39.5},
//   "confidence":  1.0,
//   "message":     "Temperature approaching upper warning limit."
// }
//
// Retain: false (events are transient)
// QoS   : 1

// ============================================================
// SECTION 10: STATUS PAYLOAD SCHEMA
// ============================================================
// Online status published to: nicegas/{PROJECT_NAME}/{DEVICE_ID}/status/connection
// Retain: true  (persistent last-known state)
// QoS   : 1
//
// Online payload:
// {
//   "status":       "online",
//   "timestamp":    "2026-09-15T08:10:30Z",
//   "device_id":    "DIGESTER-01",
//   "device_name":  "ESP32 Edge AI Biodigester Node"
// }
//
// LWT (Last Will) payload (set at connect time, auto-published on disconnect):
// {
//   "status":       "offline",
//   "device_id":    "DIGESTER-01",
//   "device_name":  "ESP32 Edge AI Biodigester Node"
// }

// ============================================================
// SECTION 11: TELEMETRY PUBLISH SCHEMA
// ============================================================
// Published to: nicegas/{PROJECT_NAME}/{DEVICE_ID}/telemetry/{COMPONENT}
// Retain: false
// QoS   : 1
//
// Payload:
// {
//   "device_id":  "DIGESTER-01",
//   "component":  "biodigester",
//   "status":     "optimal",   <- calculateStatus(): "optimal"|"warning"|"alarm"
//   "timestamp":  "2026-09-15T08:10:32Z",
//   "metrics": {
//     "temperature": {"v": 37.82, "u": "degC"},
//     "pressure":    {"v": 1.32,  "u": "bar"},
//     "methane":     {"v": 61.6,  "u": "%"},
//     "gas_flow":    {"v": 26.2,  "u": "Nm3/h"},
//     "ph":          {"v": 7.14,  "u": "pH"}
//   }
// }
//
// "status" field values:
//   "optimal"  -- all metrics within normal range
//   "warning"  -- one or more metrics breached warn threshold
//   "alarm"    -- one or more metrics breached alarm threshold
//   "offline"  -- device not reachable (LWT only)

// ============================================================
// SECTION 12: TIMING CONFIG
// ============================================================
#define TELEMETRY_INTERVAL_MS           5000    // Publish telemetry every 5 seconds
#define MQTT_RECONNECT_INTERVAL_MS      5000    // Retry MQTT connect every 5 seconds
#define NTP_SYNC_TIMEOUT_MS             10000   // Max wait for first NTP sync on boot

// NTP Servers (UTC, no timezone offset)
#define NTP_SERVER_PRIMARY      "pool.ntp.org"
#define NTP_SERVER_SECONDARY    "time.nist.gov"
#define NTP_SERVER_TERTIARY     "time.google.com"

// Epoch validity check -- any timestamp before this is considered invalid
// Unix epoch for 2023-11-01T00:00:00Z ~= 1698796800
#define NTP_VALID_EPOCH_MIN     1700000000UL

// ============================================================
// SECTION 13: STALE TOPIC CLEANUP NOTICE
// ============================================================
// The following MQTT retained topics (from old firmware versions) may
// still exist on the Mosquitto broker and should be manually cleared:
//
//   nicegas/192.168.1.204/#   <- old PROJECT_NAME was IP address
//   nicegas/Bio-CNG ITENAS/#  <- old PROJECT_NAME was incorrect
//   nicegas/Bio-CNG Plant Alpha/# <- if this existed
//
// To clear retained topics, run on the broker machine:
//   mosquitto_pub -h 192.168.1.204 -t "nicegas/Bio-CNG ITENAS/DIGESTER-01/status/connection" -r -n
//   mosquitto_pub -h 192.168.1.204 -t "nicegas/192.168.1.204/DIGESTER-01/status/connection"  -r -n
//
// This must be done ONCE after flashing the corrected firmware.
// ESP32 must NOT attempt to clear stale topics -- only the broker admin tool.

// ============================================================
// END OF EDGE AI AGENT CONFIG SCHEMA
// ============================================================
