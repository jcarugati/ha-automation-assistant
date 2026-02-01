# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important: Always Lint and Verify Your Changes

**After making ANY code changes, you MUST run the appropriate linter:**

### Frontend changes (TypeScript/React):
```bash
make lint            # ESLint - run after every change
make format          # Prettier - run after every change
make typecheck       # TypeScript check
make build           # Verify production build works
```

### Backend changes (Python):
```bash
make lint-python     # Run all Python linters (ruff, pylint, flake8)
# Or run individually:
make lint-ruff       # Fast linter
make lint-pylint     # Detailed analysis
make lint-flake8     # Style checks
```

### Before committing:
- Run `make install` first if dependencies changed
- Ensure `make build` passes for frontend changes
- Ensure `make dev-backend` starts for backend changes

**Do not submit changes that fail linting or break the build.**

## Project Overview

Automation Assistant is a Home Assistant add-on that generates automations from natural language using Claude AI. It also includes a "Doctor" feature for diagnosing and fixing issues in existing automations.

## Local Development

1. Create a long-lived access token in Home Assistant (HA profile → Security → Long-Lived Access Tokens)

2. Set up environment and run:
   ```bash
   cp automation-assistant/.env.example automation-assistant/.env
   # Edit .env with your CLAUDE_API_KEY, SUPERVISOR_TOKEN, and HA_URL
   make dev
   ```

The web UI is served at `http://localhost:8099`.

## Architecture

The add-on is a FastAPI backend serving a single-page frontend.

**Data Flow**: User prompt → `automation.py` fetches HA context via `ha_client.py` → builds prompt with `prompts/*.py` → sends to Claude via `llm/claude.py` → extracts YAML from response → returns to frontend.

**Home Assistant Integration**: Communicates with HA via Supervisor API (`http://supervisor/core`) for entities, devices, areas, and services. Uses WebSocket for device/area registries. For local dev, uses `HA_URL` + long-lived access token instead.

**Storage** (in `/config/automation_assistant/`):
- `saved_automations.json` - User-saved automations
- `insights.json` - Deduplicated diagnostic findings
- `diagnostic_storage/` - Batch diagnosis reports

**LLM Interface**: `llm/base.py` defines the abstract interface; `llm/claude.py` implements it using the Anthropic SDK.

## Key Files

- `app/main.py` - All FastAPI endpoints
- `app/automation.py` - Generation logic, YAML extraction and validation
- `app/doctor.py` - Single automation diagnosis
- `app/batch_doctor.py` - Batch diagnosis of all automations
- `app/ha_client.py` - HA API client (REST + WebSocket)
- `app/prompts/*.py` - System/user prompts for generation and diagnosis
- `app/static/index.html` - Legacy single-file frontend (vanilla JS)
- `app/static/dist/` - Built React frontend (served when available)
- `frontend/` - React TypeScript frontend source
- `config.yaml` - HA add-on manifest (update version here)

## API Endpoints

- `POST /api/generate` - Generate automation from natural language
- `POST /api/modify` - Modify existing automation with AI
- `POST /api/deploy` - Deploy automation directly to HA
- `GET/POST/PUT/DELETE /api/automations/*` - Saved automations CRUD
- `GET /api/ha-automations/*` - Read HA automations
- `/api/doctor/*` - Diagnosis, batch analysis, insights, scheduling

## Debugging Local Development

### Common Issues

**1. Empty automations list (0 automations)**
- **Cause**: The app reads from `/config/automations.yaml` which doesn't exist locally
- **Solution**: The app now falls back to HA REST API when the file doesn't exist
- **Verify**: Check server logs for "Automations file not found, fetching via API..."

**2. Environment variables not loaded**
- **Cause**: `.env` file not saved, or server not restarted after changes
- **Solution**: Save `.env` file (check for unsaved dot in VS Code tab), then restart `make dev`
- **Note**: `uvicorn --reload` only reloads code changes, not environment variables

**3. All automations show "Unknown" state or "No Area"**
- **Cause**: Entity ID mismatch between automation ID and entity_id used for lookups
- **Details**: HA automation IDs (e.g., `1726837859026`) differ from entity IDs (e.g., `automation.my_auto_name`)
- **Solution**: Use `_entity_id` from API response for state/area lookups

### Debugging Commands

```bash
# Test HA API connection
export $(grep -v '^#' .env | xargs)
curl -s -H "Authorization: Bearer $SUPERVISOR_TOKEN" "$HA_URL/api/"

# List automations directly from HA
curl -s -H "Authorization: Bearer $SUPERVISOR_TOKEN" "$HA_URL/api/states" | \
  python3 -c "import sys,json; [print(s['entity_id']) for s in json.load(sys.stdin) if s['entity_id'].startswith('automation.')]"

# Check automation state attributes (includes real ID)
curl -s -H "Authorization: Bearer $SUPERVISOR_TOKEN" "$HA_URL/api/states/automation.ENTITY_NAME"

# Test local API endpoints
curl -s http://localhost:8099/api/version
curl -s http://localhost:8099/api/ha-automations | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin), indent=2))"
```

### Key Differences: Add-on vs Local Dev

| Aspect | Add-on Mode | Local Dev Mode |
|--------|-------------|----------------|
| Automations source | `/config/automations.yaml` file | HA REST API (`/api/states`) |
| Auth | Supervisor token (auto) | Long-lived access token (manual) |
| HA URL | `http://supervisor/core` | `HA_URL` env var |
| Config path | `/config` | `HA_CONFIG_PATH` env var (optional) |

## Git Guidelines

### Version Bumping
- Always bump the version in `automation-assistant/config.yaml` for any change.
- Use semantic versioning (major.minor.patch).

### Commit Messages
- Keep messages concise and consistent with repository history.
- Do not add `Co-Authored-By` lines.

## Frontend Development

The frontend is a React + TypeScript SPA with shadcn/ui components.

**Source**: `frontend/src/` - React TypeScript source
**Output**: `app/static/dist/` - Built files served by FastAPI

### Stack
- React 18 with TypeScript (strict mode)
- shadcn/ui for UI components (Radix primitives)
- Tailwind CSS for styling
- Vite for build and dev server

### Structure
- `types/` - TypeScript interfaces (mirrors `app/models.py`)
- `api/` - Typed fetch functions
- `hooks/` - Custom React hooks for state
- `components/ui/` - shadcn components (don't edit directly)
- `components/` - App-specific components
- `lib/utils.ts` - Tailwind class merge helper

### Commands

From the project root:
```bash
make install         # Install frontend dependencies
make build           # Build frontend to app/static/dist/
make dev             # Build frontend + run backend
make dev-backend     # Run backend only (for frontend dev)
make dev-frontend    # Run frontend dev server (proxies /api to :8099)
make lint            # ESLint check
make lint-fix        # ESLint with auto-fix
make format          # Prettier format
make format-check    # Prettier check (no changes)
make typecheck       # TypeScript check
```

Or directly with npm:
```bash
cd automation-assistant/frontend
npm install          # Install dependencies
npm run dev          # Dev server with HMR
npm run build        # Build for production
npm run lint         # ESLint check
npm run lint:fix     # ESLint with auto-fix
npm run format       # Prettier format
npm run format:check # Prettier check
```

### Adding shadcn Components
```bash
cd frontend
npx shadcn@latest add [component-name]
```

### Adding New Features
1. Add types to `types/` if needed
2. Add API functions to `api/`
3. Create hook in `hooks/` if state needed
4. Create component in `components/`
5. Use shadcn primitives from `components/ui/`