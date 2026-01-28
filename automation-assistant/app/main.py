"""FastAPI application for Automation Assistant."""

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .automation import automation_generator, validate_automation_yaml
from .batch_doctor import CancelledException, batch_diagnosis_service
from .config import VERSION, config
from .diagnostic_storage import diagnostic_storage
from .doctor import automation_doctor
from .ha_automations import ha_automation_reader
from .ha_client import ha_client
from .insights_storage import insights_storage
from .llm.claude import AsyncClaudeClient
from .models import (
    ApplyFixResponse,
    AutomationRequest,
    AutomationResponse,
    BatchDiagnosisReport,
    ContextSummary,
    DeployAutomationRequest,
    DeployAutomationResponse,
    DiagnoseRequest,
    DiagnosisResponse,
    HAAutomationList,
    HAAutomationSummary,
    HealthResponse,
    Insight,
    InsightsList,
    ModifyAutomationRequest,
    SaveAutomationRequest,
    SavedAutomation,
    SavedAutomationList,
    ScheduleConfig,
    UpdateAutomationRequest,
    ValidationRequest,
    ValidationResponse,
)
from .scheduler import diagnosis_scheduler
from .storage import storage_manager

# Configure logging
LOG_LEVEL = getattr(logging, config.log_level.upper(), logging.INFO)
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Automation Assistant")
    logger.info("Using model: %s", config.model)
    logger.info("Using doctor model: %s", config.doctor_model_or_default)
    logger.info("API key configured: %s", config.is_configured)

    # Start the diagnosis scheduler
    diagnosis_scheduler.start()
    logger.info("Diagnosis scheduler started")

    yield

    # Cleanup
    diagnosis_scheduler.stop()
    await ha_client.close()
    logger.info("Automation Assistant stopped")


app = FastAPI(
    title="Automation Assistant",
    description="Create Home Assistant automations using natural language",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
# Try to serve from built frontend first, fall back to legacy index.html
static_path = Path(__file__).parent / "static"
dist_path = static_path / "dist"

# Mount dist assets if available, otherwise mount static root
if dist_path.exists():
    app.mount("/assets", StaticFiles(directory=dist_path / "assets"), name="assets")
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web UI."""
    # Try built frontend first
    dist_index = dist_path / "index.html"
    if dist_index.exists():
        response = FileResponse(dist_index)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # Fall back to legacy single-file frontend
    index_path = static_path / "index.html"
    if index_path.exists():
        response = FileResponse(index_path)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return HTMLResponse("<h1>Automation Assistant</h1><p>UI not found</p>")


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint for watchdog."""
    return HealthResponse(
        status="healthy",
        configured=config.is_configured,
    )


@app.get("/api/version")
async def get_version():
    """Get the add-on version."""
    return {"version": VERSION}


@app.post("/api/generate", response_model=AutomationResponse)
async def generate_automation(request: AutomationRequest):
    """Generate an automation from natural language."""
    if not config.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Claude API key not configured. Please configure in add-on settings.",
        )

    logger.info("Generating automation for: %s...", request.prompt[:100])
    result = await automation_generator.generate(request.prompt)

    if not result.success:
        logger.error("Generation failed: %s", result.error)

    return result


@app.post("/api/modify", response_model=AutomationResponse)
async def modify_automation(request: ModifyAutomationRequest):
    """Modify an existing automation using natural language."""
    if not config.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Claude API key not configured. Please configure in add-on settings.",
        )

    logger.info("Modifying automation with request: %s...", request.prompt[:100])
    result = await automation_generator.modify(request.existing_yaml, request.prompt)

    if not result.success:
        logger.error("Modification failed: %s", result.error)

    return result


@app.get("/api/context", response_model=ContextSummary)
async def get_context():
    """Get a summary of the available Home Assistant context."""
    summary = await automation_generator.get_context_summary()
    return ContextSummary(**summary)


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
        logger.info("Saved automation: %s", request.name)
        return SavedAutomation(**automation)
    except OSError as exc:
        logger.error("Failed to save automation: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
    logger.info("Updated automation: %s", automation_id)
    return SavedAutomation(**automation)


@app.delete("/api/automations/{automation_id}")
async def delete_automation(automation_id: str):
    """Delete a saved automation."""
    deleted = await storage_manager.delete(automation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Automation not found")
    logger.info("Deleted automation: %s", automation_id)
    return {"success": True}


# Deploy endpoints


@app.post("/api/deploy", response_model=DeployAutomationResponse)
async def deploy_automation(request: DeployAutomationRequest):
    """Deploy an automation directly to Home Assistant.

    This creates or updates an automation in HA and reloads automations.
    """
    # Parse the YAML content
    try:
        automation_config = yaml.safe_load(request.yaml_content)
        if not automation_config:
            raise HTTPException(status_code=400, detail="Empty YAML content")
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid YAML: {exc}"
        ) from exc

    # Extract or generate automation ID
    automation_id = request.automation_id
    if not automation_id:
        # Try to extract from YAML
        automation_id = automation_config.get("id")
    if not automation_id:
        # Generate a new UUID
        automation_id = str(uuid.uuid4())
        automation_config["id"] = automation_id

    # Check if this is a new automation or update
    existing = await ha_client.get_automation_config(automation_id)
    is_new = existing is None

    # Ensure the ID is set in the config
    automation_config["id"] = automation_id

    # Deploy to HA
    result = await ha_client.create_or_update_automation(
        automation_id, automation_config
    )

    if not result.get("success"):
        error_msg = result.get("error", "Unknown error")
        raise HTTPException(status_code=500, detail=f"Failed to deploy: {error_msg}")

    # Reload automations to apply changes
    reloaded = await ha_client.reload_automations()
    if not reloaded:
        logger.warning(
            "Automation saved but reload failed - may require manual reload"
        )

    action = "created" if is_new else "updated"
    alias = automation_config.get("alias", automation_id)
    logger.info(
        "Deployed automation '%s' (%s) - %s", alias, automation_id, action
    )

    return DeployAutomationResponse(
        success=True,
        automation_id=automation_id,
        message=f"Automation '{alias}' {action} successfully",
        is_new=is_new,
    )


# Doctor endpoints

@app.get("/api/ha-automations", response_model=HAAutomationList)
async def list_ha_automations():
    """List all automations from Home Assistant."""
    automations = await automation_doctor.list_automations()
    return HAAutomationList(
        automations=[HAAutomationSummary(**a) for a in automations],
        count=len(automations),
    )


@app.get("/api/ha-automations/{automation_id}")
async def get_ha_automation(automation_id: str):
    """Get a Home Assistant automation with its traces."""
    details = await automation_doctor.get_automation_details(automation_id)
    if not details.get("automation"):
        raise HTTPException(status_code=404, detail="Automation not found")
    return details


@app.post("/api/doctor/diagnose", response_model=DiagnosisResponse)
async def diagnose_automation(request: DiagnoseRequest):
    """Diagnose an automation and provide analysis."""
    if not config.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Claude API key not configured. Please configure in add-on settings.",
        )

    logger.info("Diagnosing automation: %s", request.automation_id)
    result = await automation_doctor.diagnose(request.automation_id)

    if not result.success:
        logger.error("Diagnosis failed: %s", result.error)

    return result


# Batch diagnosis endpoints


@app.post("/api/doctor/run-batch", response_model=BatchDiagnosisReport)
async def run_batch_diagnosis():
    """Manually trigger batch diagnosis of all automations."""
    if not config.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Claude API key not configured. Please configure in add-on settings.",
        )

    if batch_diagnosis_service.is_running:
        raise HTTPException(
            status_code=409,
            detail="A diagnosis is already running. Cancel it first or wait for it to complete.",
        )

    logger.info("Manual batch diagnosis triggered")
    try:
        result = await batch_diagnosis_service.run_batch_diagnosis(scheduled=False)
        return result
    except CancelledException as exc:
        logger.info("Batch diagnosis cancelled: %s", exc)
        raise HTTPException(
            status_code=409, detail="Batch diagnosis was cancelled"
        ) from exc
    except (RuntimeError, ValueError) as exc:
        logger.error("Batch diagnosis failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/doctor/cancel")
async def cancel_batch_diagnosis():
    """Cancel a running batch diagnosis."""
    if batch_diagnosis_service.cancel():
        return {"success": True, "message": "Cancellation requested"}
    raise HTTPException(
        status_code=400,
        detail="No diagnosis is currently running",
    )


@app.get("/api/doctor/status")
async def get_diagnosis_status():
    """Get the current status of batch diagnosis."""
    return {
        "is_running": batch_diagnosis_service.is_running,
    }


@app.get("/api/doctor/reports")
async def list_diagnosis_reports():
    """List all diagnosis reports (summaries only)."""
    reports = await diagnostic_storage.list_reports()
    return {"reports": reports, "count": len(reports)}


@app.get("/api/doctor/reports/latest")
async def get_latest_report():
    """Get the most recent full diagnosis report."""
    report = await diagnostic_storage.get_latest_report()
    if not report:
        raise HTTPException(status_code=404, detail="No diagnosis reports found")
    return report


@app.get("/api/doctor/reports/{run_id}")
async def get_report(run_id: str):
    """Get a specific diagnosis report by run ID."""
    report = await diagnostic_storage.get_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


# Schedule endpoints


@app.get("/api/doctor/schedule", response_model=ScheduleConfig)
async def get_schedule():
    """Get current schedule configuration."""
    config_data = diagnosis_scheduler.get_schedule()
    return ScheduleConfig(**config_data)


class ScheduleUpdateRequest(BaseModel):
    """Request model for updating schedule."""
    time: Optional[str] = None
    enabled: Optional[bool] = None
    frequency: Optional[str] = None
    day_of_week: Optional[str] = None
    day_of_month: Optional[int] = None


@app.put("/api/doctor/schedule", response_model=ScheduleConfig)
async def update_schedule(request: ScheduleUpdateRequest):
    """Update scheduled run time and/or enabled status."""
    try:
        updates = request.model_dump()
        config_data = diagnosis_scheduler.update_schedule(updates)
        return ScheduleConfig(**config_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# Insights endpoints


@app.get("/api/doctor/insights", response_model=InsightsList)
async def get_insights():
    """Get all insights, separated by category (single/multi)."""
    single = await insights_storage.get_single_automation_insights()
    multi = await insights_storage.get_multi_automation_insights()
    unresolved = await insights_storage.get_unresolved_count()

    return InsightsList(
        single_automation=[Insight(**i) for i in single],
        multi_automation=[Insight(**i) for i in multi],
        total_count=len(single) + len(multi),
        unresolved_count=unresolved,
    )


@app.get("/api/doctor/insights/single")
async def get_single_insights():
    """Get insights for single automation issues."""
    insights = await insights_storage.get_single_automation_insights()
    return {"insights": insights, "count": len(insights)}


@app.get("/api/doctor/insights/multi")
async def get_multi_insights():
    """Get insights for multi-automation conflicts."""
    insights = await insights_storage.get_multi_automation_insights()
    return {"insights": insights, "count": len(insights)}


@app.put("/api/doctor/insights/{insight_id}/resolve")
async def resolve_insight(insight_id: str, resolved: bool = Query(True)):
    """Mark an insight as resolved or unresolved."""
    success = await insights_storage.mark_resolved(insight_id, resolved)
    if not success:
        raise HTTPException(status_code=404, detail="Insight not found")
    return {"success": True, "insight_id": insight_id, "resolved": resolved}


@app.delete("/api/doctor/insights/{insight_id}")
async def delete_insight(insight_id: str):
    """Delete an insight permanently."""
    success = await insights_storage.delete_insight(insight_id)
    if not success:
        raise HTTPException(status_code=404, detail="Insight not found")
    return {"success": True, "insight_id": insight_id}


@app.post("/api/doctor/insights/{insight_id}/fix")
async def get_insight_fix(insight_id: str):
    """Get a suggested fix for an insight."""
    if not config.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Claude API key not configured.",
        )

    # Get the insight
    all_insights = await insights_storage.get_all()
    insight = next(
        (item for item in all_insights if item.get("insight_id") == insight_id),
        None,
    )
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    # Get the automation(s) involved
    automations = []
    for auto_id in insight.get("automation_ids", []):
        auto = await ha_automation_reader.get_automation(auto_id)
        if auto:
            automations.append(auto)

    if not automations:
        raise HTTPException(
            status_code=404, detail="Could not find the automation(s)"
        )

    # Build prompt for fix suggestion
    automation_blocks = []
    for automation in automations:
        alias = automation.get("alias", "Unnamed")
        automation_id = automation.get("id")
        automation_yaml = yaml.dump(
            automation, default_flow_style=False, sort_keys=False
        )
        automation_blocks.append(
            f"# {alias} (id: {automation_id})\n```yaml\n"
            f"{automation_yaml}\n```"
        )
    automations_yaml = "\n\n".join(automation_blocks)

    prompt = (
        "Fix this Home Assistant automation issue.\n\n"
        "## Issue\n"
        f"**Type:** {insight.get('insight_type', 'unknown')}\n"
        f"**Title:** {insight.get('title', '')}\n"
        f"**Description:** {insight.get('description', '')}\n\n"
        "## Automation(s)\n"
        f"{automations_yaml}\n\n"
        "## Your Task\n"
        "Provide a corrected version of the automation(s) that fixes the issue.\n"
        "- Return ONLY the corrected YAML, no explanations\n"
        "- If multiple automations are involved, separate them with ---\n"
        "- Keep the original id and alias\n"
        "- Only change what's necessary to fix the issue"
    )

    llm = AsyncClaudeClient(model=config.doctor_model_or_default)
    fix_suggestion = await llm.generate_automation(
        "You are a Home Assistant automation expert. Return only valid YAML.",
        prompt,
    )

    return {
        "insight_id": insight_id,
        "automation_ids": insight.get("automation_ids", []),
        "automation_names": insight.get("automation_names", []),
        "issue": insight.get("description", ""),
        "fix_suggestion": fix_suggestion,
    }


class ApplyFixRequest(BaseModel):
    """Request model for applying a fix."""
    yaml_content: str


@app.post("/api/doctor/insights/{insight_id}/apply", response_model=ApplyFixResponse)
async def apply_insight_fix(insight_id: str, request: ApplyFixRequest):
    """Apply a fix suggestion directly to Home Assistant.

    Takes the fixed YAML and deploys it to HA, then marks the insight as resolved.
    """
    # Get the insight to know which automation(s) are affected
    all_insights = await insights_storage.get_all()
    insight = next(
        (item for item in all_insights if item.get("insight_id") == insight_id),
        None,
    )
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    # Parse the YAML - may contain multiple documents separated by ---
    yaml_content = request.yaml_content
    # Strip markdown code blocks if present
    yaml_content = (
        yaml_content.replace("```yaml", "")
        .replace("```yml", "")
        .replace("```", "")
        .strip()
    )

    try:
        documents = list(yaml.safe_load_all(yaml_content))
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=400, detail=f"Invalid YAML: {exc}"
        ) from exc

    if not documents:
        raise HTTPException(status_code=400, detail="No automation found in YAML")

    # Deploy each automation
    deployed_ids: list[str] = []
    errors: list[str] = []

    for doc in documents:
        if not doc:
            continue

        automation_id = doc.get("id")
        if not automation_id:
            errors.append("Automation missing 'id' field")
            continue

        # Ensure the ID is in the config
        doc["id"] = automation_id

        result = await ha_client.create_or_update_automation(automation_id, doc)
        if result.get("success"):
            deployed_ids.append(automation_id)
            logger.info("Applied fix to automation: %s", automation_id)
        else:
            errors.append(
                f"Failed to update {automation_id}: "
                f"{result.get('error', 'Unknown error')}"
            )

    if not deployed_ids:
        joined_errors = "; ".join(errors) if errors else "No automations deployed"
        raise HTTPException(
            status_code=500,
            detail=f"Failed to apply fix: {joined_errors}",
        )

    # Reload automations
    reloaded = await ha_client.reload_automations()
    if not reloaded:
        errors.append(
            "Automations saved but reload failed - may require manual reload"
        )

    # Mark the insight as resolved
    await insights_storage.mark_resolved(insight_id, True)

    return ApplyFixResponse(
        success=True,
        automation_ids=deployed_ids,
        message=f"Fix applied to {len(deployed_ids)} automation(s)",
        errors=errors,
    )
