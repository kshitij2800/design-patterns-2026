from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from scalar_fastapi import get_scalar_api_reference
from interfaces.api.devices import router as devices_router
from interfaces.api.locations import router as locations_router

from infrastructure.settings import settings
from interfaces.api.health import router as health_router
from interfaces.api.sensors import router as sensors_router

app = FastAPI(
    title="Smart Greenhouse API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router)
app.include_router(sensors_router)
app.include_router(locations_router)
app.include_router(devices_router)

# Discovery root
@app.get("/", include_in_schema=False)
def root():
    return JSONResponse({
        "message": "Smart Greenhouse API",
        "api_reference": "/scalar",
        "openapi": "/openapi.json",
    })


# Scalar UI
@app.get("/scalar", include_in_schema=False)
def scalar_ui():
    return get_scalar_api_reference(
        openapi_url="/openapi.json",
        title="Smart Greenhouse API",
    )