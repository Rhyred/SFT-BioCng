# NICEGAS Server

This directory contains the Phase 2.1 local Docker foundation for NICEGAS. The current implementation runs PostgreSQL and Eclipse Mosquitto only. The FastAPI backend will be added in Phase 2.2.

## Services

| Service | Host access | Container hostname | Purpose |
| --- | --- | --- | --- |
| PostgreSQL | `localhost:5432` | `postgres:5432` | Persistent application database |
| MQTT | `localhost:1883` | `mqtt:1883` | Local device messaging |

Both services use the dedicated `nicegas-network` Docker network. Containers must use the service hostnames `postgres` and `mqtt`, not `localhost`.

The MQTT configuration follows the approved Phase 1 topic hierarchy:

```text
nicegas/{site_id}/{device_id}/{category}/{component}
```

## Requirements

- Docker Desktop with Docker Compose support
- VS Code

## Configuration

Create a local environment file from the example:

```powershell
Copy-Item .env.example .env
```

Adjust the values in `.env` for local development if necessary. `.env` is ignored by Git and must not contain production credentials.

## Start and Stop

Start both services in detached mode:

```powershell
docker compose up -d
```

Stop the services while retaining named-volume data:

```powershell
docker compose down
```

To intentionally remove the persisted local data as well:

```powershell
docker compose down -v
```

## Inspection and Verification

View service status:

```powershell
docker compose ps
```

View combined logs:

```powershell
docker compose logs
```

View one service's logs:

```powershell
docker compose logs postgres
docker compose logs mqtt
```

The Compose healthchecks use `pg_isready` for PostgreSQL and a real local MQTT publish for Mosquitto. PostgreSQL can also be checked directly with:

```powershell
docker compose exec postgres pg_isready -U $env:POSTGRES_USER -d $env:POSTGRES_DB
```

The MQTT broker is reachable from the host at `localhost:1883` and from a future backend container at `mqtt:1883`.

## Storage

Named Docker volumes preserve data after `docker compose down`:

- `nicegas-postgres-data`
- `nicegas-mqtt-data`
- `nicegas-mqtt-log`

Use `docker compose down -v` only when intentionally deleting the local database and MQTT state.

## Security Scope

This is a local development environment. Mosquitto anonymous access is intentionally enabled, and TLS, production authentication, cloud IAM, and public exposure are not implemented. Do not expose this configuration to an untrusted network or reuse its credentials in production.

## Database Migrations & Seeding

The application uses Alembic for database migrations. The initial schema is already generated.

To run migrations to the latest version:
```powershell
docker compose exec backend alembic upgrade head
```

To seed the database with local development data:
```powershell
docker compose exec backend python seed_data.py
```

## API Endpoints

The Core REST API is exposed at `http://localhost:8000`:
- `GET /health`
- `GET /projects`
- `GET /devices`
- `GET /devices/{deviceId}`
- `GET /telemetry`
- `GET /alerts`

Authentication is intentionally deferred to a later phase. The API is accessible without a token.
MQTT ingestion is not yet connected to the database. Telemetry data can be populated via `seed_data.py`.

## Current Status

- Phase 0: Flutter Foundation — completed.
- Phase 1: System Configuration & Contracts — completed and frozen.
- Phase 2.1: Docker Foundation — completed.
- Phase 2.2: FastAPI Backend — completed.
- **Phase 2.3: Database Schema & Core REST API — IMPLEMENTED.**

### Future Features
- Authentication (JWT)
- ESP32 MQTT to PostgreSQL integration
- Digital Twin
- AI Predictions
- Flutter Integration
