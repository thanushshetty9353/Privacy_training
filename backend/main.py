"""
Privacy-Preserving Federated Learning Platform — FastAPI Application
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import init_db

# ── Routers ───────────────────────────────────────────────────────────
from backend.routers import (
    auth_routes,
    organizations,
    datasets,
    training,
    models,
    audit,
    dashboard,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    # Create tables
    await init_db()
    # Ensure model storage directory exists
    os.makedirs(settings.MODEL_STORAGE_DIR, exist_ok=True)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "A privacy-preserving data sharing platform using "
        "Federated Learning, Differential Privacy, and Secure Aggregation."
    ),
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Audit‐logging middleware ──────────────────────────────────────────
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    response = await call_next(request)
    # Lightweight: log all non-GET requests at the HTTP level
    if request.method not in ("GET", "OPTIONS", "HEAD"):
        print(
            f"[AUDIT] {request.method} {request.url.path} "
            f"→ {response.status_code} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
    return response


# ── Register routers ─────────────────────────────────────────────────
app.include_router(auth_routes.router)
app.include_router(organizations.router)
app.include_router(datasets.router)
app.include_router(training.router)
app.include_router(models.router)
app.include_router(audit.router)
app.include_router(dashboard.router)


# ── Health check ──────────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


# ── Root ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Privacy-Preserving Federated Learning Platform API",
        "docs": "/docs",
        "version": settings.APP_VERSION,
    }
