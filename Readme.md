# NICEGAS Server

NICEGAS is a Bio-CNG monitoring and management system. This project contains the backend and local infrastructure that will support the NICEGAS Flutter mobile application.

The mobile application is developed separately in Android Studio. The `nicegas-server` project is developed primarily in VS Code and provides the local Docker-based foundation for the backend, database, and MQTT communication.

## Project Overview

The server project is being established during Phase 2 of the NICEGAS development plan. Its initial purpose is to provide a reproducible local environment in which:

- A FastAPI backend exposes the NICEGAS REST API.
- PostgreSQL stores application data.
- Eclipse Mosquitto provides MQTT messaging for device communication.
- The backend coordinates API requests, database access, and MQTT integration.

The initial infrastructure is intentionally limited to the MVP foundation. Authentication, AI integration, 3D Digital Twin features, and cloud infrastructure are outside the initial setup.

## System Architecture

```text
Flutter Mobile App
	|
	| HTTP / REST API
	v
FastAPI Backend
	|
	+------------------> PostgreSQL Database
	|
	+------------------> MQTT Broker
				  |
				  v
				ESP32
```

The Flutter application communicates with the FastAPI backend over HTTP. The backend reads and writes PostgreSQL data and communicates with ESP32 devices through the MQTT broker.

The AI model is planned to run locally on a separate laptop in a later phase. It is not part of the current server infrastructure.

## Repository Structure

The current repository structure is:

```text
nicegas-server/
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── postgres/
│   └── init/
└── mqtt/
    └── mosquitto.conf
```

Phase 2.1 currently implements the Docker Compose foundation only. The `postgres/init/` directory is reserved for future initialization scripts; no business schema has been added. FastAPI backend files will be added in Phase 2.2.

The Flutter application is maintained separately:

```text
nicegas-app/
└── Flutter mobile application
```

## Technology Stack

| Area | Technology |
| --- | --- |
| Mobile application | Flutter |
| Mobile state management | Riverpod |
| Mobile REST client | Dio |
| Backend API | Python with FastAPI |
| Database | PostgreSQL |
| Messaging | Eclipse Mosquitto MQTT broker |
| Infrastructure | Docker Compose |
| Device platform | ESP32 |
| AI integration | Local model on a separate laptop in a future phase |

Cloud infrastructure and Kubernetes are not part of the current MVP architecture.

## Development Requirements

The server project is intended to be developed with:

- Docker Desktop with Docker Compose support
- VS Code
- Git
- Access to the NICEGAS source repositories

The Flutter toolchain and Android Studio are required for mobile application development, but are separate from the server infrastructure setup. No cloud account is required for the local Phase 2 environment.

## Implemented Docker Services

Docker Compose currently orchestrates exactly these services:

| Service | Role |
| --- | --- |
| `postgres` | Runs PostgreSQL for persistent application data. |
| `mqtt` | Runs Eclipse Mosquitto for MQTT communication with ESP32 devices. |

The backend is not yet implemented. PostgreSQL and MQTT communicate through the dedicated `nicegas-network` Docker network. Host access uses the ports defined in `.env`; the development defaults are PostgreSQL `5432` and MQTT `1883`. Container-to-container access uses `postgres:5432` and `mqtt:1883`.

See [`NICEGAS_Server/README.md`](NICEGAS_Server/README.md) for setup, commands, healthchecks, volumes, and development-only security limitations.

## Phase 2 Goals

Phase 2, **Local Infrastructure & Backend Foundation**, is underway. Phase 2.1 has established the local Docker foundation. Its remaining goals include:

1. Establish the Docker development environment.
2. Run the FastAPI backend in Docker.
3. Run PostgreSQL in Docker.
4. Run the MQTT broker in Docker.
5. Establish communication between the backend, database, and MQTT broker.
6. Provide REST endpoints that follow the existing NICEGAS API contract.
7. Prepare for a later connection to the Flutter application.

## Initial API Endpoints

The minimum initial API surface is:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Verify that the backend is running. |
| `GET` | `/projects` | List Bio-CNG plants or projects. |
| `GET` | `/devices` | List hardware devices, with optional project filtering when supported by the contract. |
| `GET` | `/devices/{deviceId}` | Return details for a specific device. |

The frozen API contract also defines the `/v1` versioning convention, JSON responses, ISO 8601 UTC timestamps, pagination formats, error formats, and additional future endpoints such as authentication, telemetry, and alerts. The contract is documented in the Flutter project at `itenice_bio_cng/docs/api_contract.md`.

Authentication is defined by the frozen contract as JWT Bearer authentication. Because authentication is explicitly excluded from the initial infrastructure setup, the Phase 2 local access policy and the point at which JWT enforcement begins require Project Lead approval.

## Development Workflow

For the implemented Phase 2.1 foundation, run the commands from `NICEGAS_Server/`:

```powershell
Copy-Item .env.example .env
docker compose up -d
docker compose ps
docker compose logs
docker compose down
```

Named volumes preserve service data after `docker compose down`. Use `docker compose down -v` only when intentionally removing local data. The environment is for local development only; production authentication, TLS, and public exposure are not configured.

Development should proceed in small, verifiable steps:

1. Start the PostgreSQL and MQTT services.
2. Start the FastAPI backend through Docker Compose.
3. Verify the health endpoint.
4. Verify backend connectivity to PostgreSQL and MQTT.
5. Add and test the initial project and device endpoints against the frozen API contract.
6. Connect the separately developed Flutter application after the local API is stable.

The FastAPI backend and Flutter-to-backend workflow remain future work.

## Current Project Status

| Area | Status |
| --- | --- |
| Phase 0: Flutter Foundation | **Completed** |
| Phase 1: System Configuration & Contracts | **Completed and frozen** |
| Phase 2: Local Infrastructure & Backend Foundation | **In progress** |
| Phase 2.1: Docker foundation | **Implemented** |
| Docker Compose environment | **Implemented: PostgreSQL and MQTT only** |
| FastAPI backend | Planned for Phase 2 |
| PostgreSQL service | **Implemented for local development** |
| MQTT broker service | **Implemented for local development** |
| Flutter-to-backend integration | Future Phase 2 follow-up |
| Authentication | Future work; excluded from initial infrastructure setup |
| AI model integration | Future work |
| 3D Digital Twin | Future work |
| Cloud deployment | Not part of the current MVP |

## Future Roadmap

After the local backend foundation is stable, planned areas include:

1. Connect the Flutter application to the local REST API.
2. Implement JWT authentication and authorization in accordance with the frozen contract.
3. Add telemetry and alert endpoints and connect them to persisted data.
4. Expand MQTT device communication and ESP32 integration.
5. Integrate the locally hosted AI model on a separate laptop.
6. Develop 3D Digital Twin capabilities.
7. Define a later deployment strategy, if cloud infrastructure becomes necessary.

The roadmap does not change the current architecture decision: Docker Compose, FastAPI, PostgreSQL, and Eclipse Mosquitto remain the approved Phase 2 foundation.

## Related Documentation

- [NICEGAS API Contract](itenice_bio_cng/docs/api_contract.md)
- [NICEGAS Environment Setup](itenice_bio_cng/docs/environment_setup.md)

## Project Lead Approvals Still Required

The following points are intentionally left open for approval before implementation details are finalized:

- Whether initial local Phase 2 endpoints are unauthenticated or use a temporary development authentication policy, given the frozen contract's JWT requirement.
- The local development ports and service connection settings.
- The initial PostgreSQL data model and seed-data policy.
- The MQTT topic naming and device-message conventions for the backend-to-ESP32 integration.
