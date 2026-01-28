ROOT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
APP_DIR := automation-assistant
FRONTEND_DIR := $(APP_DIR)/frontend
VENV_PYTHON := $(ROOT_DIR).venv/bin/python
PYTHON := $(shell if [ -x $(VENV_PYTHON) ]; then echo $(VENV_PYTHON); else echo python3; fi)
UVICORN := $(PYTHON) -m uvicorn

-include $(APP_DIR)/.env

HOST ?= 0.0.0.0
PORT ?= 8099
CLAUDE_API_KEY ?=
SUPERVISOR_TOKEN ?=
HA_URL ?=
MODEL ?= claude-sonnet-4-20250514
DOCTOR_MODEL ?=
LOG_LEVEL ?= info
HA_CONFIG_PATH ?=

export CLAUDE_API_KEY
export SUPERVISOR_TOKEN
export HA_URL
export MODEL
export DOCTOR_MODEL
export LOG_LEVEL
export HA_CONFIG_PATH

.PHONY: deps deps-dev dev dev-backend dev-frontend build install lint lint-fix lint-ruff lint-pylint lint-flake8 lint-python typecheck format format-check clean preview

# Install Python dependencies
deps:
	cd $(APP_DIR) && $(PYTHON) -m pip install -r requirements.txt

# Install Python dev dependencies
deps-dev:
	cd $(APP_DIR) && $(PYTHON) -m pip install -r requirements-dev.txt

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

# Run ESLint on frontend with auto-fix
lint-fix:
	cd $(FRONTEND_DIR) && npm run lint:fix

# Format frontend code with Prettier
format:
	cd $(FRONTEND_DIR) && npm run format

# Check frontend code formatting
format-check:
	cd $(FRONTEND_DIR) && npm run format:check

# Run Ruff on backend
lint-ruff: deps-dev
	cd $(APP_DIR) && $(PYTHON) -m ruff check app

# Run Pylint on backend
lint-pylint: deps-dev
	cd $(APP_DIR) && PYLINTHOME=/tmp/pylint $(PYTHON) -m pylint app

# Run Flake8 on backend
lint-flake8: deps-dev
	cd $(APP_DIR) && $(PYTHON) -m flake8 --max-line-length 100 app

# Run all backend linters
lint-python: lint-ruff lint-pylint lint-flake8

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
