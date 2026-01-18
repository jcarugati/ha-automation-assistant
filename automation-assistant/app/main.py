"""FastAPI application for Automation Assistant."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .automation import automation_generator, validate_automation_yaml
from .config import config
from .doctor import automation_doctor
from .ha_client import ha_client
from .models import (
    AutomationRequest,
    AutomationResponse,
    ContextSummary,
    DiagnoseRequest,
    DiagnosisResponse,
    HAAutomationList,
    HAAutomationSummary,
    HealthResponse,
    SaveAutomationRequest,
    SavedAutomation,
    SavedAutomationList,
    UpdateAutomationRequest,
    ValidationRequest,
    ValidationResponse,
)
from .storage import storage_manager

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


@app.get("/api/automations", response_model=SavedAutomationList)
async def list_automations():
    """List all saved automations."""
    automations = await storage_manager.list()
    return SavedAutomationList(automations=automations, count=len(automations))


@app.post("/api/automations", response_model=SavedAutomation)
async def save_automation(request: SaveAutomationRequest):
    """Save a new automation."""
    try:
        automation = await storage_manager.save(
            name=request.name,
            prompt=request.prompt,
            yaml_content=request.yaml_content,
        )
        logger.info(f"Saved automation: {request.name}")
        return SavedAutomation(**automation)
    except Exception as e:
        logger.error(f"Failed to save automation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/automations/{automation_id}", response_model=SavedAutomation)
async def get_automation(automation_id: str):
    """Get a specific saved automation."""
    automation = await storage_manager.get(automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    return SavedAutomation(**automation)


@app.put("/api/automations/{automation_id}", response_model=SavedAutomation)
async def update_automation(automation_id: str, request: UpdateAutomationRequest):
    """Update an existing automation."""
    automation = await storage_manager.update(
        automation_id=automation_id,
        prompt=request.prompt,
        yaml_content=request.yaml_content,
    )
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    logger.info(f"Updated automation: {automation_id}")
    return SavedAutomation(**automation)


@app.delete("/api/automations/{automation_id}")
async def delete_automation(automation_id: str):
    """Delete a saved automation."""
    deleted = await storage_manager.delete(automation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Automation not found")
    logger.info(f"Deleted automation: {automation_id}")
    return {"success": True}


# Doctor endpoints

@app.get("/api/ha-automations", response_model=HAAutomationList)
async def list_ha_automations():
    """List all automations from Home Assistant."""
    try:
        automations = await automation_doctor.list_automations()
        return HAAutomationList(
            automations=[HAAutomationSummary(**a) for a in automations],
            count=len(automations),
        )
    except Exception as e:
        logger.error(f"Failed to list HA automations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ha-automations/{automation_id}")
async def get_ha_automation(automation_id: str):
    """Get a Home Assistant automation with its traces."""
    try:
        details = await automation_doctor.get_automation_details(automation_id)
        if not details.get("automation"):
            raise HTTPException(status_code=404, detail="Automation not found")
        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get HA automation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/doctor/diagnose", response_model=DiagnosisResponse)
async def diagnose_automation(request: DiagnoseRequest):
    """Diagnose an automation and provide analysis."""
    if not config.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Claude API key not configured. Please configure in add-on settings.",
        )

    logger.info(f"Diagnosing automation: {request.automation_id}")
    result = await automation_doctor.diagnose(request.automation_id)

    if not result.success:
        logger.error(f"Diagnosis failed: {result.error}")

    return result
