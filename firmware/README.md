# NICEGAS Bio-CNG — ESP32 Real MQTT Telemetry Publisher

Firmware ESP32 modular untuk publisher telemetri MQTT realtime pada ekosistem **NICEGAS Bio-CNG** (terintegrasi dengan Mosquitto Broker, Operator App Flutter, dan Backend FastAPI PostgreSQL).

---

## 1. Hardware Architecture & Wiring (Berdasarkan Skematik)

Sistem menggunakan catu daya 9V 2A terpusat yang didistribusikan ke 4 node menggunakan modul stepdown **LM2596 5V 3A** per node dengan **Common Ground (GND)**.

```
ADAPTOR 9V 2A ──► KABEL 4 CABANG ──► STEPDOWN LM2596 (5V 3A) ──► ESP32 (VIN / 5V)
                                                                   └── SENSOR & AKTUATOR
```

### Pin Mapping Node 1: Biodigester (Active Firmware)

| Komponen / Sensor | Tipe Sinyal | Pin ESP32 (DEVKIT V1) | Catu Daya | Keterangan |
| :--- | :--- | :--- | :--- | :--- |
| **Suhu (DS18B20)** | Digital 1-Wire | **D4 (GPIO2)** | 3.3V / GND | Sensor temperatur biodigester |
| **Metana (MQ-4)** | Analog | **A0 (GPIO34 / ADC1_CH6)** | 5V / GND | Konsentrasi CH4 |
| **pH Meter (PH-4502C)** | Analog | **A1 (GPIO35 / ADC1_CH7)** | 5V / GND | Probe keasaman / pH slurry |

### Ringkasan Pinout Node Lainnya (Future Expansion)

* **Node 2 Purifikasi**:
  * H2S (MQ-136): `A0` (GPIO34)
  * CO2 (MQ-135): `A1` (GPIO35)
* **Node 3 Kompresi**:
  * CH4 (MQ-4): `A0` (GPIO34)
  * Pressure Transducer (0–10 MPa): `A1` (GPIO35)
* **Node 4 Aktuasi**:
  * Solenoid Valve Gas: `D5` (GPIO14)
  * Relay 4 Channel: `D18` (GPIO18), `D19` (GPIO19), `D21` (GPIO21), `D22` (GPIO22)

---

## 2. MQTT Hierarchy & Data Contract

### Topic Contract

* **Telemetry**: `nicegas/{PROJECT_NAME}/{DEVICE_ID}/telemetry/{COMPONENT}`
  * Contoh: `nicegas/Bio-CNG Plant Alpha/DIGESTER-01/telemetry/biodigester`
* **Status (LWT & Online)**: `nicegas/{PROJECT_NAME}/{DEVICE_ID}/status/connection`
  * Contoh: `nicegas/Bio-CNG Plant Alpha/DIGESTER-01/status/connection`
* **Event**: `nicegas/{PROJECT_NAME}/{DEVICE_ID}/event/{COMPONENT}`

> **PENTING**: `PROJECT_NAME` harus persis (*exact case-sensitive*) dengan nama project yang terdaftar di database dan aplikasi Flutter (misal: `"Bio-CNG Plant Alpha"`). Jangan mengganti spasi menjadi underscore.

### Status Payloads (Retained = true, QoS = 1)

* **Last Will and Testament (LWT / Offline)**:
  ```json
  {
    "status": "offline"
  }
  ```
* **Online Status (saat boot / reconnect)**:
  ```json
  {
    "status": "online",
    "timestamp": "2026-09-11T08:00:00Z",
    "device_id": "DIGESTER-01",
    "device_name": "ESP32 Biodigester Node"
  }
  ```

### Telemetry Payload (Canonical Schema)

```json
{
  "timestamp": "2026-09-11T08:00:00Z",
  "status": "nominal",
  "metrics": {
    "temperature": { "v": 37.82, "u": "°C" },
    "pressure": { "v": 1.32, "u": "bar" },
    "methane": { "v": 61.6, "u": "%" },
    "gas_flow": { "v": 26.2, "u": "Nm³/h" },
    "ph": { "v": 7.14, "u": "pH" }
  }
}
```

---

## 3. Struktur Project Firmware

```
firmware/
├── platformio.ini               # Konfigurasi PlatformIO & library dependencies
├── README.md                    # Dokumentasi lengkap firmware
├── include/
│   ├── Config.h                 # Konfigurasi terpusat (WiFi, Broker MQTT, Identity)
│   ├── PinDefinitions.h         # Definisi pinout sesuai skematik fisik
│   ├── WiFiManager.h            # Header manajemen koneksi WiFi & exponential backoff
│   ├── TimeManager.h            # Header NTP UTC ISO 8601 synchronization
│   ├── MQTTManager.h            # Header MQTT client, LWT, dan telemetry publisher
│   └── TelemetrySimulator.h     # Header bounded drift simulation biodigester
├── src/
│   ├── main.cpp                 # Main loop orchestrator (non-blocking)
│   ├── WiFiManager.cpp
│   ├── TimeManager.cpp
│   ├── MQTTManager.cpp
│   └── TelemetrySimulator.cpp
└── nicegas_esp32_arduino/
    └── nicegas_esp32_arduino.ino # Single-sketch version untuk pengguna Arduino IDE
```

---

## 4. Konfigurasi & Cara Flash

### Mengubah Konfigurasi Jaringan & Broker

Buka `firmware/include/Config.h` (untuk PlatformIO) atau `nicegas_esp32_arduino.ino` (untuk Arduino IDE):

```cpp
constexpr const char* WIFI_SSID       = "NAMA_WIFI_ANDA";
constexpr const char* WIFI_PASSWORD   = "PASSWORD_WIFI_ANDA";

constexpr const char* MQTT_HOST       = "192.168.1.100";  // IP Laptop / Edge Server Mosquitto
constexpr uint16_t    MQTT_PORT       = 1883;

constexpr const char* PROJECT_NAME    = "Bio-CNG Plant Alpha";
constexpr const char* DEVICE_ID       = "DIGESTER-01";
```

### Pilihan A: Menggunakan PlatformIO (VS Code / CLI)

1. Pasang extension **PlatformIO IDE** di VS Code.
2. Buka folder `firmware`.
3. Sambungkan ESP32 via kabel Micro-USB/Type-C ke komputer.
4. Klik icon **PlatformIO: Build** lalu **PlatformIO: Upload**.
5. Buka **PlatformIO: Serial Monitor** pada baudrate `115200`.

### Pilihan B: Menggunakan Arduino IDE

1. Buka Arduino IDE.
2. Pasang board support ESP32 via Boards Manager: `esp32 by Espressif Systems`.
3. Pasang library via Library Manager:
   * **PubSubClient** by *Nick O'Leary*
   * **ArduinoJson** by *Benoit Blanchon* (v6 atau v7)
4. Buka file `firmware/nicegas_esp32_arduino/nicegas_esp32_arduino.ino`.
5. Pilih Board: **ESP32 Dev Module** dan Port COM yang sesuai.
6. Klik **Upload** dan buka Serial Monitor (`115200 baud`).

---

## 5. Serial Monitor Output Contoh

```text
==================================================
   NICEGAS Bio-CNG ESP32 Telemetry Publisher     
==================================================
[BOOT] Project Name : Bio-CNG Plant Alpha
[BOOT] Device ID    : DIGESTER-01
[BOOT] Component    : biodigester
[BOOT] Telemetry Top: nicegas/Bio-CNG Plant Alpha/DIGESTER-01/telemetry/biodigester
[BOOT] Status Topic : nicegas/Bio-CNG Plant Alpha/DIGESTER-01/status/connection
--------------------------------------------------
[TIME] Configuring SNTP for UTC Time Sync...
[WIFI] Initializing Wi-Fi Manager...
[WIFI] Connecting to SSID: NICEGAS_WIFI
[MQTT] Initializing MQTT Manager...
[BOOT] Subsystems initialized. Entering main loop...

[WIFI] Connected
[WIFI] IP: 192.168.1.50
[WIFI] RSSI: -54 dBm
[TIME] NTP Synced Successfully! Current UTC: 2026-09-11T08:05:00Z
[MQTT] Connecting to 192.168.1.100:1883 as ClientID: DIGESTER-01_A1B2C3
[MQTT] Connected
[STATUS] online published to nicegas/Bio-CNG Plant Alpha/DIGESTER-01/status/connection (retained)
[TELEMETRY] biodigester | T: 37.45 °C | P: 1.26 bar | CH4: 61.2 % | Flow: 25.4 Nm3/h | pH: 7.12
[TELEMETRY] biodigester | T: 37.48 °C | P: 1.25 bar | CH4: 61.4 % | Flow: 25.1 Nm3/h | pH: 7.15
```

---

## 6. Integrasi End-to-End dengan Flutter & Backend

1. **Jalankan Mosquitto & Backend**:
   ```bash
   cd NICEGAS_Server
   docker-compose up -d
   ```
2. **Jalankan ESP32**:
   Nyalakan ESP32, amati log serial hingga muncul `[MQTT] Connected` dan `[STATUS] online`.
3. **Buka Aplikasi Flutter**:
   Pilih project `"Bio-CNG Plant Alpha"`.
   * Status perangkat `"DIGESTER-01"` akan otomatis berubah menjadi **ONLINE** (hijau).
   * Badge indikator **LIVE** menyala.
   * Nilai metrik Temperature, Pressure, Methane, Flow, dan pH akan diperbarui secara realtime setiap 3 detik.
