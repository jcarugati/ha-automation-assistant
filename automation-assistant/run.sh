#!/usr/bin/with-contenv bashio

# Read configuration from options
export CLAUDE_API_KEY=$(bashio::config 'claude_api_key')
export MODEL=$(bashio::config 'model')
export LOG_LEVEL=$(bashio::config 'log_level')

# Get supervisor token for HA API access
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN}"

bashio::log.info "Starting Automation Assistant..."
bashio::log.info "Using model: ${MODEL}"
bashio::log.info "Log level: ${LOG_LEVEL}"

# Start the FastAPI server
cd /app
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8099
