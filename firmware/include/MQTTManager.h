#pragma once

#include <Arduino.h>
#include <WiFiClient.h>
#include <PubSubClient.h>
#include "TimeManager.h"

class MQTTManager {
public:
    MQTTManager(TimeManager& timeManager);
    void begin();
    void loop();
    bool isConnected();
    bool publishTelemetry(const String& payload);
    bool publishStatus(const char* status);

private:
    void reconnect();
    void publishOnlineStatus();

    WiFiClient _wifiClient;
    PubSubClient _mqttClient;
    TimeManager& _timeManager;

    uint32_t _lastReconnectAttempt;
    bool _wasConnected;
};
