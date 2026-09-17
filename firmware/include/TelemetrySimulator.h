#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

struct BiodigesterMetrics {
    float temperature; // °C (35.0 - 40.0)
    float pressure;    // bar (1.00 - 1.50)
    float methane;     // % (58.0 - 65.0)
    float gas_flow;    // Nm³/h (20.0 - 30.0)
    float ph;          // pH (6.80 - 7.50)
};

class TelemetrySimulator {
public:
    TelemetrySimulator();
    void begin();
    void update(); // Step simulation drift
    
    BiodigesterMetrics getMetrics() const;
    String generatePayload(const String& isoTimestamp) const;

private:
    float applyBoundedDrift(float current, float minVal, float maxVal, float maxStep);
    
    BiodigesterMetrics _metrics;
    uint32_t _lastUpdateTime;
};
