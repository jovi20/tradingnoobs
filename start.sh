#!/bin/bash

# Trading Noobs Startup Script (macOS/Linux)
# This script starts both backend and frontend

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PATH="$SCRIPT_DIR/backend"
FRONTEND_PATH="$SCRIPT_DIR/frontend"

echo -e "${CYAN}========================================"
echo -e "  Trading Noobs Startup"
echo -e "========================================${NC}"
echo ""

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "${GREEN}[OK] Python installed: $PYTHON_VERSION${NC}"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1)
    echo -e "${GREEN}[OK] Python installed: $PYTHON_VERSION${NC}"
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR] Python not found. Please install Python 3.10+${NC}"
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version 2>&1)
    echo -e "${GREEN}[OK] Node.js installed: $NODE_VERSION${NC}"
else
    echo -e "${RED}[ERROR] Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi

echo ""

# ========== Backend Setup ==========
echo -e "${YELLOW}--- Setting up Backend ---${NC}"

VENV_PATH="$BACKEND_PATH/venv"

# Create virtual environment if not exists
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${CYAN}Creating Python virtual environment...${NC}"
    cd "$BACKEND_PATH"
    $PYTHON_CMD -m venv venv
fi

# Activate venv and install dependencies
echo -e "${CYAN}Installing backend dependencies...${NC}"
cd "$BACKEND_PATH"
source "$VENV_PATH/bin/activate"
pip install -r requirements.txt --quiet

# Check .env file
if [ ! -f "$BACKEND_PATH/.env" ]; then
    if [ -f "$BACKEND_PATH/.env.example" ]; then
        echo -e "${CYAN}Copying .env.example to .env...${NC}"
        cp "$BACKEND_PATH/.env.example" "$BACKEND_PATH/.env"
    else
        echo -e "${CYAN}Creating default .env file...${NC}"
        cat > "$BACKEND_PATH/.env" << EOF
DATABASE_URL=sqlite:///./tradingnoobs.db
SECRET_KEY=dev-secret-key-change-in-production
CORS_ORIGINS=http://localhost:3000
EOF
    fi
fi

echo -e "${GREEN}[OK] Backend setup complete${NC}"
echo ""

# ========== Frontend Setup ==========
echo -e "${YELLOW}--- Setting up Frontend ---${NC}"

if [ ! -d "$FRONTEND_PATH/node_modules" ]; then
    echo -e "${CYAN}Installing frontend dependencies (npm install)...${NC}"
    cd "$FRONTEND_PATH"
    npm install
fi

echo -e "${GREEN}[OK] Frontend setup complete${NC}"
echo ""

# ========== Start Services ==========
echo -e "${CYAN}========================================"
echo -e "  Starting Services"
echo -e "========================================${NC}"
echo ""

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping services...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}Services stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${GREEN}Starting backend (http://localhost:8000)...${NC}"
cd "$BACKEND_PATH"
source "$VENV_PATH/bin/activate"
uvicorn main:app --reload --reload-exclude venv --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend
echo -e "${GREEN}Starting frontend (http://localhost:3000)...${NC}"
cd "$FRONTEND_PATH"
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${CYAN}========================================"
echo -e "${GREEN}  Services Started!"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${WHITE}Frontend: http://localhost:3000${NC}"
echo -e "${WHITE}Backend:  http://localhost:8000${NC}"
echo -e "${WHITE}API Docs: http://localhost:8000/docs${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services.${NC}"

# Wait for any process to exit
wait
