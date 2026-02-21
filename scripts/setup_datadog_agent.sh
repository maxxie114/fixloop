#!/bin/bash
# Installs and starts the Datadog Agent on Ubuntu/WSL2

set -e

if [ -z "$DD_API_KEY" ]; then
    # Try to load from .env
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | grep DD_API_KEY | xargs) 2>/dev/null || true
    fi
fi

if [ -z "$DD_API_KEY" ]; then
    echo "ERROR: DD_API_KEY is not set. Cannot install/start Datadog Agent."
    exit 1
fi

DD_SITE="${DD_SITE:-datadoghq.com}"

# Check if agent is already running
if pgrep -x "datadog-agent" > /dev/null 2>&1; then
    echo "Datadog Agent is already running."
    exit 0
fi

# Install agent if not present
if ! command -v datadog-agent &> /dev/null; then
    echo "Installing Datadog Agent..."
    DD_API_KEY="$DD_API_KEY" DD_SITE="$DD_SITE" bash -c "$(curl -L https://install.datadoghq.com/scripts/install_script_agent7.sh)"
    echo "Datadog Agent installed."
fi

# Configure APM
AGENT_CONFIG="/etc/datadog-agent/datadog.yaml"
if [ -f "$AGENT_CONFIG" ]; then
    # Enable APM if not already enabled
    if ! grep -q "^apm_enabled: true" "$AGENT_CONFIG" 2>/dev/null; then
        echo "apm_enabled: true" | sudo tee -a "$AGENT_CONFIG" > /dev/null
        echo "APM tracing enabled in agent config."
    fi
fi

# Start the agent
echo "Starting Datadog Agent..."
if command -v systemctl &> /dev/null && systemctl is-system-running &> /dev/null; then
    sudo systemctl start datadog-agent
    sudo systemctl enable datadog-agent
else
    # WSL2 without systemd — start manually
    sudo service datadog-agent start 2>/dev/null || \
    sudo /etc/init.d/datadog-agent start 2>/dev/null || \
    sudo datadog-agent start 2>/dev/null || \
    (echo "Could not start agent via service — trying direct launch..." && \
     sudo -u dd-agent datadog-agent run &)
fi

echo "Datadog Agent started. Listening on localhost:8126 for APM traces."
