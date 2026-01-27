"""FastAPI application for Automation Assistant."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .automation import automation_generator, validate_automation_yaml
from .batch_doctor import batch_diagnosis_service
from .config import VERSION, config
from .diagnostic_storage import diagnostic_storage
from .doctor import automation_doctor
from .ha_client import ha_client
from .insights_storage import insights_storage
from .models import (
    ApplyFixResponse,
    AutomationRequest,
    AutomationResponse,
    BatchDiagnosisReport,
    BatchReportSummary,
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
    logger.info(f"Using doctor model: {config.doctor_model_or_default}")
    logger.info(f"API key configured: {config.is_configured}")

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

    logger.info(f"Generating automation for: {request.prompt[:100]}...")
    result = await automation_generator.generate(request.prompt)

    if not result.success:
        logger.error(f"Generation failed: {result.error}")

    return result


@app.post("/api/modify", response_model=AutomationResponse)
async def modify_automation(request: ModifyAutomationRequest):
    """Modify an existing automation using natural language."""
    if not config.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Claude API key not configured. Please configure in add-on settings.",
        )

    logger.info(f"Modifying automation with request: {request.prompt[:100]}...")
    result = await automation_generator.modify(request.existing_yaml, request.prompt)

    if not result.success:
        logger.error(f"Modification failed: {result.error}")

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


# Deploy endpoints


@app.post("/api/deploy", response_model=DeployAutomationResponse)
async def deploy_automation(request: DeployAutomationRequest):
    """Deploy an automation directly to Home Assistant.

    This creates or updates an automation in HA and reloads automations.
    """
    import uuid
    import yaml

    # Parse the YAML content
    try:
        automation_config = yaml.safe_load(request.yaml_content)
        if not automation_config:
            raise HTTPException(status_code=400, detail="Empty YAML content")
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")

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
    result = await ha_client.create_or_update_automation(automation_id, automation_config)

    if not result.get("success"):
        error_msg = result.get("error", "Unknown error")
        raise HTTPException(status_code=500, detail=f"Failed to deploy: {error_msg}")

    # Reload automations to apply changes
    reloaded = await ha_client.reload_automations()
    if not reloaded:
        logger.warning("Automation saved but reload failed - may require manual reload")

    action = "created" if is_new else "updated"
    alias = automation_config.get("alias", automation_id)
    logger.info(f"Deployed automation '{alias}' ({automation_id}) - {action}")

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
    except Exception as e:
        logger.error(f"Batch diagnosis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/doctor/cancel")
async def cancel_batch_diagnosis():
    """Cancel a running batch diagnosis."""
    if batch_diagnosis_service.cancel():
        return {"success": True, "message": "Cancellation requested"}
    else:
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
    try:
        reports = await diagnostic_storage.list_reports()
        return {"reports": reports, "count": len(reports)}
    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/doctor/reports/latest")
async def get_latest_report():
    """Get the most recent full diagnosis report."""
    try:
        report = await diagnostic_storage.get_latest_report()
        if not report:
            raise HTTPException(status_code=404, detail="No diagnosis reports found")
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/doctor/reports/{run_id}")
async def get_report(run_id: str):
    """Get a specific diagnosis report by run ID."""
    try:
        report = await diagnostic_storage.get_report(run_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        config_data = diagnosis_scheduler.update_schedule(
            time=request.time,
            enabled=request.enabled,
            frequency=request.frequency,
            day_of_week=request.day_of_week,
            day_of_month=request.day_of_month,
        )
        return ScheduleConfig(**config_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Insights endpoints


@app.get("/api/doctor/insights", response_model=InsightsList)
async def get_insights():
    """Get all insights, separated by category (single/multi)."""
    try:
        single = await insights_storage.get_single_automation_insights()
        multi = await insights_storage.get_multi_automation_insights()
        unresolved = await insights_storage.get_unresolved_count()

        return InsightsList(
            single_automation=[Insight(**i) for i in single],
            multi_automation=[Insight(**i) for i in multi],
            total_count=len(single) + len(multi),
            unresolved_count=unresolved,
        )
    except Exception as e:
        logger.error(f"Failed to get insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/doctor/insights/single")
async def get_single_insights():
    """Get insights for single automation issues."""
    try:
        insights = await insights_storage.get_single_automation_insights()
        return {"insights": insights, "count": len(insights)}
    except Exception as e:
        logger.error(f"Failed to get single insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/doctor/insights/multi")
async def get_multi_insights():
    """Get insights for multi-automation conflicts."""
    try:
        insights = await insights_storage.get_multi_automation_insights()
        return {"insights": insights, "count": len(insights)}
    except Exception as e:
        logger.error(f"Failed to get multi insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/doctor/insights/{insight_id}/resolve")
async def resolve_insight(insight_id: str, resolved: bool = Query(True)):
    """Mark an insight as resolved or unresolved."""
    try:
        success = await insights_storage.mark_resolved(insight_id, resolved)
        if not success:
            raise HTTPException(status_code=404, detail="Insight not found")
        return {"success": True, "insight_id": insight_id, "resolved": resolved}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve insight {insight_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/doctor/insights/{insight_id}")
async def delete_insight(insight_id: str):
    """Delete an insight permanently."""
    try:
        success = await insights_storage.delete_insight(insight_id)
        if not success:
            raise HTTPException(status_code=404, detail="Insight not found")
        return {"success": True, "insight_id": insight_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete insight {insight_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/doctor/insights/{insight_id}/fix")
async def get_insight_fix(insight_id: str):
    """Get a suggested fix for an insight."""
    if not config.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Claude API key not configured.",
        )

    try:
        # Get the insight
        all_insights = await insights_storage.get_all()
        insight = next((i for i in all_insights if i.get("insight_id") == insight_id), None)
        if not insight:
            raise HTTPException(status_code=404, detail="Insight not found")

        # Get the automation(s) involved
        from .ha_automations import ha_automation_reader
        from .llm.claude import AsyncClaudeClient

        automations = []
        for auto_id in insight.get("automation_ids", []):
            auto = await ha_automation_reader.get_automation(auto_id)
            if auto:
                automations.append(auto)

        if not automations:
            raise HTTPException(status_code=404, detail="Could not find the automation(s)")

        # Build prompt for fix suggestion
        import yaml
        automations_yaml = "\n\n".join([
            f"# {a.get('alias', 'Unnamed')} (id: {a.get('id')})\n```yaml\n{yaml.dump(a, default_flow_style=False)}\n```"
            for a in automations
        ])

        prompt = f"""Fix this Home Assistant automation issue.

## Issue
**Type:** {insight.get('insight_type', 'unknown')}
**Title:** {insight.get('title', '')}
**Description:** {insight.get('description', '')}

## Automation(s)
{automations_yaml}

## Your Task
Provide a corrected version of the automation(s) that fixes the issue.
- Return ONLY the corrected YAML, no explanations
- If multiple automations are involved, separate them with ---
- Keep the original id and alias
- Only change what's necessary to fix the issue"""

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get fix for insight {insight_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ApplyFixRequest(BaseModel):
    """Request model for applying a fix."""
    yaml_content: str


@app.post("/api/doctor/insights/{insight_id}/apply", response_model=ApplyFixResponse)
async def apply_insight_fix(insight_id: str, request: ApplyFixRequest):
    """Apply a fix suggestion directly to Home Assistant.

    Takes the fixed YAML and deploys it to HA, then marks the insight as resolved.
    """
    import yaml as yaml_lib

    try:
        # Get the insight to know which automation(s) are affected
        all_insights = await insights_storage.get_all()
        insight = next((i for i in all_insights if i.get("insight_id") == insight_id), None)
        if not insight:
            raise HTTPException(status_code=404, detail="Insight not found")

        # Parse the YAML - may contain multiple documents separated by ---
        yaml_content = request.yaml_content
        # Strip markdown code blocks if present
        yaml_content = yaml_content.replace("```yaml", "").replace("```yml", "").replace("```", "").strip()

        try:
            documents = list(yaml_lib.safe_load_all(yaml_content))
        except yaml_lib.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")

        if not documents:
            raise HTTPException(status_code=400, detail="No automation found in YAML")

        # Deploy each automation
        deployed_ids = []
        errors = []

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
                logger.info(f"Applied fix to automation: {automation_id}")
            else:
                errors.append(f"Failed to update {automation_id}: {result.get('error', 'Unknown error')}")

        if not deployed_ids:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to apply fix: {'; '.join(errors) if errors else 'No automations deployed'}"
            )

        # Reload automations
        reloaded = await ha_client.reload_automations()
        if not reloaded:
            errors.append("Automations saved but reload failed - may require manual reload")

        # Mark the insight as resolved
        await insights_storage.mark_resolved(insight_id, True)

        return ApplyFixResponse(
            success=True,
            automation_ids=deployed_ids,
            message=f"Fix applied to {len(deployed_ids)} automation(s)",
            errors=errors,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to apply fix for insight {insight_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
