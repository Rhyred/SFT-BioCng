#pragma once

#include <Arduino.h>
#include <time.h>

class TimeManager {
public:
    TimeManager();
    void begin();
    void loop();
    bool isTimeSynced() const;
    String getISO8601UTC() const;
    time_t getEpochUTC() const;

private:
    bool _isSynced;
    uint32_t _lastSyncCheck;
};
