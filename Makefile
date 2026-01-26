APP_DIR := automation-assistant
FRONTEND_DIR := $(APP_DIR)/frontend
VENV_PYTHON := .venv/bin/python
PYTHON := $(shell if [ -x $(VENV_PYTHON) ]; then echo $(VENV_PYTHON); else echo python3; fi)
UVICORN := $(PYTHON) -m uvicorn

-include $(APP_DIR)/.env

HOST ?= 0.0.0.0
PORT ?= 8099
CLAUDE_API_KEY ?=
SUPERVISOR_TOKEN ?=
HA_URL ?=
MODEL ?= claude-sonnet-4-20250514
LOG_LEVEL ?= info
HA_CONFIG_PATH ?=

export CLAUDE_API_KEY
export SUPERVISOR_TOKEN
export HA_URL
export MODEL
export LOG_LEVEL
export HA_CONFIG_PATH

.PHONY: deps dev dev-backend dev-frontend build install lint typecheck clean preview

# Install Python dependencies
deps:
	cd $(APP_DIR) && pip3 install -r requirements.txt

# Install frontend dependencies
install:
	cd $(FRONTEND_DIR) && npm install

# Run full dev environment (backend serves built frontend)
dev: deps build
	cd $(APP_DIR) && $(UVICORN) app.main:app --host $(HOST) --port $(PORT) --reload

# Run backend only (useful when developing frontend separately)
dev-backend: deps
	cd $(APP_DIR) && $(UVICORN) app.main:app --host $(HOST) --port $(PORT) --reload

# Run frontend dev server only (proxies /api to backend on :8099)
dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev

# Build frontend for production
build:
	cd $(FRONTEND_DIR) && npm run build

# Run ESLint on frontend
lint:
	cd $(FRONTEND_DIR) && npm run lint

# Type check frontend
typecheck:
	cd $(FRONTEND_DIR) && npx tsc --noEmit

# Clean build artifacts
clean:
	rm -rf $(FRONTEND_DIR)/node_modules
	rm -rf $(APP_DIR)/app/static/dist

# Preview production build
preview:
	cd $(FRONTEND_DIR) && npm run preview
