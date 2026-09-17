#include "WiFiManager.h"
#include "Config.h"

WiFiManager::WiFiManager()
    : _wasConnected(false),
      _lastAttemptTime(0),
      _currentBackoffMs(Config::WIFI_RETRY_INTERVAL_MS),
      _connectStartTime(0),
      _isConnecting(false) {
}

void WiFiManager::begin() {
    Serial.println("[WIFI] Initializing Wi-Fi Manager...");
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    initiateConnection();
}

void WiFiManager::initiateConnection() {
    Serial.printf("[WIFI] Connecting to SSID: %s\n", Config::WIFI_SSID);
    // Security: Do NOT log WIFI_PASSWORD
    WiFi.begin(Config::WIFI_SSID, Config::WIFI_PASSWORD);
    _lastAttemptTime = millis();
    _connectStartTime = millis();
    _isConnecting = true;
}

void WiFiManager::loop() {
    wl_status_t status = WiFi.status();
    bool connected = (status == WL_CONNECTED);

    if (connected && !_wasConnected) {
        _wasConnected = true;
        _isConnecting = false;
        _currentBackoffMs = Config::WIFI_RETRY_INTERVAL_MS; // Reset backoff
        Serial.println("[WIFI] Connected");
        Serial.printf("[WIFI] IP: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("[WIFI] RSSI: %d dBm\n", WiFi.RSSI());
    } else if (!connected && _wasConnected) {
        _wasConnected = false;
        _isConnecting = false;
        _lastAttemptTime = millis();
        Serial.println("[WIFI] Disconnected from AP");
    }

    // If not connected and not currently attempting or attempt timed out (15s), retry with backoff
    if (!connected) {
        uint32_t now = millis();
        if (_isConnecting && (now - _connectStartTime > 15000)) {
            Serial.println("[WIFI] Connection attempt timed out. Will retry...");
            _isConnecting = false;
            _lastAttemptTime = now;
        }

        if (!_isConnecting && (now - _lastAttemptTime >= _currentBackoffMs)) {
            Serial.printf("[WIFI] Reconnecting... (Backoff: %u ms)\n", _currentBackoffMs);
            initiateConnection();
            
            // Exponential backoff capped at max
            _currentBackoffMs = min(_currentBackoffMs * 2, Config::WIFI_MAX_BACKOFF_MS);
        }
    }
}

bool WiFiManager::isConnected() const {
    return WiFi.status() == WL_CONNECTED;
}

String WiFiManager::getIPAddress() const {
    if (isConnected()) {
        return WiFi.localIP().toString();
    }
    return "0.0.0.0";
}

int8_t WiFiManager::getRSSI() const {
    if (isConnected()) {
        return WiFi.RSSI();
    }
    return 0;
}
