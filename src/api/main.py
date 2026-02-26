"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import AUTO_CREATE_DB
from ..core.db import init_db
from .routers import (
    systems,
    schemas,
    datasets,
    mappings,
    rule_sets,
    jobs,
    results,
    reference_datasets,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    if AUTO_CREATE_DB:
        init_db()
        logger.info("Database initialized")
    yield
    # Shutdown (if needed)


app = FastAPI(
    title="GenRecon API",
    description="Generic Data Reconciliation Platform API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(systems.router, prefix="/api/v1/systems", tags=["Systems"])
app.include_router(schemas.router, prefix="/api/v1/schemas", tags=["Schemas"])
app.include_router(datasets.router, prefix="/api/v1/datasets", tags=["Datasets"])
app.include_router(mappings.router, prefix="/api/v1/mappings", tags=["Mappings"])
app.include_router(
    reference_datasets.router,
    prefix="/api/v1/reference-datasets",
    tags=["Reference Datasets"],
)
app.include_router(rule_sets.router, prefix="/api/v1/rule-sets", tags=["Rule Sets"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(results.router, prefix="/api/v1/results", tags=["Results"])


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "genrecon-api"}
