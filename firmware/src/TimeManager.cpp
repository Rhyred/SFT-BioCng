#include "TimeManager.h"
#include "Config.h"
#include <esp_sntp.h>

TimeManager::TimeManager()
    : _isSynced(false),
      _lastSyncCheck(0) {
}

void TimeManager::begin() {
    Serial.println("[TIME] Configuring SNTP for UTC Time Sync...");
    // 0 offset and 0 daylight offset for UTC
    configTime(Config::NTP_GMT_OFFSET_SEC, Config::NTP_DAYLIGHT_OFFSET_SEC, 
               Config::NTP_SERVER_1, Config::NTP_SERVER_2, Config::NTP_SERVER_3);
}

void TimeManager::loop() {
    uint32_t now = millis();
    // Check sync status every 5 seconds until synced, then every 60 seconds
    uint32_t checkInterval = _isSynced ? 60000 : 5000;
    
    if (now - _lastSyncCheck >= checkInterval) {
        _lastSyncCheck = now;
        
        time_t nowUtc = 0;
        struct tm timeinfo;
        if (getLocalTime(&timeinfo, 50)) {
            time(&nowUtc);
            // Verify if year is greater than 2024 (valid sync)
            if (timeinfo.tm_year + 1900 >= 2024) {
                if (!_isSynced) {
                    _isSynced = true;
                    Serial.printf("[TIME] NTP Synced Successfully! Current UTC: %s\n", getISO8601UTC().c_str());
                }
            }
        }
    }
}

bool TimeManager::isTimeSynced() const {
    return _isSynced;
}

time_t TimeManager::getEpochUTC() const {
    time_t now;
    time(&now);
    return now;
}

String TimeManager::getISO8601UTC() const {
    struct tm timeinfo;
    if (getLocalTime(&timeinfo, 50) && (timeinfo.tm_year + 1900 >= 2024)) {
        char buf[32];
        strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
        return String(buf);
    }
    
    // Fallback if NTP is not yet synced: return simulated 2026 UTC timestamp using millis
    uint32_t secondsSinceBoot = millis() / 1000;
    char fallbackBuf[32];
    snprintf(fallbackBuf, sizeof(fallbackBuf), "2026-09-11T00:00:%02dZ", (int)(secondsSinceBoot % 60));
    return String(fallbackBuf);
}
