#!/usr/bin/env bash
set -Eeuo pipefail

# Start Workspaces Django server
# Usage: start-workspace.sh [port]
# Can be run from anywhere - script auto-navigates to correct directory

# Resolve actual script location (follows symlinks)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${VIRTUAL_ENV:-$ROOT/.venv}"
WORKSPACE_DIR="$ROOT/workspace"
PORT="${1:-8001}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [[ ! -d "$VENV_DIR" ]]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_DIR${NC}"
    echo "Please run $ROOT/scripts/setup-dev.sh first to set up the environment."
    exit 1
fi

# Check if workspace directory exists
if [[ ! -d "$WORKSPACE_DIR" ]]; then
    echo -e "${RED}Error: Workspace directory not found at $WORKSPACE_DIR${NC}"
    exit 1
fi

# Activate virtual environment and start server
echo -e "${GREEN}Starting Workspaces Django server on port $PORT...${NC}"
echo -e "${YELLOW}Virtual environment: $VENV_DIR${NC}"
echo -e "${YELLOW}Working directory: $WORKSPACE_DIR${NC}"
echo ""

cd "$WORKSPACE_DIR"
source "$VENV_DIR/bin/activate"

# Check if .env exists
if [[ ! -f "$ROOT/.env" ]]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example...${NC}"
    cp "$ROOT/.env.example" "$ROOT/.env"
    chmod 600 "$ROOT/.env"
fi

# Start the server
exec python -m uvicorn workspace.asgi:application --host 127.0.0.1 --port "$PORT" --reload
