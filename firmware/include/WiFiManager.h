#pragma once

#include <Arduino.h>
#include <WiFi.h>

class WiFiManager {
public:
    WiFiManager();
    void begin();
    void loop();
    bool isConnected() const;
    String getIPAddress() const;
    int8_t getRSSI() const;

private:
    void initiateConnection();
    
    bool _wasConnected;
    uint32_t _lastAttemptTime;
    uint32_t _currentBackoffMs;
    uint32_t _connectStartTime;
    bool _isConnecting;
};
