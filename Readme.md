# NICEGAS

NICEGAS is an industrial monitoring platform consisting of a Flutter operator application, a FastAPI backend, a PostgreSQL database, MQTT realtime messaging, Edge Server deployment, ESP32/device integration, emergency MQTT failover, and future analytics, AI, Digital Twin, and cloud capabilities.

The project is being developed incrementally. The realtime IoT foundation is being established before advanced intelligence and cloud features are introduced.

## Current Project Status

The project is currently executing Phase 4, establishing the Realtime IoT foundation connecting the Flutter operator application to devices via MQTT. Phase 4.3B (MQTT Primary / Emergency Failover) is implemented, with physical verification pending.

### Project Roadmap & Status

| Phase | Area                                           | Status                  |
| ----- | ---------------------------------------------- | ----------------------- |
| 0     | Flutter Foundation                             | ✅ COMPLETED            |
| 1     | System Configuration & Contracts               | ✅ COMPLETED / FROZEN   |
| 2     | Backend & Local Infrastructure                 | ✅ COMPLETED            |
| 3     | Flutter MVP                                    | ✅ COMPLETED            |
| 4.1   | MQTT Architecture & Telemetry Contract         | ✅ COMPLETED            |
| 4.2   | Backend MQTT Consumer                          | ✅ COMPLETED            |
| 4.3A  | Flutter MQTT Realtime                          | ✅ COMPLETED            |
| 4.3B  | MQTT Primary/Emergency Failover                | 🟡 PENDING VERIFICATION |
| 4.4   | Physical Prototype Topology                    | ⏳ PLANNED              |
| 4.5   | Physical Failover Verification                 | ⏳ PLANNED              |
| 4.6   | ESP32 Firmware Integration                     | ⏳ PLANNED              |
| 4.7   | End-to-End IoT Validation                      | ⏳ PLANNED              |
| 4.8   | Operator First-Run Configuration               | ⏳ PLANNED              |
| 4.9   | Offline Buffering & Data Continuity            | ⏸️ DEFERRED           |
| 5     | Production Security & Access Control           | ⏳ PLANNED              |
| 6     | Alerting, Audible Alarm & Operator Flow        | ✅ IMPLEMENTED (APP)    |
| 7     | N.E.X.A. AI Operational Companion (J.A.R.V.I.S)| ✅ IMPLEMENTED (APP)    |
| 8     | 3D Digital Twin Viewer & Visualization         | ✅ IMPLEMENTED (APP)    |
| 9     | Cloud, Multi-Site & Production Scale           | 🔮 FUTURE               |

---

## Phase Details

### PHASE 0: Flutter Foundation

**STATUS: ✅ COMPLETED**

* Flutter project foundation
* Basic project structure
* Dependency foundation
* Environment/configuration pattern
* Android physical-device verification

### PHASE 1: System Configuration & API/MQTT Contracts

**STATUS: ✅ COMPLETED / FROZEN**

* API contract
* JSON response conventions
* UTC timestamp conventions
* Pagination conventions
* Error conventions
* MQTT topic conventions
* Telemetry payload structure
* Stable boundaries between Flutter, backend, database, and MQTT

*Phase 1 contracts should be treated as the source of truth unless explicitly changed through a documented architecture decision.*

### PHASE 2: Backend + Local Infrastructure

**STATUS: ✅ COMPLETED**

* Docker Compose
* PostgreSQL
* Eclipse Mosquitto
* FastAPI
* SQLAlchemy
* Alembic
* Core REST API
* Health endpoint
* Project schema, device schema, telemetry schema, alert schema
* Seed data
* Repositories
* Pagination
* PostgreSQL connectivity

*Note: PostgreSQL remains the current database. SQLite is only a possible future evaluation and not an active implementation.*

### PHASE 3: Flutter MVP

**STATUS: ✅ COMPLETED**

#### 3.1 Health API Integration

* Flutter to FastAPI connectivity, Dio integration, health endpoint verification

#### 3.2 Projects

* Project list, API integration, Riverpod provider, loading state, error state, empty state

#### 3.3 Devices

* Device list, project filtering, device detail, online/offline state, navigation flow

#### 3.4 Telemetry History

* REST telemetry integration, time range filtering, dynamic metrics, pagination, historical visualization

#### 3.5 Alerts

* Alert list, severity filtering, status filtering, device-specific alerts, pagination

#### 3.6 Dashboard

* Project context, device counts, online/offline summary, latest telemetry, alert summary, navigation, refresh

#### 3.7 Pitch Demo Mode

* Deterministic simulator, telemetry simulation, warning/critical/recovery scenarios, DEMO_MODE, branding and visual polish, LIVE DEMO indicator

*Note: Demo Mode is implemented as a demonstration feature. It must not be described as production realtime telemetry and is not the current development focus.*

### PHASE 4: Realtime IoT

**STATUS: 🚧 IN PROGRESS**

Phase 4 connects real devices, MQTT, backend persistence, Flutter realtime monitoring, and failover behavior.

#### 4.1 MQTT Architecture & Telemetry Contract

**STATUS: ✅ COMPLETED**

**Primary MQTT Broker**

* Eclipse Mosquitto
* Runs on the Edge Server
* Deployed through Docker

**Primary Realtime Path**
ESP32 → Primary Mosquitto → Flutter

**Backend Persistence Path**
ESP32 → Mosquitto → Backend MQTT Consumer → PostgreSQL

**Emergency Architecture**
Primary MQTT unavailable → Flutter fails over to Emergency MQTT Broker → local realtime monitoring continues

**Emergency Broker**
The emergency broker must:

* Be independent from the Edge Server failure domain
* Be hardware agnostic
* Support future deployment on different gateway platforms (e.g., Raspberry Pi, OpenWrt-compatible gateway or STB, x86 mini PC, MikroTik or equivalent gateway-capable device, another suitable Linux or gateway device)

*The hardware choice remains open. No specific emergency hardware platform has been selected.*

**MQTT Topic Convention**
`nicegas/{site_id}/{device_id}/{category}/{component}`

**Telemetry Payload**

* JSON payload
* ISO 8601 UTC timestamp
* Dynamic metrics
* Metric value
* Metric unit
* Device/site metadata derived from the MQTT topic

**MQTT Policies**

* Telemetry: QoS 0 or QoS 1
* Status: QoS 1
* Events: QoS 1
* Device/server status: retained
* High-volume telemetry: not retained
* Last Will and Testament used for offline status

**Security Direction**

* Anonymous access is development-only
* Production requires MQTT authentication
* Production requires TLS
* Credentials must not be hardcoded
* Production secrets must be managed securely

**Deferred Items**

* Offline telemetry replay
* Offline buffering
* Full production security hardening

#### 4.2 Backend MQTT Consumer

**STATUS: ✅ COMPLETED**

Implemented functionality:

* Asynchronous MQTT consumer using gmqtt
* FastAPI lifecycle integration
* MQTT topic routing
* Telemetry JSON validation
* Dynamic metric processing
* PostgreSQL persistence
* Device online/offline handling
* Event processing
* QoS 1 duplicate/idempotency handling
* Reconnect behavior
* Graceful shutdown

Validated flow: Test Publisher / ESP32 → Mosquitto → Backend MQTT Consumer → PostgreSQL

*Known technical debt (not blockers):*

* Current development identity mapping uses project/device names against MQTT identifiers
* Future stable machine-readable project/device codes may be desirable
* Offline persistence during failover remains deferred

#### 4.3A Flutter MQTT Realtime

**STATUS: ✅ COMPLETED**

Implemented functionality:

* Flutter MQTT client
* Primary broker connection
* Realtime telemetry state
* Project-scoped topic subscription
* Compound realtime key using device ID and component
* Separate broker status and device status
* Reconnect behavior
* Resubscribe behavior
* Realtime Dashboard overlay
* Realtime Device Detail
* REST baseline plus MQTT realtime layering
* Demo Mode compatibility

Architecture:
REST → baseline and historical data
MQTT → realtime overlay

*The Dashboard should retain baseline information even when MQTT is temporarily unavailable.*

#### 4.3B MQTT Primary / Emergency Failover

**STATUS: 🟡 PENDING VERIFICATION**

Current implementation:

* Primary broker configuration
* Emergency broker configuration
* BrokerRole
* Automatic failover
* Emergency mode
* Resubscription
* Primary recovery probing
* Anti-flapping
* Emergency dashboard indication

**Approved Failover Timing**

* Failover: 3 primary reconnect attempts, approximately 5 seconds apart, approximately 15 seconds before switching to emergency.
* Primary recovery: probe every 30 seconds, require 2 consecutive successful probes, return to primary only after stability confirmation.

**Verification Status**

* Automated/unit tests: ✅ COMPLETED
* Physical failover test: 🟡 PENDING (The physical topology prototype is intentionally deferred for approximately two days).

#### 4.4 Physical Prototype Topology

**STATUS: ⏳ PLANNED / NEXT REAL-WORLD TASK**

The next real-world task is to build a physical prototype topology that matches the intended failover architecture. The emergency broker must not share the same failure domain as the primary Edge Server.

```text
Local Plant Network / Wi-Fi AP
│
├── Flutter physical device
├── ESP32 or test publisher
├── Edge Server
│   └── Docker
│       └── Primary Mosquitto
│
└── Independent Gateway / Emergency Broker
    └── Emergency Mosquitto
```

*The prototype does not need to use the final hardware platform yet.*

#### 4.5 Physical Failover Verification

**STATUS: ⏳ PLANNED**

Planned test scenarios:

* **Normal Operation**: ESP32 or test publisher → Primary Mosquitto → Flutter
* **Primary Broker Failure**: Stop/disconnect primary broker, verify Flutter detects failure, attempts failover, connects to emergency broker, continues realtime monitoring, and restores project subscriptions.
* **Primary Recovery**: Restore primary broker, verify recovery probes, verify 2 consecutive successful probes, verify switch back to primary, verify subscriptions remain active, and verify no rapid broker flapping.
* **Failure-Domain Validation**: Verify primary broker is on Edge Server, emergency broker remains available when Edge Server is unavailable, and emergency broker is not hosted only on the same machine as the primary broker.

#### 4.6 ESP32 Firmware Integration

**STATUS: ⏳ PLANNED**

Planned work:

* Wi-Fi setup, device identity, NTP/time synchronization, MQTT client, primary broker configuration, emergency broker configuration, telemetry publishing, status publishing, Last Will, reconnect behavior, failover behavior, sensor integration, payload validation. (A test publisher may be used before final firmware is ready.)

#### 4.7 End-to-End IoT Validation

**STATUS: ⏳ PLANNED**

Target end-to-end flows:

* ESP32 → MQTT → Flutter realtime
* ESP32 → MQTT → Backend MQTT Consumer → PostgreSQL

Validation should confirm telemetry reaches Flutter in realtime, is persisted by the backend, device status is reflected correctly, alerts/events are processed, REST history and MQTT realtime overlay remain consistent, and failover does not break local realtime monitoring.

#### 4.8 Operator First-Run Configuration

**STATUS: ⏳ PLANNED**

Planned first-launch setup flow:
First launch → Operator setup → Primary MQTT endpoint → Emergency MQTT endpoint → Credentials/security settings → Test connection → Save configuration

#### 4.9 Offline Buffering & Data Continuity

**STATUS: ⏸️ DEFERRED**

Realtime failover and offline data continuity are separate concerns.

* Current behavior: Flutter realtime may continue through the emergency broker. PostgreSQL persistence may be unavailable if the backend/Edge Server is unavailable. Telemetry gaps may occur during a backend outage.
* Potential future solutions: ESP32 local buffering, gateway buffering, broker replay, backend resynchronization, sequence numbers, event timestamps and deduplication.

### PHASE 5: Production Security & Access Control

**STATUS: ⏳ PLANNED**

Planned security work:

* MQTT username/password authentication, MQTT TLS, certificate strategy, device credentials, operator authentication, JWT authentication, authorization, role-based access control, secret management, secure configuration storage, audit logging, production deployment hardening.
  *(Development anonymous MQTT access is not acceptable for production.)*

### PHASE 6: Alerting, Audible Alarm & Operator Flow

**STATUS: ✅ IMPLEMENTED IN FLUTTER APP**

Implemented capabilities in Flutter:
* Gojek-driver style urgent alert pop-up with animated pulsing radar rings.
* Continuous audible siren/sound effect (`beep_warning.mp3`) routed through alarm channel.
* Haptic feedback vibration (`HapticFeedback.heavyImpact()`).
* Two-step operator acknowledgment workflow: "KONFIRMASI & TANGANI" and "Buka di Log System".
* Anti-spam tracking to prevent repeated modal pop-ups for already acknowledged alert IDs.
* App settings toggle for emergency sound effects (`soundAlertsEnabled`).

### PHASE 7: N.E.X.A. AI Operational Companion (J.A.R.V.I.S. Mode)

**STATUS: ✅ IMPLEMENTED IN FLUTTER APP**

Implemented capabilities in Flutter:
* Dual interaction modes: Technical Chat Interface & Fullscreen Voice-driven LIVE Visualizer.
* Natural-language operational queries and real-time plant telemetry analysis.
* Text-to-Speech (TTS) integration with Auto-Speak toggle and adjustable speech rate.
* Telemetry context mapping across Biodigester, Purification, and Compression stages.

### PHASE 8: 3D Digital Twin Viewer & Visualization

**STATUS: ✅ IMPLEMENTED IN FLUTTER APP**

Implemented capabilities in Flutter:
* Interactive plant-wide 3D model viewer (`BioCNG_Plant.glb`) powered by `model_viewer_plus`.
* Node-specific 3D Digital Twins (`SensorNodeBiodigester.glb`, `SensorNodePurifikasi.glb`, `SensorNodeKompresi.glb`).
* Automated camera pivots and target focus for Biodigester, H2S Scrubber, Gas Holder, Buffer Tank, Compressor, and Gas Cylinder.

### PHASE 9: Cloud, Multi-Site & Production Scale

**STATUS: 🔮 FUTURE**

Possible future capabilities:

* Cloud deployment, multi-site support, remote access, centralized fleet management, tenant isolation, scalable telemetry ingestion, centralized observability, backup and disaster recovery, production monitoring, deployment automation.
  *(Cloud deployment is not currently active.)*

---

## Architecture

```text
                         INTERNET
                             │
                         Router / AP
                             │
             ┌───────────────┼────────────────┐
             │               │                │
        Flutter          ESP32 / Test      Edge Server (pc/Smartphone)
     Operator App         Publisher          Docker 
             │               │                │
             │               └──── MQTT ──────┤
             │                                │
             │                         Primary Mosquitto
             │                                │
             │                         Backend Consumer
             │                                │
             │                            PostgreSQL/(sqlte) if change
             │
             └──────────── MQTT realtime ─────┘
```

**Emergency path:**

```text
Primary broker unavailable
        ↓
Emergency MQTT broker
        ↓
Flutter continues local realtime monitoring
```

**Responsibilities:**

* AP/router provides network connectivity
* MQTT broker provides realtime messaging
* Edge Server hosts primary broker and backend services
* Backend Consumer persists telemetry and processes events
* PostgreSQL stores application and historical data
* Flutter is the operator client
* ESP32 publishes device telemetry and status
* Emergency broker provides continuity for local realtime monitoring

*The emergency broker must be independent from the primary Edge Server failure domain.*

## Data Flow

### Historical / REST Flow

Flutter → FastAPI → PostgreSQL

### Realtime Flow

ESP32 → MQTT Broker → Flutter

### Persistence Flow

ESP32 → MQTT Broker → Backend MQTT Consumer → PostgreSQL

### Failover Flow

Primary MQTT unavailable → Flutter reconnect attempts → Emergency MQTT Broker → realtime monitoring continues

### Recovery Flow

Primary MQTT restored → recovery probes → two consecutive successful probes → Flutter returns to primary → subscriptions restored

---

## Team Integration and Boundaries

The project is developed by a small team. Flutter UI/UX work may be developed in parallel by another team member, while backend, infrastructure, and MQTT work are handled separately.

The project emphasizes:

* Stable API contracts
* Stable MQTT contracts
* Architecture boundaries
* Source-of-truth responsibilities
* Careful integration between parallel workstreams
* Avoiding accidental changes to realtime infrastructure while merging UI work

Flutter UI work may be merged in parallel, but integration should be reviewed carefully around:

* `main.dart`
* App configuration
* Providers
* MQTT state
* MQTT service
* Dashboard page
* Device detail page
* Routing
* Environment variables
* Dart defines

UI merges must preserve existing realtime MQTT and failover behavior.

If the following files exist in the repository, they should be treated as architecture sources of truth:

* [README.md](README.md)
* [mqtt_convention.md](mqtt_convention.md)
* API contract documentation
* Project specification documents
* Environment/configuration documentation
