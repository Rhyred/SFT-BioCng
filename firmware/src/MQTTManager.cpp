#include "MQTTManager.h"
#include "Config.h"
#include <ArduinoJson.h>

MQTTManager::MQTTManager(TimeManager& timeManager)
    : _mqttClient(_wifiClient),
      _timeManager(timeManager),
      _lastReconnectAttempt(0),
      _wasConnected(false) {
}

void MQTTManager::begin() {
    Serial.println("[MQTT] Initializing MQTT Manager...");
    _mqttClient.setServer(Config::MQTT_HOST, Config::MQTT_PORT);
    _mqttClient.setBufferSize(512); // Ensure JSON payloads fit comfortably
    _mqttClient.setKeepAlive(Config::MQTT_KEEPALIVE);
}

void MQTTManager::loop() {
    if (_mqttClient.connected()) {
        if (!_wasConnected) {
            _wasConnected = true;
        }
        _mqttClient.loop();
    } else {
        if (_wasConnected) {
            _wasConnected = false;
            Serial.printf("[MQTT] Disconnected (State: %d)\n", _mqttClient.state());
        }
        
        // Reconnect with cooldown
        uint32_t now = millis();
        if (WiFi.status() == WL_CONNECTED && (now - _lastReconnectAttempt > Config::MQTT_RECONNECT_INTERVAL_MS)) {
            _lastReconnectAttempt = now;
            reconnect();
        }
    }
}

bool MQTTManager::isConnected() {
    return _mqttClient.connected();
}

void MQTTManager::reconnect() {
    String clientId = Config::getMqttClientId();
    String statusTopic = Config::getStatusTopic();
    
    // LWT Payload: {"status": "offline"}
    const char* willPayload = "{\"status\":\"offline\"}";
    uint8_t willQos = 1;
    bool willRetain = true;

    Serial.printf("[MQTT] Connecting to %s:%d as ClientID: %s\n", 
                  Config::MQTT_HOST, Config::MQTT_PORT, clientId.c_str());

    bool success = false;
    if (strlen(Config::MQTT_USERNAME) > 0) {
        success = _mqttClient.connect(
            clientId.c_str(),
            Config::MQTT_USERNAME,
            Config::MQTT_PASSWORD,
            statusTopic.c_str(),
            willQos,
            willRetain,
            willPayload
        );
    } else {
        success = _mqttClient.connect(
            clientId.c_str(),
            statusTopic.c_str(),
            willQos,
            willRetain,
            willPayload
        );
    }

    if (success) {
        Serial.println("[MQTT] Connected");
        _wasConnected = true;
        publishOnlineStatus();
    } else {
        Serial.printf("[MQTT] Connect failed, rc=%d. Will retry in %u ms\n", 
                      _mqttClient.state(), Config::MQTT_RECONNECT_INTERVAL_MS);
    }
}

void MQTTManager::publishOnlineStatus() {
    String statusTopic = Config::getStatusTopic();
    String isoTime = _timeManager.getISO8601UTC();

    JsonDocument doc;
    doc["status"] = "online";
    doc["timestamp"] = isoTime;
    doc["device_id"] = Config::DEVICE_ID;
    doc["device_name"] = Config::DEVICE_NAME;

    String payload;
    serializeJson(doc, payload);

    bool pubSuccess = _mqttClient.publish(statusTopic.c_str(), payload.c_str(), true); // Retained
    if (pubSuccess) {
        Serial.printf("[STATUS] online published to %s (retained)\n", statusTopic.c_str());
    } else {
        Serial.println("[STATUS] Failed to publish online status");
    }
}

bool MQTTManager::publishStatus(const char* status) {
    if (!_mqttClient.connected()) return false;

    String statusTopic = Config::getStatusTopic();
    String isoTime = _timeManager.getISO8601UTC();

    JsonDocument doc;
    doc["status"] = status;
    doc["timestamp"] = isoTime;

    String payload;
    serializeJson(doc, payload);

    return _mqttClient.publish(statusTopic.c_str(), payload.c_str(), true);
}

bool MQTTManager::publishTelemetry(const String& payload) {
    if (!_mqttClient.connected()) return false;

    String telemetryTopic = Config::getTelemetryTopic();
    // Telemetry is published with QoS 0 or 1, Retain = false (as per NICEGAS convention)
    bool success = _mqttClient.publish(telemetryTopic.c_str(), payload.c_str(), false);
    
    if (success) {
        Serial.printf("[TELEMETRY] Published to %s\n", telemetryTopic.c_str());
    } else {
        Serial.printf("[TELEMETRY] Failed to publish to %s\n", telemetryTopic.c_str());
    }
    return success;
}
