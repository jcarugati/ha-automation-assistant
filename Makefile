APP_DIR := automation-assistant
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

.PHONY: deps dev

deps:
	cd $(APP_DIR) && pip3 install -r requirements.txt

dev: deps
	cd $(APP_DIR) && $(UVICORN) app.main:app --host $(HOST) --port $(PORT) --reload
