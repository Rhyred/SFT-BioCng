/**
 * @file nicegas_esp4_edge_ai_actuator.ino
 * @brief NICEGAS Bio-CNG — ESP4: EDGE AI + ACTUATOR NODE
 *
 * ============================================================
 * NICEGAS ESP4
 * EDGE AI + ACTUATOR NODE
 *
 * Device:
 *   EDGE-AI-01
 *
 * Role:
 *   Local decision engine + actuator control.
 *   Subscribes to Node 1/2/3 telemetry, caches state.
 *   Accepts explicit MQTT commands, validates, passes through
 *   safety interlock, and executes on named actuator targets.
 *
 * Hardware:
 *   ESP32 DevKit V1
 *   4-channel relay module (5V optocoupler)
 *   DC 3V gas solenoid valve
 *   LM2596 Step-Down 9V -> 5V (per wiring diagram)
 *
 * IMPORTANT:
 *   - Actuator outputs are forced OFF on boot BEFORE any other init.
 *   - AUTO mode is DISABLED by default.
 *   - No direct GPIO commands are accepted.
 *   - All commands pass full validation + safety interlock.
 *   - VERIFY WIRING DIAGRAM BEFORE ENERGIZING ACTUATORS.
 *
 * Libraries Required (Arduino Library Manager):
 *   1. PubSubClient by Nick O'Leary
 *   2. ArduinoJson by Benoit Blanchon (v6 or v7)
 *
 * ESP32 Arduino Core Required:
 *   espressif/arduino-esp32 >= 2.0
 * ============================================================
 */

#include <WiFi.h>
#include <WiFiClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include <esp_task_wdt.h>

// ==============================================================================
// SECTION 1: CONFIGURATION — IDENTITY
// ==============================================================================

// These values MUST EXACTLY match the PostgreSQL database records.
// Case-sensitive. Whitespace-sensitive.
#define AGENT_PROJECT_NAME      "Bio-CNG Plant New"
#define AGENT_DEVICE_ID         "EDGE-AI-01"
#define AGENT_DEVICE_NAME       "ESP32 Edge AI Actuator Node"
#define AGENT_COMPONENT         "edge_ai"
#define AGENT_FIRMWARE_VERSION  "1.0.0-esp4"

// ==============================================================================
// SECTION 2: CONFIGURATION — NETWORK
// ==============================================================================

// WiFi credentials (password is NEVER printed to Serial)
#define WIFI_SSID               "ICT-LAB WORKSPACE"
#define WIFI_PASSWORD           "ICTLAB2024"

// IMPORTANT:
// Set MQTT_BROKER_HOST to the LAN IP of the machine running Mosquitto.
// ALL NICEGAS ESP32 nodes must use the same broker.
#define MQTT_BROKER_HOST        "192.168.1.204"
#define MQTT_BROKER_PORT        1883
#define MQTT_USERNAME_STR       ""
#define MQTT_PASSWORD_STR       ""
#define MQTT_BUFFER_SIZE        1024     // bytes — must fit largest JSON payload
#define MQTT_KEEPALIVE_SEC      15

// ==============================================================================
// SECTION 3: CONFIGURATION — ACTUATOR PIN MAP
// ==============================================================================
// Source: NICEGAS NODE 4 wiring diagram (ESP32 DevKit V1)
//
// VERIFY AGAINST ACTUAL WIRING BEFORE ENERGIZING ACTUATORS
//
// | Signal        | ESP32 Pin | GPIO | Hardware Target            |
// |:------------- |:--------- |:---- |:-------------------------- |
// | Solenoid Ctrl | D5        | 14   | DC 3V Gas Solenoid Valve   |
// | Relay Ch.1    | D18       | 18   | Relay 5V Optocoupler Ch.1  |
// | Relay Ch.2    | D19       | 19   | Relay 5V Optocoupler Ch.2  |
// | Relay Ch.3    | D21       | 21   | Relay 5V Optocoupler Ch.3  |
// | Relay Ch.4    | D22       | 22   | Relay 5V Optocoupler Ch.4  |
//
#define PIN_SOLENOID    14   // D5  / GPIO14
#define PIN_RELAY_1     18   // D18 / GPIO18
#define PIN_RELAY_2     19   // D19 / GPIO19
#define PIN_RELAY_3     21   // D21 / GPIO21
#define PIN_RELAY_4     22   // D22 / GPIO22

// ==============================================================================
// SECTION 4: CONFIGURATION — ACTUATOR POLARITY
// ==============================================================================

// Set true if relay module energizes when GPIO is LOW (common optocoupler modules)
// Set false if relay energizes when GPIO is HIGH
#define RELAY_ACTIVE_LOW        true

// Set true if solenoid opens when GPIO is HIGH
// Set false if solenoid opens when GPIO is LOW
#define SOLENOID_ACTIVE_HIGH    true

// ==============================================================================
// SECTION 5: CONFIGURATION — PEER NODE IDENTITIES
// ==============================================================================

#define NODE_DIGESTER_ID        "DIGESTER-01"
#define NODE_PURIFY_ID          "PURIFY-01"
#define NODE_COMP_ID            "COMP-01"
#define NODE_DIGESTER_COMP      "biodigester"
#define NODE_PURIFY_COMP        "purifikasi"
#define NODE_COMP_COMP          "kompresi"

// ==============================================================================
// SECTION 6: CONFIGURATION — TIMING & SAFETY TIMEOUTS
// ==============================================================================

#define STATUS_PUBLISH_INTERVAL_MS      10000   // Publish status heartbeat every 10s
#define MQTT_RECONNECT_INTERVAL_MS       5000   // Retry MQTT connect every 5s
#define TELEMETRY_STALE_TIMEOUT_MS      30000   // Node data older than 30s = stale
#define NTP_VALID_EPOCH_MIN     1700000000UL    // ~2023-11-01 UTC epoch minimum
#define WDT_TIMEOUT_SEC                   30    // Hardware watchdog timeout

// NTP Servers (UTC, no timezone offset)
#define NTP_SERVER_1    "pool.ntp.org"
#define NTP_SERVER_2    "time.nist.gov"
#define NTP_SERVER_3    "time.google.com"

// ==============================================================================
// SECTION 7: CONFIGURATION — AI + OPERATION FLAGS
// ==============================================================================

// EDGE_AI_DUMMY_MODE = true  -> use deterministic rule engine (no ML model)
// EDGE_AI_DUMMY_MODE = false -> future: plug in actual edge inference runtime
#define EDGE_AI_DUMMY_MODE      true

// ACTUATOR_TEST_MODE: explicitly enables test sequences. Does NOT bypass interlock.
// Default MUST be false for production/deployment.
#define ACTUATOR_TEST_MODE      false

// ==============================================================================
// SECTION 8: OPERATING MODES
// ==============================================================================

enum OperatingMode : uint8_t {
    MODE_SAFE   = 0,    // Boot default. All actuators OFF. All ON commands rejected.
    MODE_MANUAL = 1,    // Explicit operator command. Safety interlock still applies.
    MODE_AUTO   = 2,    // Decision engine drives actuators. Requires full interlock.
};

const char* modeStr(OperatingMode m) {
    switch (m) {
        case MODE_SAFE:   return "safe";
        case MODE_MANUAL: return "manual";
        case MODE_AUTO:   return "auto";
        default:          return "unknown";
    }
}

// ==============================================================================
// SECTION 9: ACTUATOR STATE STRUCT
// ==============================================================================

struct ActuatorState {
    bool solenoid = false;
    bool relay1   = false;
    bool relay2   = false;
    bool relay3   = false;
    bool relay4   = false;
};

// ==============================================================================
// SECTION 10: SYSTEM STATE STRUCT
// ==============================================================================

struct SystemState {
    OperatingMode mode          = MODE_SAFE;
    bool          armed         = false;
    bool          emergencyStop = false;
    bool          bootComplete  = false;
    bool          ntpSynced     = false;
    bool          mqttOnline    = false;
    ActuatorState actuator;
    String        lastCmdId     = "";  // Last processed command_id (dedup)
};

// ==============================================================================
// SECTION 11: TELEMETRY CACHE (from Node 1/2/3)
// ==============================================================================

struct NodeTelemetry {
    bool     received      = false;
    uint32_t lastSeenMs    = 0;
    String   nodeStatus    = "";
    String   timestamp     = "";
    float    temperature   = 0.0f;
    float    pressure      = 0.0f;
    float    methane       = 0.0f;
    float    gas_flow      = 0.0f;
    float    ph            = 0.0f;
    float    h2s           = 0.0f;
    float    co2           = 0.0f;
    float    motor_current = 0.0f;

    bool isStale() const {
        if (!received) return true;
        return ((millis() - lastSeenMs) > TELEMETRY_STALE_TIMEOUT_MS);
    }
};

// Explicit prototype (fixes "NodeTelemetry was not declared in this scope" /
// "declared void" build errors): the Arduino builder auto-generates function
// prototypes and inserts them near the very top of the .ino, above this
// struct. Its auto-generated prototype for parseTelemetryToCache() then
// references NodeTelemetry before it exists. Declaring the prototype
// ourselves here (after NodeTelemetry is defined) gives the builder a
// matching signature it recognizes, so it skips generating its own broken
// one.
void parseTelemetryToCache(NodeTelemetry& cache, const JsonDocument& doc);

// ==============================================================================
// SECTION 12: EDGE DECISION STRUCT
// ==============================================================================

struct EdgeDecision {
    String  decision_id;
    String  timestamp;
    String  source;       // "rule_engine" | "edge_ai"
    String  target;       // "solenoid" | "relay_1" | ...
    String  action;       // "on" | "off"
    String  reason;
    float   confidence;   // 0.0 - 1.0 (rule-based: 1.0)
    String  expires_at;
};

// ==============================================================================
// SECTION 13: GLOBAL OBJECTS & STATE
// ==============================================================================

WiFiClient   espWiFiClient;
PubSubClient mqttClient(espWiFiClient);

SystemState   sysState;
NodeTelemetry cacheDIGESTER;
NodeTelemetry cachePURIFY;
NodeTelemetry cacheCOMP;

bool     wasWifiConnected  = false;
bool     wasMqttConnected  = false;
uint32_t lastStatusPublish = 0;
uint32_t lastMqttReconnect = 0;

// ==============================================================================
// SECTION 14: ACTUATOR ABSTRACTION
// (Use ONLY these functions — never call digitalWrite directly on actuator pins)
// ==============================================================================

void _relayPinWrite(uint8_t pin, bool activate) {
    if (RELAY_ACTIVE_LOW) {
        digitalWrite(pin, activate ? LOW : HIGH);
    } else {
        digitalWrite(pin, activate ? HIGH : LOW);
    }
}

void _solenoidPinWrite(bool activate) {
    if (SOLENOID_ACTIVE_HIGH) {
        digitalWrite(PIN_SOLENOID, activate ? HIGH : LOW);
    } else {
        digitalWrite(PIN_SOLENOID, activate ? LOW : HIGH);
    }
}

void solenoidOn() {
    _solenoidPinWrite(true);
    sysState.actuator.solenoid = true;
}

void solenoidOff() {
    _solenoidPinWrite(false);
    sysState.actuator.solenoid = false;
}

void relayOn(uint8_t channel) {
    switch (channel) {
        case 1: _relayPinWrite(PIN_RELAY_1, true);  sysState.actuator.relay1 = true;  break;
        case 2: _relayPinWrite(PIN_RELAY_2, true);  sysState.actuator.relay2 = true;  break;
        case 3: _relayPinWrite(PIN_RELAY_3, true);  sysState.actuator.relay3 = true;  break;
        case 4: _relayPinWrite(PIN_RELAY_4, true);  sysState.actuator.relay4 = true;  break;
        default: Serial.println("[ERROR] relayOn: invalid channel"); break;
    }
}

void relayOff(uint8_t channel) {
    switch (channel) {
        case 1: _relayPinWrite(PIN_RELAY_1, false); sysState.actuator.relay1 = false; break;
        case 2: _relayPinWrite(PIN_RELAY_2, false); sysState.actuator.relay2 = false; break;
        case 3: _relayPinWrite(PIN_RELAY_3, false); sysState.actuator.relay3 = false; break;
        case 4: _relayPinWrite(PIN_RELAY_4, false); sysState.actuator.relay4 = false; break;
        default: Serial.println("[ERROR] relayOff: invalid channel"); break;
    }
}

void allRelaysOff() {
    relayOff(1); relayOff(2); relayOff(3); relayOff(4);
}

void setAllActuatorsOff() {
    solenoidOff();
    allRelaysOff();
    Serial.println("[ACTUATOR] ALL -> OFF");
}

// ==============================================================================
// SECTION 15: EMERGENCY STOP
// ==============================================================================

void enterEmergencyStop(const char* reason) {
    sysState.emergencyStop = true;
    sysState.mode = MODE_SAFE;
    setAllActuatorsOff();
    Serial.printf("[SAFETY] !!! EMERGENCY STOP: %s !!!\n", reason);
}

// IMPORTANT: Emergency stop reset is explicit. NOT auto-triggered by any event.
void clearEmergencyStop() {
    sysState.emergencyStop = false;
    Serial.println("[SAFETY] Emergency stop cleared by operator command.");
}

// ==============================================================================
// SECTION 16: SAFETY INTERLOCK
// All actuator ON commands MUST pass this before execution.
// ==============================================================================

bool safetyInterlockPassed(bool requiresAutoMode) {
    if (sysState.emergencyStop) {
        Serial.println("[SAFETY] Interlock FAIL: emergency_stop_active");
        return false;
    }
    if (!sysState.bootComplete) {
        Serial.println("[SAFETY] Interlock FAIL: boot_not_complete");
        return false;
    }
    if (!sysState.mqttOnline) {
        Serial.println("[SAFETY] Interlock FAIL: mqtt_offline");
        return false;
    }
    if (requiresAutoMode) {
        // AUTO mode requires valid NTP timestamp
        if (!sysState.ntpSynced) {
            Serial.println("[SAFETY] Interlock FAIL: ntp_not_synced (AUTO requires valid clock)");
            return false;
        }
        // AUTO mode requires fresh telemetry from all nodes
        if (cacheDIGESTER.isStale()) {
            Serial.println("[SAFETY] Interlock FAIL: digester_telemetry_stale");
            return false;
        }
        if (cachePURIFY.isStale()) {
            Serial.println("[SAFETY] Interlock FAIL: purify_telemetry_stale");
            return false;
        }
        if (cacheCOMP.isStale()) {
            Serial.println("[SAFETY] Interlock FAIL: comp_telemetry_stale");
            return false;
        }
    }
    Serial.println("[SAFETY] Interlock PASS");
    return true;
}

// ==============================================================================
// SECTION 17: NTP / TIMESTAMP UTILITIES
// ==============================================================================

bool isTimeValid() {
    return (time(nullptr) > (time_t)NTP_VALID_EPOCH_MIN);
}

String getISO8601UTC() {
    struct tm timeinfo;
    time_t now = time(nullptr);
    gmtime_r(&now, &timeinfo);
    char buf[32];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
    return String(buf);
}

// Portable replacement for timegm(). Not every ESP32 Arduino core version
// declares timegm() in <time.h> (it's a BSD/GNU extension, not standard C),
// which is why the build fails with "timegm was not declared in this scope".
// This computes UTC seconds-since-epoch directly from the calendar fields,
// so it works regardless of what the underlying core/newlib exposes.
static time_t timegmPortable(struct tm* tmUtc) {
    static const int cumDaysNonLeap[] = {0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334};
    int year = tmUtc->tm_year + 1900;
    int mon  = tmUtc->tm_mon; // 0-11

    auto isLeapYear = [](int y) {
        return (y % 4 == 0 && y % 100 != 0) || (y % 400 == 0);
    };

    long days = 0;
    if (year >= 1970) {
        for (int y = 1970; y < year; y++) days += isLeapYear(y) ? 366 : 365;
    } else {
        for (int y = year; y < 1970; y++) days -= isLeapYear(y) ? 366 : 365;
    }
    days += cumDaysNonLeap[mon];
    if (isLeapYear(year) && mon > 1) days += 1; // Feb 29 already passed this year
    days += (tmUtc->tm_mday - 1);

    long seconds = days * 86400L + tmUtc->tm_hour * 3600L
                 + tmUtc->tm_min * 60L + tmUtc->tm_sec;
    return (time_t)seconds;
}

// Parse ISO8601 UTC string to time_t.
// Returns 0 on failure (treat as invalid).
time_t parseISO8601UTC(const String& ts) {
    if (ts.length() < 19) return 0;
    struct tm t;
    memset(&t, 0, sizeof(t));
    // Format: YYYY-MM-DDTHH:MM:SSZ
    t.tm_year  = ts.substring(0,  4).toInt() - 1900;
    t.tm_mon   = ts.substring(5,  7).toInt() - 1;
    t.tm_mday  = ts.substring(8, 10).toInt();
    t.tm_hour  = ts.substring(11, 13).toInt();
    t.tm_min   = ts.substring(14, 16).toInt();
    t.tm_sec   = ts.substring(17, 19).toInt();
    t.tm_isdst = 0;
    // timegmPortable() = our own timegm(): treats input as UTC, not local time
    return timegmPortable(&t);
}

// ==============================================================================
// SECTION 18: MQTT TOPIC BUILDERS
// Topics are ALWAYS built from PROJECT_NAME + DEVICE_ID macros.
// DO NOT hardcode topics anywhere else.
// ==============================================================================

String buildTopic(const char* category, const char* sub) {
    return String("nicegas/") + AGENT_PROJECT_NAME + "/"
           + AGENT_DEVICE_ID + "/" + category + "/" + sub;
}

inline String topicConnection()      { return buildTopic("status",  "connection"); }
inline String topicEdgeAiStatus()    { return buildTopic("status",  "edge-ai"); }
inline String topicActuatorStatus()  { return buildTopic("status",  "actuator"); }
inline String topicCommandActuator() { return buildTopic("command", "actuator"); }
inline String topicCommandDecision() { return buildTopic("command", "decision"); }
inline String topicEventActuator()   { return buildTopic("event",   "actuator"); }

// Peer node telemetry topics (for subscription)
String topicNodeTelemetry(const char* deviceId, const char* component) {
    return String("nicegas/") + AGENT_PROJECT_NAME + "/"
           + deviceId + "/telemetry/" + component;
}

String getMqttClientId() {
    uint32_t chipId = (uint32_t)ESP.getEfuseMac();
    char buf[48];
    snprintf(buf, sizeof(buf), "%s_%06X", AGENT_DEVICE_ID, chipId & 0xFFFFFF);
    return String(buf);
}

// ==============================================================================
// SECTION 19: MQTT PUBLISH HELPERS
// ==============================================================================

void publishConnectionStatus(bool online) {
    JsonDocument doc;
    doc["device_id"]   = AGENT_DEVICE_ID;
    doc["device_name"] = AGENT_DEVICE_NAME;
    doc["status"]      = online ? "online" : "offline";
    if (online && isTimeValid()) {
        doc["timestamp"] = getISO8601UTC();
    }
    String payload;
    serializeJson(doc, payload);
    bool ok = mqttClient.publish(topicConnection().c_str(), payload.c_str(), /*retain=*/true);
    Serial.printf("[STATUS] Connection '%s' published %s\n",
                  online ? "online" : "offline", ok ? "OK" : "FAILED");
}

void publishEdgeAiStatus() {
    JsonDocument doc;
    doc["device_id"]      = AGENT_DEVICE_ID;
    doc["status"]         = "online";
    doc["mode"]           = EDGE_AI_DUMMY_MODE ? "dummy_rule_engine" : "edge_ai";
    doc["inference"]      = EDGE_AI_DUMMY_MODE ? "not_loaded" : "ready";
    doc["operating_mode"] = modeStr(sysState.mode);
    doc["armed"]          = sysState.armed;
    doc["emergency_stop"] = sysState.emergencyStop;
    if (isTimeValid()) { doc["timestamp"] = getISO8601UTC(); }
    String payload;
    serializeJson(doc, payload);
    bool ok = mqttClient.publish(topicEdgeAiStatus().c_str(), payload.c_str(), /*retain=*/true);
    Serial.printf("[EDGE-AI] Status published %s\n", ok ? "OK" : "FAILED");
}

void publishActuatorStatus() {
    JsonDocument doc;
    doc["device_id"]      = AGENT_DEVICE_ID;
    doc["operating_mode"] = modeStr(sysState.mode);
    doc["emergency_stop"] = sysState.emergencyStop;
    doc["solenoid"]       = sysState.actuator.solenoid ? "on" : "off";
    doc["relay_1"]        = sysState.actuator.relay1   ? "on" : "off";
    doc["relay_2"]        = sysState.actuator.relay2   ? "on" : "off";
    doc["relay_3"]        = sysState.actuator.relay3   ? "on" : "off";
    doc["relay_4"]        = sysState.actuator.relay4   ? "on" : "off";
    if (isTimeValid()) { doc["timestamp"] = getISO8601UTC(); }
    String payload;
    serializeJson(doc, payload);
    bool ok = mqttClient.publish(topicActuatorStatus().c_str(), payload.c_str(), /*retain=*/true);
    if (!ok) { Serial.println("[MQTT] Actuator status publish FAILED"); }
}

void publishCommandAck(const String& cmdId, const String& target, const String& action,
                       bool accepted, const char* reason = nullptr) {
    JsonDocument doc;
    doc["event"]      = "command_ack";
    doc["command_id"] = cmdId.length() > 0 ? cmdId : "unknown";
    doc["status"]     = accepted ? "accepted" : "rejected";
    if (target.length() > 0) { doc["target"] = target; }
    if (action.length() > 0) { doc["action"] = action; }
    if (!accepted && reason)  { doc["reason"] = reason; }
    if (isTimeValid()) { doc["timestamp"] = getISO8601UTC(); }
    String payload;
    serializeJson(doc, payload);
    bool ok = mqttClient.publish(topicEventActuator().c_str(), payload.c_str(), /*retain=*/false);
    Serial.printf("[COMMAND] ACK cmd='%s' %s%s %s\n",
                  cmdId.c_str(),
                  accepted ? "ACCEPTED" : "REJECTED",
                  (!accepted && reason) ? (String(" reason=") + reason).c_str() : "",
                  ok ? "" : "(publish FAILED)");
}

void publishRejectionEvent(const String& cmdId, const char* reason) {
    JsonDocument doc;
    doc["event"]      = "actuator_command_rejected";
    doc["command_id"] = cmdId;
    doc["reason"]     = reason;
    doc["device_id"]  = AGENT_DEVICE_ID;
    if (isTimeValid()) { doc["timestamp"] = getISO8601UTC(); }
    String payload;
    serializeJson(doc, payload);
    mqttClient.publish(topicEventActuator().c_str(), payload.c_str(), false);
}

// ==============================================================================
// SECTION 20: ACTUATOR EXECUTOR
// Final step in the pipeline — only called after all validation passes.
// ==============================================================================

bool executeActuator(const String& target, const String& action) {
    bool activate = (action == "on");
    if (target == "solenoid") {
        if (activate) solenoidOn(); else solenoidOff();
    } else if (target == "relay_1") {
        if (activate) relayOn(1); else relayOff(1);
    } else if (target == "relay_2") {
        if (activate) relayOn(2); else relayOff(2);
    } else if (target == "relay_3") {
        if (activate) relayOn(3); else relayOff(3);
    } else if (target == "relay_4") {
        if (activate) relayOn(4); else relayOff(4);
    } else if (target == "all_relays") {
        if (activate) { relayOn(1); relayOn(2); relayOn(3); relayOn(4); }
        else          { allRelaysOff(); }
    } else {
        Serial.printf("[ERROR] executeActuator: unknown target '%s'\n", target.c_str());
        return false;
    }
    Serial.printf("[ACTUATOR] %s -> %s\n", target.c_str(), activate ? "ON" : "OFF");
    return true;
}

// ==============================================================================
// SECTION 21: COMMAND VALIDATION + PROCESSING PIPELINE
//
// Pipeline:
//   JSON parsed -> Field validation -> Whitelist check -> Dedup check ->
//   Expiry check -> Mode check -> Safety Interlock -> Execute -> ACK
// ==============================================================================

// Whitelists
bool isValidTarget(const String& t) {
    return (t == "solenoid" || t == "relay_1" || t == "relay_2" ||
            t == "relay_3"  || t == "relay_4" || t == "all_relays");
}

bool isValidAction(const String& a) {
    return (a == "on" || a == "off");
}

bool isValidMode(const String& m) {
    return (m == "manual" || m == "auto" || m == "safe");
}

void processActuatorCommand(const JsonDocument& doc) {

    // --- Extract fields ---
    const char* cCmdId    = doc["command_id"];
    const char* cTs       = doc["timestamp"];
    const char* cMode     = doc["mode"];
    const char* cTarget   = doc["target"];
    const char* cAction   = doc["action"];
    const char* cExpires  = doc["expires_at"];

    String cmdId   = cCmdId   ? String(cCmdId)   : "";
    String ts      = cTs      ? String(cTs)       : "";
    String mode    = cMode    ? String(cMode)     : "";
    String target  = cTarget  ? String(cTarget)   : "";
    String action  = cAction  ? String(cAction)   : "";
    String expires = cExpires ? String(cExpires)  : "";

    Serial.printf("[COMMAND] Received id='%s' target='%s' action='%s' mode='%s'\n",
                  cmdId.c_str(), target.c_str(), action.c_str(), mode.c_str());

    // --- Required field presence ---
    if (cmdId.isEmpty()) {
        Serial.println("[COMMAND] REJECTED: missing command_id");
        publishCommandAck("", target, action, false, "missing_command_id");
        return;
    }
    if (ts.isEmpty()) {
        Serial.println("[COMMAND] REJECTED: missing timestamp");
        publishCommandAck(cmdId, target, action, false, "missing_timestamp");
        return;
    }
    if (expires.isEmpty()) {
        Serial.println("[COMMAND] REJECTED: missing expires_at");
        publishCommandAck(cmdId, target, action, false, "missing_expires_at");
        return;
    }

    // --- Whitelist validation ---
    if (!isValidTarget(target)) {
        Serial.printf("[COMMAND] REJECTED: unknown target '%s'\n", target.c_str());
        publishCommandAck(cmdId, target, action, false, "unknown_target");
        return;
    }
    if (!isValidAction(action)) {
        Serial.printf("[COMMAND] REJECTED: unknown action '%s'\n", action.c_str());
        publishCommandAck(cmdId, target, action, false, "unknown_action");
        return;
    }
    if (!isValidMode(mode)) {
        Serial.printf("[COMMAND] REJECTED: unknown mode '%s'\n", mode.c_str());
        publishCommandAck(cmdId, target, action, false, "unknown_mode");
        return;
    }

    // --- Duplicate command_id check ---
    if (cmdId == sysState.lastCmdId) {
        Serial.printf("[COMMAND] REJECTED: duplicate command_id '%s'\n", cmdId.c_str());
        publishCommandAck(cmdId, target, action, false, "duplicate_command_id");
        return;
    }

    // --- Expiry check (requires NTP for AUTO; accept MANUAL without NTP but warn) ---
    if (isTimeValid()) {
        time_t expT = parseISO8601UTC(expires);
        if (expT > 0 && time(nullptr) > expT) {
            Serial.println("[COMMAND] REJECTED: command expired");
            publishCommandAck(cmdId, target, action, false, "command_expired");
            return;
        }
    } else {
        if (mode == "auto") {
            Serial.println("[COMMAND] REJECTED: NTP not valid, AUTO blocked");
            publishCommandAck(cmdId, target, action, false, "ntp_not_synced");
            return;
        }
        Serial.println("[COMMAND] WARNING: NTP not synced, expiry check skipped (manual cmd)");
    }

    // --- System mode gate ---
    if (mode == "auto" && sysState.mode != MODE_AUTO) {
        Serial.println("[COMMAND] REJECTED: system is not in AUTO mode");
        publishCommandAck(cmdId, target, action, false, "system_not_in_auto_mode");
        return;
    }
    if (mode == "manual" && sysState.mode == MODE_SAFE) {
        Serial.println("[COMMAND] REJECTED: system is in SAFE mode");
        publishCommandAck(cmdId, target, action, false, "system_in_safe_mode");
        return;
    }

    // --- Safety Interlock (all ON commands must pass; OFF always passes if boot ok) ---
    bool isAutoCmd = (mode == "auto");
    bool requiresInterlock = (action == "on");
    if (requiresInterlock) {
        if (!safetyInterlockPassed(isAutoCmd)) {
            Serial.printf("[COMMAND] REJECTED: safety interlock failed\n");
            publishCommandAck(cmdId, target, action, false, "safety_interlock_failed");
            publishRejectionEvent(cmdId, "safety_interlock_failed");
            return;
        }
    } else {
        // OFF commands: only check boot + emergency stop
        if (!sysState.bootComplete) {
            publishCommandAck(cmdId, target, action, false, "boot_not_complete");
            return;
        }
    }

    // --- Execute ---
    bool ok = executeActuator(target, action);
    if (ok) {
        sysState.lastCmdId = cmdId;
        publishCommandAck(cmdId, target, action, true);
        publishActuatorStatus();
    } else {
        publishCommandAck(cmdId, target, action, false, "execution_failed");
    }
}

// ==============================================================================
// SECTION 22: EDGE AI / DECISION ENGINE
// Currently: deterministic rule engine (DUMMY MODE).
// Future: integrate edge AI runtime result here, call processActuatorCommand().
// ==============================================================================

void runDecisionEngine() {
#if EDGE_AI_DUMMY_MODE
    // RULE 1: Emergency stop overrides everything
    if (sysState.emergencyStop) {
        bool anyOn = sysState.actuator.solenoid || sysState.actuator.relay1 ||
                     sysState.actuator.relay2   || sysState.actuator.relay3 ||
                     sysState.actuator.relay4;
        if (anyOn) {
            Serial.println("[EDGE-AI] Rule: Emergency stop active -> force all OFF");
            setAllActuatorsOff();
            publishActuatorStatus();
        }
        return;
    }

    // RULE 2: SAFE mode forces all OFF
    if (sysState.mode == MODE_SAFE) {
        bool anyOn = sysState.actuator.solenoid || sysState.actuator.relay1 ||
                     sysState.actuator.relay2   || sysState.actuator.relay3 ||
                     sysState.actuator.relay4;
        if (anyOn) {
            Serial.println("[EDGE-AI] Rule: MODE_SAFE -> force all OFF");
            setAllActuatorsOff();
            publishActuatorStatus();
        }
        return;
    }

    // RULE 3: Stale data in AUTO mode = block (already enforced by interlock,
    //         but also enforce in engine as defense-in-depth)
    if (sysState.mode == MODE_AUTO) {
        if (cacheDIGESTER.isStale() || cachePURIFY.isStale() || cacheCOMP.isStale()) {
            // Data is stale — keep current safe state, do not issue new ON commands
            return;
        }
        // Future: pass cached telemetry to ML inference here
        // EdgeDecision decision = runMLInference(cacheDIGESTER, cachePURIFY, cacheCOMP);
        // if (decision is valid) -> processActuatorCommand(decision);
    }
    // In MANUAL mode: no autonomous decisions — wait for explicit MQTT command
#endif
}

// ==============================================================================
// SECTION 23: TELEMETRY CACHE PARSING
// Telemetry from Node 1/2/3 is stored here ONLY.
// No direct actuator action is taken from telemetry.
// ==============================================================================

void parseTelemetryToCache(NodeTelemetry& cache, const JsonDocument& doc) {
    cache.received    = true;
    cache.lastSeenMs  = millis();
    cache.nodeStatus  = doc["status"]    | "";
    cache.timestamp   = doc["timestamp"] | "";

    JsonObjectConst m = doc["metrics"];
    if (!m.isNull()) {
        if (m.containsKey("temperature"))   cache.temperature   = m["temperature"]["v"]   | 0.0f;
        if (m.containsKey("pressure"))      cache.pressure      = m["pressure"]["v"]      | 0.0f;
        if (m.containsKey("methane"))       cache.methane       = m["methane"]["v"]       | 0.0f;
        if (m.containsKey("gas_flow"))      cache.gas_flow      = m["gas_flow"]["v"]      | 0.0f;
        if (m.containsKey("ph"))            cache.ph            = m["ph"]["v"]            | 0.0f;
        if (m.containsKey("h2s"))           cache.h2s           = m["h2s"]["v"]           | 0.0f;
        if (m.containsKey("co2"))           cache.co2           = m["co2"]["v"]           | 0.0f;
        if (m.containsKey("motor_current")) cache.motor_current = m["motor_current"]["v"] | 0.0f;
    }
}

// ==============================================================================
// SECTION 24: MQTT MESSAGE CALLBACK (message router)
// ==============================================================================

void onMqttMessage(char* topicC, byte* payloadRaw, unsigned int length) {
    String topic = String(topicC);

    // Safety gate: retained messages that arrive before boot completes are silently
    // ignored to prevent actuator activation from stale retained commands.
    if (!sysState.bootComplete) {
        Serial.printf("[MQTT] Ignoring message on '%s' — boot not complete\n", topic.c_str());
        return;
    }

    // Build payload string
    String payloadStr;
    payloadStr.reserve(length + 1);
    for (unsigned int i = 0; i < length; i++) { payloadStr += (char)payloadRaw[i]; }

    // Parse JSON
    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, payloadStr);
    if (err) {
        Serial.printf("[ERROR] JSON parse failed on '%s': %s — rejected\n",
                      topic.c_str(), err.c_str());
        return;
    }

    // Route messages by topic
    if (topic == topicCommandActuator() || topic == topicCommandDecision()) {
        processActuatorCommand(doc);
        return;
    }

    // Node 1: DIGESTER-01 telemetry
    if (topic == topicNodeTelemetry(NODE_DIGESTER_ID, NODE_DIGESTER_COMP)) {
        parseTelemetryToCache(cacheDIGESTER, doc);
        Serial.printf("[EDGE-AI] DIGESTER cached: T=%.1fC CH4=%.1f%% P=%.2fbar\n",
                      cacheDIGESTER.temperature, cacheDIGESTER.methane, cacheDIGESTER.pressure);
        return;
    }

    // Node 2: PURIFY-01 telemetry
    if (topic == topicNodeTelemetry(NODE_PURIFY_ID, NODE_PURIFY_COMP)) {
        parseTelemetryToCache(cachePURIFY, doc);
        Serial.printf("[EDGE-AI] PURIFY cached: CH4=%.1f%% H2S=%.1fppm P=%.2fbar\n",
                      cachePURIFY.methane, cachePURIFY.h2s, cachePURIFY.pressure);
        return;
    }

    // Node 3: COMP-01 telemetry
    if (topic == topicNodeTelemetry(NODE_COMP_ID, NODE_COMP_COMP)) {
        parseTelemetryToCache(cacheCOMP, doc);
        Serial.printf("[EDGE-AI] COMP cached: P=%.1fbar T=%.1fC I=%.1fA\n",
                      cacheCOMP.pressure, cacheCOMP.temperature, cacheCOMP.motor_current);
        return;
    }

    Serial.printf("[MQTT] Unknown topic '%s' — ignored\n", topic.c_str());
}

// ==============================================================================
// SECTION 25: MQTT CONNECT + SUBSCRIBE
// ==============================================================================

void connectMQTT() {
    String clientId = getMqttClientId();
    String statusTopic = topicConnection();

    // Build LWT payload
    JsonDocument willDoc;
    willDoc["device_id"]   = AGENT_DEVICE_ID;
    willDoc["device_name"] = AGENT_DEVICE_NAME;
    willDoc["status"]      = "offline";
    String willPayload;
    serializeJson(willDoc, willPayload);

    Serial.printf("[MQTT] Connecting to %s:%d as %s...\n",
                  MQTT_BROKER_HOST, MQTT_BROKER_PORT, clientId.c_str());

    bool ok = false;
    const char* usr = MQTT_USERNAME_STR;
    const char* pwd = MQTT_PASSWORD_STR;

    if (strlen(usr) > 0) {
        ok = mqttClient.connect(clientId.c_str(), usr, pwd,
                                statusTopic.c_str(), 1, true, willPayload.c_str());
    } else {
        ok = mqttClient.connect(clientId.c_str(),
                                statusTopic.c_str(), 1, true, willPayload.c_str());
    }

    if (ok) {
        Serial.println("[MQTT] Connected");
        wasMqttConnected    = true;
        sysState.mqttOnline = true;

        // Subscribe: own command topics
        mqttClient.subscribe(topicCommandActuator().c_str(), 1);
        mqttClient.subscribe(topicCommandDecision().c_str(), 1);
        Serial.println("[MQTT] Subscribed: command/actuator, command/decision");

        // Subscribe: peer node telemetry
        mqttClient.subscribe(
            topicNodeTelemetry(NODE_DIGESTER_ID, NODE_DIGESTER_COMP).c_str(), 1);
        mqttClient.subscribe(
            topicNodeTelemetry(NODE_PURIFY_ID, NODE_PURIFY_COMP).c_str(), 1);
        mqttClient.subscribe(
            topicNodeTelemetry(NODE_COMP_ID, NODE_COMP_COMP).c_str(), 1);
        Serial.println("[MQTT] Subscribed: Node 1/2/3 telemetry");

        // Publish online statuses (retained)
        publishConnectionStatus(true);
        publishEdgeAiStatus();
        publishActuatorStatus();

    } else {
        sysState.mqttOnline = false;
        Serial.printf("[MQTT] Connect failed, rc=%d. Retry in %u ms\n",
                      mqttClient.state(), MQTT_RECONNECT_INTERVAL_MS);
    }
}

// ==============================================================================
// SECTION 26: BOOT SELF-TEST
// Must not energize any actuator. Reports and halts on inconsistency.
// ==============================================================================

void runBootSelfTest() {
    Serial.println("[BOOT] Running self-test...");

    // Verify actuator state struct matches actual GPIO state
    bool structAllOff = (!sysState.actuator.solenoid &&
                         !sysState.actuator.relay1   &&
                         !sysState.actuator.relay2   &&
                         !sysState.actuator.relay3   &&
                         !sysState.actuator.relay4);

    if (!structAllOff) {
        Serial.println("[BOOT] SELF-TEST FAIL: Actuator state struct inconsistency on boot");
        enterEmergencyStop("boot_selftest_state_inconsistency");
        return;
    }

    Serial.println("[BOOT] Self-test: Actuator state OK (all OFF)");
    Serial.printf("[BOOT] Self-test: Pins SOLENOID=%d R1=%d R2=%d R3=%d R4=%d\n",
                  PIN_SOLENOID, PIN_RELAY_1, PIN_RELAY_2, PIN_RELAY_3, PIN_RELAY_4);
    Serial.printf("[BOOT] Self-test: RELAY_ACTIVE_LOW=%s SOLENOID_ACTIVE_HIGH=%s\n",
                  RELAY_ACTIVE_LOW ? "true" : "false",
                  SOLENOID_ACTIVE_HIGH ? "true" : "false");
    Serial.printf("[BOOT] Self-test: AI_MODE=%s\n",
                  EDGE_AI_DUMMY_MODE ? "DUMMY_RULE_ENGINE" : "EDGE_AI");
    Serial.println("[BOOT] Self-test: PASSED");
}

// ==============================================================================
// SECTION 27: SETUP
// Order: Actuator safe-off FIRST -> System state -> WDT -> NTP -> WiFi -> MQTT ->
//        Self-test -> Mark boot complete
// ==============================================================================

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n==================================================");
    Serial.println("  NICEGAS — ESP4: EDGE AI + ACTUATOR NODE        ");
    Serial.println("==================================================");
    Serial.printf("[BOOT] Firmware   : %s\n", AGENT_FIRMWARE_VERSION);
    Serial.printf("[BOOT] Device ID  : %s\n", AGENT_DEVICE_ID);
    Serial.printf("[BOOT] Project    : %s\n", AGENT_PROJECT_NAME);
    Serial.printf("[BOOT] Component  : %s\n", AGENT_COMPONENT);
    Serial.printf("[BOOT] AI Mode    : %s\n",
                  EDGE_AI_DUMMY_MODE ? "DUMMY_RULE_ENGINE" : "EDGE_AI");
    Serial.printf("[BOOT] Telemetry  : nicegas/%s/%s/...\n",
                  AGENT_PROJECT_NAME, AGENT_DEVICE_ID);
    Serial.println("--------------------------------------------------");

    // =========================================================
    // STEP 1: ACTUATOR SAFE-OFF — MUST BE FIRST
    // Drive all actuator outputs to safe OFF state BEFORE any
    // other initialization to prevent boot transients.
    // =========================================================

    // Pre-drive pins before calling pinMode (avoids brief floating/wrong state)
    if (RELAY_ACTIVE_LOW) {
        // HIGH = relay de-energized (ACTIVE_LOW modules)
        gpio_set_level((gpio_num_t)PIN_RELAY_1, 1);
        gpio_set_level((gpio_num_t)PIN_RELAY_2, 1);
        gpio_set_level((gpio_num_t)PIN_RELAY_3, 1);
        gpio_set_level((gpio_num_t)PIN_RELAY_4, 1);
    } else {
        gpio_set_level((gpio_num_t)PIN_RELAY_1, 0);
        gpio_set_level((gpio_num_t)PIN_RELAY_2, 0);
        gpio_set_level((gpio_num_t)PIN_RELAY_3, 0);
        gpio_set_level((gpio_num_t)PIN_RELAY_4, 0);
    }
    // Solenoid: safe = de-energized
    if (SOLENOID_ACTIVE_HIGH) {
        gpio_set_level((gpio_num_t)PIN_SOLENOID, 0);  // LOW = closed
    } else {
        gpio_set_level((gpio_num_t)PIN_SOLENOID, 1);
    }

    // Now set as outputs; state already established above
    pinMode(PIN_SOLENOID, OUTPUT);
    pinMode(PIN_RELAY_1,  OUTPUT);
    pinMode(PIN_RELAY_2,  OUTPUT);
    pinMode(PIN_RELAY_3,  OUTPUT);
    pinMode(PIN_RELAY_4,  OUTPUT);

    // Confirm safe state via abstraction layer (updates state struct)
    solenoidOff(); relayOff(1); relayOff(2); relayOff(3); relayOff(4);

    Serial.println("[SAFETY] All actuators initialized -> OFF");

    // =========================================================
    // STEP 2: SYSTEM STATE INIT
    // =========================================================
    sysState.mode          = MODE_SAFE;
    sysState.armed         = false;
    sysState.emergencyStop = false;
    sysState.bootComplete  = false;
    sysState.ntpSynced     = false;
    sysState.mqttOnline    = false;

    // =========================================================
    // STEP 3: WATCHDOG
    // =========================================================
    esp_task_wdt_config_t wdt_cfg = {
        .timeout_ms    = WDT_TIMEOUT_SEC * 1000,
        .idle_core_mask = 0,
        .trigger_panic  = true,
    };
    esp_task_wdt_reconfigure(&wdt_cfg);
    esp_task_wdt_add(NULL);
    Serial.printf("[BOOT] Watchdog: %d sec timeout\n", WDT_TIMEOUT_SEC);

    // =========================================================
    // STEP 4: SEED PRNG + NTP
    // =========================================================
    randomSeed(millis() ^ (uint32_t)ESP.getEfuseMac());
    configTime(0, 0, NTP_SERVER_1, NTP_SERVER_2, NTP_SERVER_3);

    // =========================================================
    // STEP 5: WIFI
    // =========================================================
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    Serial.println("[WIFI] Connecting...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    // NOTE: WIFI_PASSWORD is not printed.

    // =========================================================
    // STEP 6: MQTT CLIENT INIT (connect happens in loop)
    // =========================================================
    mqttClient.setServer(MQTT_BROKER_HOST, MQTT_BROKER_PORT);
    mqttClient.setBufferSize(MQTT_BUFFER_SIZE);
    mqttClient.setKeepAlive(MQTT_KEEPALIVE_SEC);
    mqttClient.setCallback(onMqttMessage);

    // =========================================================
    // STEP 7: SELF-TEST
    // =========================================================
    runBootSelfTest();

    // =========================================================
    // STEP 8: MARK BOOT COMPLETE
    // Only after all safety init is done.
    // This flag gates command processing in the MQTT callback.
    // =========================================================
    sysState.bootComplete = true;

    Serial.println("[BOOT] Boot complete. Operating mode: SAFE");
    Serial.println("==================================================");
}

// ==============================================================================
// SECTION 28: LOOP
// ==============================================================================

void loop() {
    // Reset hardware watchdog at top of every loop
    esp_task_wdt_reset();

    uint32_t now = millis();

    // --- WiFi State Tracking ---
    bool wifiConnected = (WiFi.status() == WL_CONNECTED);
    if (wifiConnected && !wasWifiConnected) {
        wasWifiConnected = true;
        Serial.println("[WIFI] Connected");
        Serial.printf("[WIFI] IP: %s\n", WiFi.localIP().toString().c_str());
    } else if (!wifiConnected && wasWifiConnected) {
        wasWifiConnected   = false;
        sysState.mqttOnline = false;
        Serial.println("[WIFI] Disconnected");
        // WiFi loss does NOT change actuator state (hold safe position)
    }

    // --- NTP State Tracking ---
    if (wifiConnected && !sysState.ntpSynced && isTimeValid()) {
        sysState.ntpSynced = true;
        Serial.println("[NTP] Synced");
    }

    // --- MQTT Connection Loop ---
    if (wifiConnected) {
        if (mqttClient.connected()) {
            mqttClient.loop();
            if (!wasMqttConnected) {
                wasMqttConnected    = true;
                sysState.mqttOnline = true;
            }
        } else {
            if (wasMqttConnected) {
                wasMqttConnected    = false;
                sysState.mqttOnline = false;
                Serial.printf("[MQTT] Disconnected (rc=%d)\n", mqttClient.state());
                // MQTT disconnect: actuator state unchanged (hold as-is)
            }
            if (now - lastMqttReconnect >= MQTT_RECONNECT_INTERVAL_MS) {
                lastMqttReconnect = now;
                connectMQTT();
            }
        }
    }

    // --- Edge AI Decision Engine ---
    runDecisionEngine();

    // --- Periodic Status Heartbeat ---
    if (now - lastStatusPublish >= STATUS_PUBLISH_INTERVAL_MS) {
        lastStatusPublish = now;
        if (mqttClient.connected()) {
            publishEdgeAiStatus();
            publishActuatorStatus();
        }
    }
}
