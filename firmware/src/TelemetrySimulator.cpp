#include "TelemetrySimulator.h"

TelemetrySimulator::TelemetrySimulator()
    : _lastUpdateTime(0) {
    // Initial nominal operating values
    _metrics.temperature = 37.5f;
    _metrics.pressure    = 1.25f;
    _metrics.methane     = 61.5f;
    _metrics.gas_flow    = 25.0f;
    _metrics.ph          = 7.15f;
}

void TelemetrySimulator::begin() {
    // Seed random generator with hardware noise from ADC
    randomSeed(analogRead(34) + millis());
    _lastUpdateTime = millis();
}

float TelemetrySimulator::applyBoundedDrift(float current, float minVal, float maxVal, float maxStep) {
    // Generate random step in [-maxStep, +maxStep]
    float step = ((float)random(-1000, 1001) / 1000.0f) * maxStep;
    
    // Add small restoring pull toward center of range to keep variation bounded & realistic
    float center = (minVal + maxVal) / 2.0f;
    float pull = (center - current) * 0.05f;
    
    float nextVal = current + step + pull;
    if (nextVal < minVal) nextVal = minVal + ((float)random(0, 100) / 1000.0f);
    if (nextVal > maxVal) nextVal = maxVal - ((float)random(0, 100) / 1000.0f);
    
    return nextVal;
}

void TelemetrySimulator::update() {
    uint32_t now = millis();
    // Update simulation state
    _lastUpdateTime = now;

    _metrics.temperature = applyBoundedDrift(_metrics.temperature, 35.0f, 40.0f, 0.15f);
    _metrics.pressure    = applyBoundedDrift(_metrics.pressure,    1.00f, 1.50f, 0.02f);
    _metrics.methane     = applyBoundedDrift(_metrics.methane,     58.0f, 65.0f, 0.25f);
    _metrics.gas_flow    = applyBoundedDrift(_metrics.gas_flow,    20.0f, 30.0f, 0.40f);
    _metrics.ph          = applyBoundedDrift(_metrics.ph,          6.80f, 7.50f, 0.03f);
}

BiodigesterMetrics TelemetrySimulator::getMetrics() const {
    return _metrics;
}

String TelemetrySimulator::generatePayload(const String& isoTimestamp) const {
    JsonDocument doc;

    doc["timestamp"] = isoTimestamp;
    doc["status"] = "nominal";

    JsonObject metricsObj = doc["metrics"].to<JsonObject>();

    // Temperature (°C)
    JsonObject tempObj = metricsObj["temperature"].to<JsonObject>();
    tempObj["v"] = round(_metrics.temperature * 100.0f) / 100.0f;
    tempObj["u"] = "°C";

    // Pressure (bar)
    JsonObject pressObj = metricsObj["pressure"].to<JsonObject>();
    pressObj["v"] = round(_metrics.pressure * 100.0f) / 100.0f;
    pressObj["u"] = "bar";

    // Methane (%)
    JsonObject ch4Obj = metricsObj["methane"].to<JsonObject>();
    ch4Obj["v"] = round(_metrics.methane * 10.0f) / 10.0f;
    ch4Obj["u"] = "%";

    // Gas Flow (Nm³/h)
    JsonObject flowObj = metricsObj["gas_flow"].to<JsonObject>();
    flowObj["v"] = round(_metrics.gas_flow * 10.0f) / 10.0f;
    flowObj["u"] = "Nm³/h";

    // pH
    JsonObject phObj = metricsObj["ph"].to<JsonObject>();
    phObj["v"] = round(_metrics.ph * 100.0f) / 100.0f;
    phObj["u"] = "pH";

    String output;
    serializeJson(doc, output);
    return output;
}
