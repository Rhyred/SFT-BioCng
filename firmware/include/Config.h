#pragma once

#include <Arduino.h>
#include "PinDefinitions.h"

/**
 * @file Config.h
 * @brief Central Configuration for NICEGAS Bio-CNG ESP32 Real Telemetry Node
 */

namespace Config {
    // ==============================================================================
    // 1. WI-FI CONFIGURATION
    // ==============================================================================
    constexpr const char* WIFI_SSID       = "HOTSPOT-ITENAS";    // Ganti dengan SSID WiFi
    constexpr const char* WIFI_PASSWORD   = "";                  // Ganti dengan Password WiFi
    constexpr uint32_t    WIFI_RETRY_INTERVAL_MS = 5000;         // Reconnect retry interval
    constexpr uint32_t    WIFI_MAX_BACKOFF_MS    = 30000;        // Max backoff duration

    // ==============================================================================
    // 2. MQTT BROKER CONFIGURATION
    // ==============================================================================
    constexpr const char* MQTT_HOST       = "192.168.137.57";     // IP Mosquitto Broker / Edge Server
    constexpr uint16_t    MQTT_PORT       = 1883;                // MQTT Port (1883 standard)
    constexpr const char* MQTT_USERNAME   = "";                  // Kosongkan jika anonymous dev broker
    constexpr const char* MQTT_PASSWORD   = "";                  // Password MQTT jika diaktifkan
    constexpr uint16_t    MQTT_KEEPALIVE  = 15;                  // KeepAlive dalam detik
    constexpr uint32_t    MQTT_RECONNECT_INTERVAL_MS = 5000;     // Jeda reconnect MQTT

    // ==============================================================================
    // 3. DEVICE & PROJECT IDENTITY (NICEGAS CONTRACT)
    // ==============================================================================
    // PENTING: PROJECT_NAME harus EXACT match dengan database / Flutter (e.g. "Bio-CNG Plant Alpha")
    constexpr const char* PROJECT_NAME    = "Bio-CNG ITENAS";
    constexpr const char* DEVICE_ID       = "DIGESTER-01";       // Sesuai DB seed ("DIGESTER-01" / "ESP32-001")
    constexpr const char* DEVICE_NAME     = "ESP32 Biodigester Node";
    constexpr const char* COMPONENT       = "biodigester";

    // ==============================================================================
    // 4. TELEMETRY & TIMING CONFIGURATION
    // ==============================================================================
    constexpr uint32_t    TELEMETRY_INTERVAL_MS = 3000;          // Interval publish (3 detik)
    constexpr uint32_t    SERIAL_BAUD_RATE      = 115200;

    // ==============================================================================
    // 5. NTP TIME SYNCHRONIZATION
    // ==============================================================================
    constexpr const char* NTP_SERVER_1    = "pool.ntp.org";
    constexpr const char* NTP_SERVER_2    = "time.google.com";
    constexpr const char* NTP_SERVER_3    = "time.nist.gov";
    constexpr long        NTP_GMT_OFFSET_SEC = 0;                // UTC Time (Wajib 0 untuk ISO 8601 UTC)
    constexpr int         NTP_DAYLIGHT_OFFSET_SEC = 0;

    // ==============================================================================
    // 6. TOPIC GENERATORS
    // ==============================================================================
    // Topic Format: nicegas/{project.name}/{device_id}/{category}/{component}
    inline String getTelemetryTopic() {
        return String("nicegas/") + PROJECT_NAME + "/" + DEVICE_ID + "/telemetry/" + COMPONENT;
    }

    inline String getStatusTopic() {
        return String("nicegas/") + PROJECT_NAME + "/" + DEVICE_ID + "/status/connection";
    }

    inline String getEventTopic(const char* eventType = "alert") {
        return String("nicegas/") + PROJECT_NAME + "/" + DEVICE_ID + "/event/" + eventType;
    }

    inline String getMqttClientId() {
        // Unique Client ID based on Device ID and Chip ID
        uint32_t chipId = (uint32_t)ESP.getEfuseMac();
        char clientIdBuf[40];
        snprintf(clientIdBuf, sizeof(clientIdBuf), "%s_%06X", DEVICE_ID, chipId & 0xFFFFFF);
        return String(clientIdBuf);
    }
}
