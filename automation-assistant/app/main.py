"""FastAPI application for Automation Assistant."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .automation import automation_generator, validate_automation_yaml
from .config import config
from .ha_client import ha_client
from .models import (
    AutomationRequest,
    AutomationResponse,
    ContextSummary,
    HealthResponse,
    ValidationRequest,
    ValidationResponse,
)

# Configure logging
log_level = getattr(logging, config.log_level.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Automation Assistant")
    logger.info(f"Using model: {config.model}")
    logger.info(f"API key configured: {config.is_configured}")
    yield
    # Cleanup
    await ha_client.close()
    logger.info("Automation Assistant stopped")


app = FastAPI(
    title="Automation Assistant",
    description="Create Home Assistant automations using natural language",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web UI."""
    index_path = static_path / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>Automation Assistant</h1><p>UI not found</p>")


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint for watchdog."""
    return HealthResponse(
        status="healthy",
        configured=config.is_configured,
    )


@app.post("/api/generate", response_model=AutomationResponse)
async def generate_automation(request: AutomationRequest):
    """Generate an automation from natural language."""
    if not config.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Claude API key not configured. Please configure in add-on settings.",
        )

    logger.info(f"Generating automation for: {request.prompt[:100]}...")
    result = await automation_generator.generate(request.prompt)

    if not result.success:
        logger.error(f"Generation failed: {result.error}")

    return result


@app.get("/api/context", response_model=ContextSummary)
async def get_context():
    """Get a summary of the available Home Assistant context."""
    try:
        summary = await automation_generator.get_context_summary()
        return ContextSummary(**summary)
    except Exception as e:
        logger.error(f"Failed to get context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/validate", response_model=ValidationResponse)
async def validate_yaml(request: ValidationRequest):
    """Validate automation YAML syntax."""
    return validate_automation_yaml(request.yaml_content)
