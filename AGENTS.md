# AGENTS.md

## Repository Layout
- `automation-assistant/app/`: FastAPI service, HA client, storage, LLM integration.
- `automation-assistant/app/llm/`: `LLMClient` base and Claude clients.
- `automation-assistant/app/prompts/`: prompt builders for generation and diagnosis.
- `automation-assistant/frontend/`: React + Vite + Tailwind + shadcn UI frontend.
- `automation-assistant/config.yaml`: Home Assistant add-on metadata (bump version on changes).
- `automation-assistant/run.sh`: container entrypoint.

## Development Commands

### Quick Start (Single Command)
```bash
cp automation-assistant/.env.example automation-assistant/.env
make dev
```

`make dev` auto-detects `.venv/bin/python` when present.

Or inline env vars:

```bash
CLAUDE_API_KEY="your-api-key" SUPERVISOR_TOKEN="your-token" make dev
```

### Install Dependencies
```bash
cd automation-assistant
pip3 install -r requirements.txt
```

### Run the API (Development)
```bash
cd automation-assistant
export CLAUDE_API_KEY="your-api-key"
export SUPERVISOR_TOKEN="your-token"  # Only available in HA environment
export HA_URL="http://192.168.1.100:8123"  # Optional for local HA
export MODEL="claude-sonnet-4-20250514"  # Optional
export LOG_LEVEL="info"  # Optional
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8099 --reload
```

### Build and Run Container
```bash
cd automation-assistant
docker build -t automation-assistant .
docker run -p 8099:8099 automation-assistant
```

### Frontend Build Requirement
- If you change anything under `automation-assistant/frontend/`, run `make build` and ensure it succeeds.

### Lint and Format
- No lint/format tooling is configured. Match existing formatting and style.

### Testing
- No automated tests exist yet.
- Use `pytest` for unit tests and create `automation-assistant/tests/`.
- Single test: `pytest tests/test_file.py::test_name`
- Full suite: `pytest`

## Frontend Notes
- Vite config outputs to `automation-assistant/app/static/dist`, which the backend serves.
- Dev server runs on port 5173 and proxies `/api` to the backend at `http://localhost:8099`.
- Path alias `@` maps to `automation-assistant/frontend/src`.
- shadcn components live in `automation-assistant/frontend/src/components/ui` and shared UI in `automation-assistant/frontend/src/components`.
- Global styles live in `automation-assistant/frontend/src/styles/globals.css`.

## Code Style Guidelines

### Imports
- Order: standard library, third-party, local.
- Use absolute local imports (e.g., `from .config import config`).
- Leave a blank line between import groups.

### Formatting
- 4-space indentation; no tabs.
- Prefer double quotes for strings; triple-quote docstrings for modules/classes/functions.
- Wrap long lines with parentheses for readability.

### Types
- Use modern hints: `str | None`, `list[str]`, `dict[str, Any]`.
- Type all function params and returns.
- Use `typing.Any` only when required.

### Naming
- Functions/variables: `snake_case`.
- Classes: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Modules: `lowercase_with_underscores.py`.

### Async and I/O
- Use `async def` for I/O; always `await` async calls.
- Prefer `asyncio.gather` for parallel I/O.
- Use async context managers with `aiohttp` and `websockets`.

### Error Handling
- Raise `HTTPException` with explicit `status_code`/`detail` in endpoints.
- Catch and log expected errors; re-raise with clear messages.
- Avoid swallowing exceptions silently.

### Logging
- Module-level logger: `logger = logging.getLogger(__name__)`.
- Log at appropriate levels; do not log secrets (API keys, tokens).

### FastAPI and Pydantic
- Use Pydantic models for request/response validation.
- Declare `response_model` and return model instances.
- Keep endpoint logic thin; push heavy work into service modules.

### YAML Handling
- Parse YAML with `yaml.safe_load()` or `yaml.safe_load_all()`.
- Guard against empty/invalid YAML and handle `yaml.YAMLError`.

### Storage and File I/O
- Persist data under `/config/automation_assistant/`.
- Ensure directories exist and handle `IOError` gracefully.
- Use locks (`asyncio.Lock`) for concurrent write safety.

### LLM Integration
- Implement clients via `app/llm/base.py` (`LLMClient`).
- Use `AsyncClaudeClient` for async workflows.
- Log API errors, but do not include prompt contents or secrets.

## Git Guidelines

### Version Bumping
- Always bump the version in `automation-assistant/config.yaml` for any change.
- Use semantic versioning (major.minor.patch).

### Commit Messages
- Keep messages concise and consistent with repository history.
- Do not add `Co-Authored-By` lines.

## Home Assistant Integration

### Supervisor API
- Use Supervisor endpoints for HA access and reloads.
- Handle HA service downtime with clear error messages.

### Trace Parsing Notes
- `trace.saved_traces` entries can store the real payload under `extended_dict` or `short_dict`.
- When present, unwrap those dicts (or JSON strings) before reading fields.
- Payload keys observed: `run_id`, `state`, `script_execution`, `timestamp`, `trigger`, `trace`, `context`, `config`.

## Cursor/Copilot Rules
- No `.cursor/rules`, `.cursorrules`, or `.github/copilot-instructions.md` found.
