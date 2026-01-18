"""Pydantic models for the API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AutomationRequest(BaseModel):
    """Request model for automation generation."""

    prompt: str = Field(..., min_length=1, description="Natural language automation request")


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
