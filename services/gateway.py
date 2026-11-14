# =============================================================================
# AI Memory Pipeline - API Gateway
# =============================================================================
# Provides unified entry point for all pipeline services
# =============================================================================

import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gateway")

# Initialize FastAPI app
app = FastAPI(
    title="AI Memory Pipeline API",
    description="Unified entry point for document processing and memory management",
    version="1.0.0"
)


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for container orchestration."""
    return HealthResponse(
        status="healthy",
        service="ai-memory-pipeline-gateway",
        timestamp="2026-11-14T22:00:00Z"
    )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AI Memory Pipeline",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "/health": "Health check",
            "/api/v1/process": "Process documents",
            "/api/v1/search": "Search memories",
            "/api/v1/status": "Service status"
        }
    }


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("AI Memory Pipeline Gateway starting up")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("AI Memory Pipeline Gateway shutting down")
