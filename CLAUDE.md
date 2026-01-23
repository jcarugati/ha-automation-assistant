# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automation Assistant is a Home Assistant add-on that generates automations from natural language using Claude AI. It also includes a "Doctor" feature for diagnosing and fixing issues in existing automations.

## Running the Add-on

The add-on runs as a Docker container in Home Assistant. For local development:

```bash
# Run the FastAPI server directly
cd automation-assistant
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8099 --reload

# Required environment variables
export CLAUDE_API_KEY="your-api-key"
export SUPERVISOR_TOKEN="your-token"  # Only available in HA environment
```

The web UI is served at `http://localhost:8099`.

## Architecture

```
automation-assistant/
├── app/
│   ├── main.py              # FastAPI app with all API endpoints
│   ├── models.py            # Pydantic request/response models
│   ├── config.py            # Configuration from environment/HA options
│   ├── automation.py        # Automation generation logic
│   ├── doctor.py            # Single automation diagnosis
│   ├── batch_doctor.py      # Batch diagnosis of all automations
│   ├── ha_client.py         # Home Assistant Supervisor API client
│   ├── ha_automations.py    # Reads automations from HA config files
│   ├── storage.py           # Saved automations persistence
│   ├── diagnostic_storage.py # Diagnosis reports persistence
│   ├── insights_storage.py  # Deduplicated insights persistence
│   ├── scheduler.py         # APScheduler for daily diagnosis
│   ├── llm/
│   │   ├── base.py          # Abstract LLM interface
│   │   └── claude.py        # Anthropic Claude implementation
│   ├── prompts/
│   │   ├── automation.py    # Generation prompts
│   │   ├── conflicts.py     # Conflict analysis prompts
│   │   └── debug.py         # Diagnosis prompts
│   └── static/
│       └── index.html       # Single-page frontend (vanilla JS)
├── config.yaml              # HA add-on manifest
├── Dockerfile               # Alpine + Python container
└── run.sh                   # Container entrypoint
```

## Key Concepts

**Home Assistant Integration**: The add-on communicates with HA via the Supervisor API (`http://supervisor/core`). It fetches entities, devices, areas, services, and automation traces to provide context for generation and diagnosis.

**Storage**: All persistent data is stored in `/config/automation_assistant/` (HA's config directory):
- `saved_automations.json` - User-saved automations
- `insights.json` - Deduplicated diagnostic findings
- `scheduler_config.json` - Schedule settings
- `diagnostic_storage/` - Batch diagnosis reports

**LLM Integration**: Uses the Anthropic SDK. The `AsyncClaudeClient` in `app/llm/claude.py` handles all Claude API calls. Context from HA is injected into prompts for accurate YAML generation.

## API Structure

Main endpoint groups in `app/main.py`:
- `/api/generate` - Generate automation from natural language
- `/api/automations/*` - CRUD for saved automations
- `/api/deploy` - Deploy automation directly to HA
- `/api/ha-automations/*` - Read HA automations
- `/api/doctor/*` - Diagnosis, batch analysis, insights, scheduling

## Frontend

The frontend is a single `index.html` file with embedded CSS and JavaScript. No build step required. It has two main tabs:
1. **Create** - Generate new automations from prompts
2. **Doctor** - Diagnose existing automations, view insights, apply fixes

## Version Bumping

Update version in `automation-assistant/config.yaml` when making changes.
