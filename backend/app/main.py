from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import os
from app.database import connect_to_mongo, close_mongo_connection
from app.routers import sensors, reports, forecast, integrity, alerts, auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()

app = FastAPI(
    title="Federated Climate Action Platform API",
    description="Backend API for the Climate Action Platform Prototype",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration supporting credentials (cookies & authorization headers)
allowed_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(sensors.router, prefix="/api/sensors", tags=["Sensors"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(forecast.router, prefix="/api/forecast", tags=["Forecast"])
app.include_router(integrity.router, prefix="/api/integrity", tags=["Integrity"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the Climate Resilience API. Visit /docs for the API documentation."}
