"""Pydantic models for the API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AutomationRequest(BaseModel):
    """Request model for automation generation."""

    prompt: str = Field(..., min_length=1, description="Natural language automation request")


class ModifyAutomationRequest(BaseModel):
    """Request model for modifying an existing automation."""

    prompt: str = Field(..., min_length=1, description="Natural language modification request")
    existing_yaml: str = Field(..., min_length=1, description="Current YAML of the automation to modify")


class AutomationResponse(BaseModel):
    """Response model for generated automation."""

    success: bool = Field(..., description="Whether generation was successful")
    response: str = Field(..., description="Full LLM response with YAML and explanation")
    yaml_content: str | None = Field(None, description="Extracted YAML content if available")
    error: str | None = Field(None, description="Error message if generation failed")


class ValidationRequest(BaseModel):
    """Request model for YAML validation."""

    yaml_content: str = Field(..., min_length=1, description="YAML content to validate")


class ValidationResponse(BaseModel):
    """Response model for YAML validation."""

    valid: bool = Field(..., description="Whether the YAML is valid")
    errors: list[str] = Field(default_factory=list, description="List of validation errors")


class ContextSummary(BaseModel):
    """Summary of Home Assistant context."""

    entity_count: int = Field(..., description="Number of entities")
    device_count: int = Field(..., description="Number of devices")
    area_count: int = Field(..., description="Number of areas")
    service_count: int = Field(..., description="Number of available services")
    domains: list[str] = Field(default_factory=list, description="List of entity domains")


class HAContext(BaseModel):
    """Full Home Assistant context."""

    states: list[dict[str, Any]] = Field(default_factory=list)
    services: list[dict[str, Any]] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    devices: list[dict[str, Any]] = Field(default_factory=list)
    areas: list[dict[str, Any]] = Field(default_factory=list)
    entity_registry: list[dict[str, Any]] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    configured: bool = Field(..., description="Whether API key is configured")


class SavedAutomation(BaseModel):
    """Model for a saved automation."""

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="User-provided name")
    prompt: str = Field(..., description="Original user request")
    yaml_content: str = Field(..., description="Generated YAML content")
    created_at: datetime = Field(..., description="Creation timestamp")


class SaveAutomationRequest(BaseModel):
    """Request model for saving an automation."""

    name: str = Field(..., min_length=1, max_length=100, description="Name for the automation")
    prompt: str = Field(..., min_length=1, description="Original prompt")
    yaml_content: str = Field(..., min_length=1, description="YAML content to save")


class UpdateAutomationRequest(BaseModel):
    """Request model for updating an automation."""

    prompt: str = Field(..., min_length=1, description="Updated prompt")
    yaml_content: str = Field(..., min_length=1, description="Updated YAML content")


class SavedAutomationList(BaseModel):
    """Response model for list of saved automations."""

    automations: list[SavedAutomation] = Field(default_factory=list, description="List of saved automations")
    count: int = Field(..., description="Total count of saved automations")


# Doctor feature models

class HAAutomationSummary(BaseModel):
    """Summary of a Home Assistant automation."""

    id: str = Field(..., description="Automation ID")
    alias: str = Field(..., description="Automation alias/name")
    description: str | None = Field(None, description="Automation description")
    mode: str | None = Field(None, description="Automation mode")
    area_id: str | None = Field(None, description="Area ID from entity registry")
    area_name: str | None = Field(None, description="Area name")
    state: str | None = Field(None, description="Automation state (on/off)")


class HAAutomationList(BaseModel):
    """List of Home Assistant automations."""

    automations: list[HAAutomationSummary] = Field(default_factory=list)
    count: int = Field(..., description="Total count")


class DiagnoseRequest(BaseModel):
    """Request model for diagnosing an automation."""

    automation_id: str = Field(..., min_length=1, description="ID of the automation to diagnose")


class DiagnosisResponse(BaseModel):
    """Response model for automation diagnosis."""

    automation_id: str = Field(..., description="ID of the diagnosed automation")
    automation_alias: str = Field(..., description="Alias/name of the automation")
    automation_yaml: str = Field(..., description="Full YAML of the automation")
    traces_summary: list[dict[str, Any]] = Field(default_factory=list, description="Recent execution traces")
    analysis: str = Field(..., description="Claude's analysis and recommendations")
    success: bool = Field(..., description="Whether diagnosis was successful")
    error: str | None = Field(None, description="Error message if diagnosis failed")


# Batch diagnosis models


class AutomationConflict(BaseModel):
    """Detected conflict between automations."""

    conflict_type: str = Field(..., description="Type: shared_trigger, state_conflict, resource_contention, timing_race, circular_dependency")
    severity: str = Field(..., description="Severity: info, warning, critical")
    automation_ids: list[str] = Field(default_factory=list, description="IDs of automations involved")
    automation_names: list[str] = Field(default_factory=list, description="Names of automations involved")
    description: str = Field(..., description="Description of the conflict")
    affected_entities: list[str] = Field(default_factory=list, description="Entities affected by the conflict")


class AutomationDiagnosisSummary(BaseModel):
    """Summary of single automation diagnosis."""

    automation_id: str = Field(..., description="Automation ID")
    automation_alias: str = Field(..., description="Automation alias/name")
    has_errors: bool = Field(..., description="Whether errors were found")
    error_count: int = Field(0, description="Number of errors")
    warning_count: int = Field(0, description="Number of warnings")
    brief_summary: str = Field("", description="Brief summary of status")


class Insight(BaseModel):
    """Actionable insight from diagnosis."""

    insight_id: str = Field(..., description="Unique ID for deduplication")
    category: str = Field(..., description="Category: single or multi")
    insight_type: str = Field(..., description="Type: error, warning, conflict, best_practice")
    severity: str = Field(..., description="Severity: info, warning, critical")
    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed description")
    automation_ids: list[str] = Field(default_factory=list, description="Affected automation IDs")
    automation_names: list[str] = Field(default_factory=list, description="Affected automation names")
    affected_entities: list[str] = Field(default_factory=list, description="Affected entities")
    recommendation: str = Field("", description="Suggested fix")
    first_seen: datetime = Field(..., description="When first detected")
    last_seen: datetime = Field(..., description="Last time detected")
    resolved: bool = Field(False, description="User marked as resolved")


class InsightsList(BaseModel):
    """Response for insights list."""

    single_automation: list[Insight] = Field(default_factory=list, description="Single automation issues")
    multi_automation: list[Insight] = Field(default_factory=list, description="Multi-automation conflicts")
    total_count: int = Field(0, description="Total insight count")
    unresolved_count: int = Field(0, description="Unresolved insight count")


class BatchDiagnosisReport(BaseModel):
    """Full batch diagnosis report."""

    run_id: str = Field(..., description="Unique run identifier")
    run_at: datetime = Field(..., description="When the diagnosis ran")
    scheduled: bool = Field(False, description="Whether this was a scheduled run")
    total_automations: int = Field(0, description="Total automations found")
    automations_analyzed: int = Field(0, description="Automations successfully analyzed")
    automations_with_errors: int = Field(0, description="Automations with issues")
    conflicts_found: int = Field(0, description="Number of conflicts detected")
    insights_added: int = Field(0, description="New insights added this run")
    automation_summaries: list[AutomationDiagnosisSummary] = Field(default_factory=list)
    conflicts: list[AutomationConflict] = Field(default_factory=list)
    overall_summary: str = Field("", description="Overall summary from Claude")
    full_analyses: list[DiagnosisResponse] = Field(default_factory=list, description="Detailed per-automation analyses")


class BatchReportSummary(BaseModel):
    """Summary for listing reports."""

    run_id: str = Field(..., description="Unique run identifier")
    run_at: datetime = Field(..., description="When the diagnosis ran")
    scheduled: bool = Field(False, description="Whether this was a scheduled run")
    total_automations: int = Field(0, description="Total automations found")
    automations_with_errors: int = Field(0, description="Automations with issues")
    conflicts_found: int = Field(0, description="Number of conflicts detected")
    insights_added: int = Field(0, description="New insights added this run")


class ScheduleConfig(BaseModel):
    """Schedule configuration."""

    enabled: bool = Field(True, description="Whether scheduling is enabled")
    time: str = Field("03:00", description="Time to run daily (HH:MM format)")
    next_run: datetime | None = Field(None, description="Next scheduled run time")


# Deploy feature models


class DeployAutomationRequest(BaseModel):
    """Request model for deploying an automation to Home Assistant."""

    yaml_content: str = Field(..., min_length=1, description="YAML content of the automation")
    automation_id: str | None = Field(None, description="Optional automation ID. If not provided, will be extracted from YAML or generated.")


class DeployAutomationResponse(BaseModel):
    """Response model for deployment result."""

    success: bool = Field(..., description="Whether deployment was successful")
    automation_id: str = Field(..., description="ID of the deployed automation")
    message: str = Field(..., description="Status message")
    is_new: bool = Field(..., description="True if automation was created, False if updated")


class ApplyFixResponse(BaseModel):
    """Response model for applying a fix to Home Assistant."""

    success: bool = Field(..., description="Whether the fix was applied successfully")
    automation_ids: list[str] = Field(default_factory=list, description="IDs of automations that were updated")
    message: str = Field(..., description="Status message")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")
