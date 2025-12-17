# Oxide Web UI - Quick Start Guide

Complete guide to setting up and using the Oxide Web Dashboard.

## Table of Contents

1. [Installation](#installation)
2. [Starting the Services](#starting-the-services)
3. [Using the Dashboard](#using-the-dashboard)
4. [API Documentation](#api-documentation)
5. [Network Services Setup](#network-services-setup)
6. [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm (for frontend)
- uv package manager (recommended)
- Running LLM services (Gemini CLI, Qwen CLI, Ollama, etc.)

### Step 1: Install Python Dependencies

```bash
cd /Users/yayoboy/Documents/GitHub/oxide

# Install with uv (recommended)
uv sync

# This will install all dependencies including:
# - FastAPI, uvicorn (web backend)
# - psutil (system metrics)
# - websockets (real-time updates)
```

### Step 2: Install Frontend Dependencies

```bash
cd oxide/web/frontend

# Install Node.js dependencies
npm install

# This will install:
# - React, React DOM
# - Vite (build tool)
# - Axios (HTTP client)
# - Recharts (for future charts)
```

---

## Starting the Services

You need to run **two services**:

### 1. Backend API Server

```bash
# From project root
uv run oxide-web

# Or directly with uvicorn
uv run uvicorn oxide.web.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will start on **http://localhost:8000**

- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- WebSocket: ws://localhost:8000/ws

### 2. Frontend Development Server

```bash
# In a new terminal
cd oxide/web/frontend

# Start Vite dev server
npm run dev
```

The frontend will start on **http://localhost:3000**

### Quick Start (Both Services)

Use two terminal windows:

**Terminal 1 - Backend:**
```bash
uv run oxide-web
```

**Terminal 2 - Frontend:**
```bash
cd oxide/web/frontend && npm run dev
```

Then open your browser to: **http://localhost:3000**

---

## Using the Dashboard

### Dashboard Overview

The Oxide dashboard provides real-time monitoring and control:

#### 1. **System Metrics Section**

Displays 4 key metric cards:

- **Services**: Enabled vs Healthy services
- **Tasks**: Completed, running, failed task counts
- **System**: CPU and memory usage with progress bars
- **WebSocket**: Active real-time connections

#### 2. **LLM Services Section**

Shows all configured services with:

- ✅ **Healthy** badge (green) - Service available
- ❌ **Unavailable** badge (red) - Service down
- Service details: type, base URL, model, optimal use cases

#### 3. **Task History Section**

Recent task executions with:

- Status badges (Completed, Running, Failed, Queued)
- Execution duration
- Prompt preview
- File count
- Error messages (if failed)
- Response preview (if completed)

Auto-refreshes every 3 seconds.

#### 4. **Live Updates Section**

Real-time WebSocket events:

- Task start notifications
- Progress updates
- Completion events
- Service status changes

### Dashboard Features

- **Real-time Updates**: WebSocket connection provides live data
- **Auto-refresh**: Metrics update every 2-5 seconds
- **Color-coded Status**: Green (healthy), Red (error), Yellow (warning)
- **Responsive Design**: Works on desktop and tablets

---

## API Documentation

### Interactive API Docs

FastAPI provides automatic interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### REST API Endpoints

#### Services API (`/api/services`)

```bash
# List all services with status
GET /api/services

# Get specific service info
GET /api/services/{service_name}

# Health check
POST /api/services/{service_name}/health

# Test service with prompt
POST /api/services/{service_name}/test?test_prompt=Hello

# Get available models
GET /api/services/{service_name}/models

# Get routing rules
GET /api/services/routing/rules
```

#### Tasks API (`/api/tasks`)

```bash
# Execute a task
POST /api/tasks/execute
Body: {
  "prompt": "Analyze this code",
  "files": ["/path/to/file.py"],
  "preferences": {}
}

# List tasks
GET /api/tasks?status=completed&limit=50

# Get specific task
GET /api/tasks/{task_id}

# Delete task
DELETE /api/tasks/{task_id}

# Clear task history
POST /api/tasks/clear?status=failed
```

#### Monitoring API (`/api/monitoring`)

```bash
# Get system metrics
GET /api/monitoring/metrics

# Get task statistics
GET /api/monitoring/stats

# System health check
GET /api/monitoring/health
```

### WebSocket API

Connect to `ws://localhost:8000/ws` to receive real-time events:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data);
};
```

**Event Types:**
- `connected` - Connection established
- `task_start` - Task execution started
- `task_progress` - Streaming chunk received
- `task_complete` - Task finished
- `service_status` - Service health changed
- `metrics` - System metrics update

---

## Network Services Setup

### Setting Up Ollama Remote

If you have Ollama running on another machine (e.g., a server):

```bash
# Run the setup script
./scripts/setup_ollama_remote.sh --ip 192.168.1.100

# Options:
#   --ip     Remote server IP (required)
#   --port   Ollama port (default: 11434)
#   --model  Model to use (default: qwen2.5-coder:7b)
```

**What the script does:**
1. Tests connectivity to remote Ollama
2. Checks available models
3. Tests model execution
4. Updates `config/default.yaml` to enable the service

**Manual Ollama Server Setup:**

On the remote server:
```bash
# Start Ollama with network binding
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# Pull models
ollama pull qwen2.5-coder:7b
```

### Setting Up LM Studio

If you have LM Studio running on another machine (e.g., laptop):

```bash
# Run the setup script
./scripts/setup_lmstudio.sh --ip 192.168.1.50

# Options:
#   --ip     LM Studio machine IP (required)
#   --port   LM Studio port (default: 1234)
```

**What the script does:**
1. Tests connectivity to LM Studio
2. Checks loaded models
3. Tests model execution
4. Updates `config/default.yaml` to enable the service

**Manual LM Studio Setup:**

On the LM Studio machine:
1. Open LM Studio
2. Go to **Settings → Server**
3. Enable **Local Server**
4. Set Port to `1234`
5. Enable **Network Access** (allow LAN)
6. Load a model

### Network Testing

```bash
# Test specific service
uv run python scripts/test_network.py --service ollama_remote
uv run python scripts/test_network.py --service lmstudio

# Test all network services
uv run python scripts/test_network.py --all

# Scan your network for services
uv run python scripts/test_network.py --scan 192.168.1.0/24
```

The network scanner will find Ollama and LM Studio instances on your LAN.

---

## Troubleshooting

### Backend Issues

#### Error: "Port 8000 already in use"

```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
kill -9 $(lsof -ti:8000)

# Or use a different port
uv run uvicorn oxide.web.backend.main:app --port 8080
```

#### Error: "ModuleNotFoundError: No module named 'psutil'"

```bash
# Reinstall dependencies
uv sync

# Or install manually
pip install psutil websockets
```

#### Error: "Orchestrator not initialized"

Make sure `config/default.yaml` exists and is valid:

```bash
# Validate configuration
uv run python scripts/validate_config.py

# Check if config file exists
ls config/default.yaml
```

### Frontend Issues

#### Error: "Cannot connect to backend"

1. Ensure backend is running on port 8000
2. Check `vite.config.js` proxy settings
3. Test backend directly: `curl http://localhost:8000/health`

#### Error: "npm install fails"

```bash
# Clear npm cache
npm cache clean --force

# Remove node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### Frontend shows no data

1. Check browser console for errors
2. Verify backend is running: http://localhost:8000/health
3. Test API directly: http://localhost:8000/api/services
4. Check WebSocket connection in browser Network tab

### WebSocket Issues

#### "WebSocket disconnected" constantly

1. Check if backend is running
2. Verify no firewall blocking port 8000
3. Check browser console for WebSocket errors
4. Try disabling browser extensions

### Service Issues

#### "Service unavailable" in dashboard

1. Check if the CLI tool is in PATH:
   ```bash
   which gemini
   which qwen
   ```

2. Test service directly:
   ```bash
   uv run python scripts/test_connection.py --service gemini
   ```

3. For network services, verify connectivity:
   ```bash
   curl http://192.168.1.100:11434/api/tags  # Ollama
   curl http://192.168.1.50:1234/v1/models   # LM Studio
   ```

### Logs

Check logs for errors:

```bash
# Backend logs (console output)
# Look for errors in the terminal running oxide-web

# MCP server logs
tail -f /tmp/oxide.log

# Enable debug logging
# Edit config/default.yaml:
logging:
  level: DEBUG
```

---

## Production Deployment

### Building for Production

**Backend:**

The backend is ready for production as-is. Use a production ASGI server:

```bash
# With gunicorn
gunicorn oxide.web.backend.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000

# Or with uvicorn
uvicorn oxide.web.backend.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4
```

**Frontend:**

Build the frontend for production:

```bash
cd oxide/web/frontend

# Build static files
npm run build

# Files will be in dist/ directory

# Serve with nginx, Apache, or any static file server
```

### Environment Variables

```bash
# Backend
export OXIDE_CONFIG_PATH=/path/to/config.yaml
export OXIDE_LOG_LEVEL=INFO

# Frontend (during build)
export VITE_API_URL=https://api.yourserver.com
```

---

## Next Steps

- **Configure More Services**: Add Ollama remote, LM Studio
- **Explore the API**: Try out endpoints in http://localhost:8000/docs
- **Monitor Tasks**: Execute tasks via MCP and watch them in dashboard
- **Network Scan**: Find LLM services on your LAN

For more information, see:
- [Installation Guide](INSTALLATION.md)
- [Main README](README.md)
- [API Documentation](http://localhost:8000/docs)

---

**Happy orchestrating! 🔬**
