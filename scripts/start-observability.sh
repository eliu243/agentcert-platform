#!/bin/bash
# Start observability stack (Jaeger and agentgateway) for local development

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "Starting Observability Stack"
echo "=========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Start Jaeger
echo ""
echo "📊 Starting Jaeger..."
cd "$PROJECT_ROOT"
# Use 'docker compose' (V2) or fallback to 'docker-compose' (V1)
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose -f docker-compose.jaeger.yml up -d
else
    docker-compose -f docker-compose.jaeger.yml up -d
fi

# Wait for Jaeger to be ready
echo "⏳ Waiting for Jaeger to be ready..."
sleep 3

# Check if Jaeger is running
if docker ps | grep -q jaeger-collector; then
    echo "✅ Jaeger is running"
    echo "   UI: http://localhost:16686"
    echo "   OTLP: http://localhost:4317"
else
    echo "❌ Failed to start Jaeger"
    exit 1
fi

# Check if agentgateway is installed
if ! command -v agentgateway &> /dev/null; then
    echo ""
    echo "⚠️  agentgateway is not installed"
    echo "   Installing agentgateway..."
    curl https://raw.githubusercontent.com/agentgateway/agentgateway/refs/heads/main/common/scripts/get-agentgateway | bash
    
    if ! command -v agentgateway &> /dev/null; then
        echo "❌ Failed to install agentgateway"
        exit 1
    fi
fi

# Start agentgateway
echo ""
echo "🚪 Starting agentgateway..."
CONFIG_FILE="$PROJECT_ROOT/config/agentgateway.yaml"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ agentgateway config not found: $CONFIG_FILE"
    exit 1
fi

# Check if agentgateway is already running (any instance)
if pgrep -f "agentgateway" > /dev/null; then
    echo "⚠️  agentgateway is already running"
    echo "   Stopping existing instance(s)..."
    pkill -f "agentgateway" || true
    sleep 2
    # Verify it's stopped
    if pgrep -f "agentgateway" > /dev/null; then
        echo "⚠️  Some agentgateway processes still running, trying force kill..."
        pkill -9 -f "agentgateway" || true
        sleep 1
    fi
fi

# Start agentgateway in background
nohup agentgateway -f "$CONFIG_FILE" > /tmp/agentgateway.log 2>&1 &
AGENTGATEWAY_PID=$!

# Wait for agentgateway to start
sleep 2

# Check if agentgateway is running
if ps -p $AGENTGATEWAY_PID > /dev/null; then
    echo "✅ agentgateway is running (PID: $AGENTGATEWAY_PID)"
    echo "   A2A Proxy: http://localhost:3000"
    echo "   OpenAI Proxy: http://localhost:3001"
    echo "   Admin UI: http://localhost:15000/ui"
    echo "   Logs: /tmp/agentgateway.log"
else
    echo "❌ Failed to start agentgateway"
    echo "   Check logs: /tmp/agentgateway.log"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Observability stack is running!"
echo "=========================================="
echo ""
echo "Jaeger UI:      http://localhost:16686"
echo "agentgateway UI: http://localhost:15000/ui"
echo ""
echo "To stop:"
echo "  docker compose -f docker-compose.jaeger.yml down  # or docker-compose on older systems"
echo "  pkill -f agentgateway"
echo ""

