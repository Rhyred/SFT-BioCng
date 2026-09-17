#include <Arduino.h>
#include "Config.h"
#include "WiFiManager.h"
#include "TimeManager.h"
#include "MQTTManager.h"
#include "TelemetrySimulator.h"

// ==============================================================================
// GLOBAL INSTANCES
// ==============================================================================
WiFiManager         wifiManager;
TimeManager         timeManager;
MQTTManager         mqttManager(timeManager);
TelemetrySimulator  simulator;

uint32_t lastTelemetryPublishTime = 0;

void setup() {
    Serial.begin(Config::SERIAL_BAUD_RATE);
    delay(1000); // Brief pause for serial monitor stabilization

    Serial.println("\n==================================================");
    Serial.println("   NICEGAS Bio-CNG ESP32 Telemetry Publisher     ");
    Serial.println("==================================================");
    Serial.printf("[BOOT] Project Name : %s\n", Config::PROJECT_NAME);
    Serial.printf("[BOOT] Device ID    : %s\n", Config::DEVICE_ID);
    Serial.printf("[BOOT] Component    : %s\n", Config::COMPONENT);
    Serial.printf("[BOOT] Telemetry Top: %s\n", Config::getTelemetryTopic().c_str());
    Serial.printf("[BOOT] Status Topic : %s\n", Config::getStatusTopic().c_str());
    Serial.println("--------------------------------------------------");

    // Initialize subsystems
    simulator.begin();
    timeManager.begin();
    wifiManager.begin();
    mqttManager.begin();

    Serial.println("[BOOT] Subsystems initialized. Entering main loop...\n");
}

void loop() {
    // 1. Maintain WiFi connection
    wifiManager.loop();

    // 2. Maintain Time synchronization
    timeManager.loop();

    // 3. Maintain MQTT connection & service loops
    mqttManager.loop();

    // 4. Periodic Telemetry Publish (Non-blocking timer)
    uint32_t now = millis();
    if (now - lastTelemetryPublishTime >= Config::TELEMETRY_INTERVAL_MS) {
        lastTelemetryPublishTime = now;

        // Step simulation physics
        simulator.update();
        BiodigesterMetrics metrics = simulator.getMetrics();

        // Generate canonical ISO 8601 UTC timestamp
        String isoTimestamp = timeManager.getISO8601UTC();

        // Generate JSON payload matching NICEGAS contract
        String payload = simulator.generatePayload(isoTimestamp);

        // Publish if connected
        if (mqttManager.isConnected()) {
            bool published = mqttManager.publishTelemetry(payload);
            if (published) {
                Serial.printf("[TELEMETRY] %s | T: %.2f °C | P: %.2f bar | CH4: %.1f %% | Flow: %.1f Nm3/h | pH: %.2f\n",
                              Config::COMPONENT,
                              metrics.temperature,
                              metrics.pressure,
                              metrics.methane,
                              metrics.gas_flow,
                              metrics.ph);
            }
        } else {
            Serial.printf("[TELEMETRY] Skipped (MQTT Not Connected) | T: %.2f °C | CH4: %.1f %%\n",
                          metrics.temperature, metrics.methane);
        }
    }
}
