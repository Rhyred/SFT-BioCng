/**
 * @file node3_kompresi.ino
 * @brief NICEGAS Bio-CNG — NODE 3: KOMPRESI (ESP32 Standardized Dummy Telemetry Publisher)
 * 
 * Target Hardware: ESP32 Dev Module
 * Telemetry Mode : DUMMY / SIMULATED ONLY (No physical sensors read in this phase)
 * Target Backend : NICEGAS Backend (PostgreSQL + Flutter)
 */

#include <WiFi.h>
#include <WiFiClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>

// ==============================================================================
// 1. CONFIGURATION
// ==============================================================================
#define TELEMETRY_MODE_DUMMY 1

// WiFi Credentials
const char* WIFI_SSID       = "ICT-LAB WORKSPACE";
const char* WIFI_PASSWORD   = "ICTLAB2024";

// IMPORTANT:
// Set MQTT_HOST to the LAN IP of the machine running Mosquitto.
// The same value MUST be used by all four ESP32 nodes.
const char* MQTT_HOST       = "192.168.1.204";
const uint16_t MQTT_PORT    = 1883;
const char* MQTT_USERNAME   = "";
const char* MQTT_PASSWORD   = "";

// Canonical Project & Node Identity (EXACT match with database & backend)
const char* PROJECT_NAME    = "Bio-CNG Plant New";
const char* DEVICE_ID       = "COMP-01";
const char* DEVICE_NAME     = "ESP32 Kompresi Node";
const char* COMPONENT       = "kompresi";

// Intervals
const uint32_t TELEMETRY_INTERVAL_MS      = 5000;  // 5 seconds
const uint32_t MQTT_RECONNECT_INTERVAL_MS = 5000;  // 5 seconds

// ==============================================================================
// 2. GLOBAL OBJECTS & STATE
// ==============================================================================
WiFiClient espClient;
PubSubClient mqttClient(espClient);

uint32_t lastTelemetryTime = 0;
uint32_t lastMqttReconnect = 0;
bool wasWifiConnected      = false;
bool wasMqttConnected      = false;
bool wasNtpSynced          = false;

// ==============================================================================
// 3. TELEMETRY MODEL & BOUNDED DRIFT
// ==============================================================================
struct KompresiMetrics {
    float pressure      = 200.0f; // bar    (Range: 180.0 - 220.0)
    float temperature   = 34.0f;  // °C     (Range: 28.0 - 40.0)
    float methane       = 96.0f;  // %      (Range: 94.0 - 98.0)
    float gas_flow      = 23.5f;  // Nm³/h  (Range: 20.0 - 27.0)
    float motor_current = 13.0f;  // A      (Range: 8.0 - 18.0)
} metrics;

float applyBoundedDrift(float current, float minVal, float maxVal, float maxStep) {
    float step = ((float)random(-1000, 1001) / 1000.0f) * maxStep;
    float center = (minVal + maxVal) / 2.0f;
    float pull = (center - current) * 0.05f;
    float nextVal = current + step + pull;
    if (nextVal < minVal) nextVal = minVal + ((float)random(0, 100) / 1000.0f);
    if (nextVal > maxVal) nextVal = maxVal - ((float)random(0, 100) / 1000.0f);
    return nextVal;
}

void updateDummyTelemetry() {
#if TELEMETRY_MODE_DUMMY
    metrics.pressure      = applyBoundedDrift(metrics.pressure,      180.00f, 220.00f, 0.80f);
    metrics.temperature   = applyBoundedDrift(metrics.temperature,   28.00f,  40.00f,  0.15f);
    metrics.methane       = applyBoundedDrift(metrics.methane,       94.00f,  98.00f,  0.10f);
    metrics.gas_flow      = applyBoundedDrift(metrics.gas_flow,      20.00f,  27.00f,  0.20f);
    metrics.motor_current = applyBoundedDrift(metrics.motor_current, 8.00f,   18.00f,  0.25f);
#endif
}

const char* calculateStatus() {
    return "optimal";
}

// ==============================================================================
// 4. NTP / TIMESTAMP VALIDATION
// ==============================================================================
bool isTimeValid() {
    time_t now = time(nullptr);
    return (now > 1700000000); // Valid epoch after late 2023
}

String getISO8601UTC() {
    struct tm timeinfo;
    time_t now = time(nullptr);
    gmtime_r(&now, &timeinfo);
    
    char buf[32];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
    return String(buf);
}

// ==============================================================================
// 5. MQTT TOPICS & PAYLOAD HELPERS
// ==============================================================================
String getTelemetryTopic() {
    return String("nicegas/") + PROJECT_NAME + "/" + DEVICE_ID + "/telemetry/" + COMPONENT;
}

String getStatusTopic() {
    return String("nicegas/") + PROJECT_NAME + "/" + DEVICE_ID + "/status/connection";
}

String getMqttClientId() {
    uint32_t chipId = (uint32_t)ESP.getEfuseMac();
    char buf[40];
    snprintf(buf, sizeof(buf), "%s_%06X", DEVICE_ID, chipId & 0xFFFFFF);
    return String(buf);
}

// ==============================================================================
// 6. MQTT PUBLISH (STATUS & TELEMETRY)
// ==============================================================================
void publishOnlineStatus() {
    String statusTopic = getStatusTopic();
    String isoTime = isTimeValid() ? getISO8601UTC() : "";

    JsonDocument doc;
    doc["status"] = "online";
    if (isoTime.length() > 0) {
        doc["timestamp"] = isoTime;
    }
    doc["device_id"] = DEVICE_ID;
    doc["device_name"] = DEVICE_NAME;

    String payload;
    serializeJson(doc, payload);

    bool ok = mqttClient.publish(statusTopic.c_str(), payload.c_str(), true);
    if (ok) {
        Serial.println("[STATUS] Online");
    } else {
        Serial.println("[STATUS] Online publish FAILED");
    }
}

void publishTelemetry() {
    if (!isTimeValid()) {
        Serial.println("[NTP] Waiting for valid time before publishing telemetry...");
        return;
    }

    updateDummyTelemetry();

    String isoTime = getISO8601UTC();
    JsonDocument doc;
    doc["device_id"] = DEVICE_ID;
    doc["component"] = COMPONENT;
    doc["status"]    = calculateStatus();
    doc["timestamp"] = isoTime;

    JsonObject metricsObj = doc["metrics"].to<JsonObject>();

    // pressure (bar)
    JsonObject pressObj = metricsObj["pressure"].to<JsonObject>();
    pressObj["v"] = round(metrics.pressure * 10.0f) / 10.0f;
    pressObj["u"] = "bar";

    // temperature (°C)
    JsonObject tempObj = metricsObj["temperature"].to<JsonObject>();
    tempObj["v"] = round(metrics.temperature * 100.0f) / 100.0f;
    tempObj["u"] = "°C";

    // methane (%)
    JsonObject ch4Obj = metricsObj["methane"].to<JsonObject>();
    ch4Obj["v"] = round(metrics.methane * 10.0f) / 10.0f;
    ch4Obj["u"] = "%";

    // gas_flow (Nm³/h)
    JsonObject flowObj = metricsObj["gas_flow"].to<JsonObject>();
    flowObj["v"] = round(metrics.gas_flow * 10.0f) / 10.0f;
    flowObj["u"] = "Nm³/h";

    // motor_current (A)
    JsonObject currObj = metricsObj["motor_current"].to<JsonObject>();
    currObj["v"] = round(metrics.motor_current * 10.0f) / 10.0f;
    currObj["u"] = "A";

    String payload;
    serializeJson(doc, payload);

    String topic = getTelemetryTopic();
    bool ok = mqttClient.publish(topic.c_str(), payload.c_str(), false);
    if (ok) {
        Serial.printf("[TELEMETRY] Published %s\n", DEVICE_ID);
        Serial.printf("[TELEMETRY] pressure=%.1fbar temp=%.2fC methane=%.1f%% flow=%.1fNm3/h current=%.1fA\n",
                      metrics.pressure, metrics.temperature, metrics.methane, metrics.gas_flow, metrics.motor_current);
    } else {
        Serial.println("[MQTT] Publish FAILED");
    }
}

// ==============================================================================
// 7. MQTT CONNECTION & LAST WILL
// ==============================================================================
void connectMQTT() {
    String clientId = getMqttClientId();
    String statusTopic = getStatusTopic();

    // LWT Payload
    JsonDocument willDoc;
    willDoc["status"] = "offline";
    willDoc["device_id"] = DEVICE_ID;
    willDoc["device_name"] = DEVICE_NAME;
    String willPayload;
    serializeJson(willDoc, willPayload);

    Serial.printf("[MQTT] Connecting to %s:%d as %s...\n", MQTT_HOST, MQTT_PORT, clientId.c_str());

    bool ok = false;
    if (strlen(MQTT_USERNAME) > 0) {
        ok = mqttClient.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD,
                                statusTopic.c_str(), 1, true, willPayload.c_str());
    } else {
        ok = mqttClient.connect(clientId.c_str(), statusTopic.c_str(), 1, true, willPayload.c_str());
    }

    if (ok) {
        Serial.println("[MQTT] Connected");
        wasMqttConnected = true;
        publishOnlineStatus();
    } else {
        Serial.printf("[MQTT] Connect failed, rc=%d. Retrying in %u ms\n", mqttClient.state(), MQTT_RECONNECT_INTERVAL_MS);
    }
}

// ==============================================================================
// 8. SETUP
// ==============================================================================
void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n==================================================");
    Serial.println("   NICEGAS Bio-CNG — NODE 3: KOMPRESI           ");
    Serial.println("==================================================");
    Serial.printf("[BOOT] Project Name : %s\n", PROJECT_NAME);
    Serial.printf("[BOOT] Device ID    : %s\n", DEVICE_ID);
    Serial.printf("[BOOT] Telemetry Top: %s\n", getTelemetryTopic().c_str());
    Serial.printf("[BOOT] Status Topic : %s\n", getStatusTopic().c_str());
    Serial.println("--------------------------------------------------");

    // Seed PRNG
    randomSeed(millis() ^ (uint32_t)ESP.getEfuseMac());

    // Configure NTP UTC
    configTime(0, 0, "pool.ntp.org", "time.nist.gov", "time.google.com");

    // Initialize WiFi
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    Serial.println("[WIFI] Connecting...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    // Initialize MQTT
    mqttClient.setServer(MQTT_HOST, MQTT_PORT);
    mqttClient.setBufferSize(512);
    mqttClient.setKeepAlive(15);
}

// ==============================================================================
// 9. LOOP
// ==============================================================================
void loop() {
    // WiFi Status Tracking
    bool wifiConnected = (WiFi.status() == WL_CONNECTED);
    if (wifiConnected && !wasWifiConnected) {
        wasWifiConnected = true;
        Serial.println("[WIFI] Connected");
        Serial.printf("[WIFI] IP: %s\n", WiFi.localIP().toString().c_str());
    } else if (!wifiConnected && wasWifiConnected) {
        wasWifiConnected = false;
        Serial.println("[WIFI] Disconnected");
    }

    // NTP Status Tracking
    if (wifiConnected && !wasNtpSynced && isTimeValid()) {
        wasNtpSynced = true;
        Serial.println("[NTP] Synced");
    }

    // MQTT Connection Loop
    if (wifiConnected) {
        if (mqttClient.connected()) {
            mqttClient.loop();
        } else {
            if (wasMqttConnected) {
                wasMqttConnected = false;
                Serial.printf("[MQTT] Disconnected (State: %d)\n", mqttClient.state());
            }
            uint32_t now = millis();
            if (now - lastMqttReconnect >= MQTT_RECONNECT_INTERVAL_MS) {
                lastMqttReconnect = now;
                connectMQTT();
            }
        }
    }

    // Periodic Telemetry Publishing
    uint32_t now = millis();
    if (now - lastTelemetryTime >= TELEMETRY_INTERVAL_MS) {
        lastTelemetryTime = now;
        if (mqttClient.connected()) {
            publishTelemetry();
        } else {
            Serial.println("[TELEMETRY] Skipped (MQTT Offline)");
        }
    }
}
