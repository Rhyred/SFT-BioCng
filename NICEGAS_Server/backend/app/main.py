import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.devices import router as devices_router
from app.api.telemetry import router as telemetry_router
from app.api.alerts import router as alerts_router

# Configure basic application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NICEGAS API",
    description="Backend API for the NICEGAS project",
    version="0.1.0",
)

# CORS configuration - document intended approach
# For production, this should be restricted to the actual frontend domains.
# For local development, we allow all origins, but this can be restricted via env vars.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["Health"])
app.include_router(projects_router, prefix="/projects", tags=["Projects"])
app.include_router(devices_router, prefix="/devices", tags=["Devices"])
app.include_router(telemetry_router, prefix="/telemetry", tags=["Telemetry"])
app.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up NICEGAS API...")
    
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down NICEGAS API...")
