---
sidebar_position: 1
---

# Installation Guide

This guide will walk you through installing Oxide on your system.

## Prerequisites

Before installing Oxide, ensure you have:

- **Python 3.11+**: Required for running Oxide
- **uv**: Modern Python package installer (recommended)
- **Node.js 20+**: Required for the Web UI
- **Git**: For cloning the repository

## Installation Methods

### Method 1: Install from Source (Recommended)

1. **Clone the repository**:

```bash
git clone https://github.com/yayoboy/oxide.git
cd oxide
```

2. **Install uv** (if not already installed):

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

3. **Install Python dependencies**:

```bash
uv sync --all-extras
```

4. **Install and build frontend**:

```bash
cd src/oxide/web/frontend
npm install
npm run build
cd ../../..
```

5. **Verify installation**:

```bash
uv run oxide-all --help
```

### Method 2: Install from PyPI (Coming Soon)

```bash
pip install oxide-llm
```

## Configuration

After installation, you need to configure Oxide with your LLM providers.

### 1. Copy Default Configuration

```bash
cp config/default.yaml config/local.yaml
```

### 2. Edit Configuration

Open `config/local.yaml` and configure your services:

```yaml
services:
  # Local Ollama
  ollama_local:
    type: http
    base_url: "http://localhost:11434"
    model: "llama2"
    enabled: true

  # OpenRouter (requires API key)
  openrouter:
    type: http
    base_url: "https://openrouter.ai/api/v1"
    api_key: "${OPENROUTER_API_KEY}"  # Set via environment variable
    default_model: "anthropic/claude-3.5-sonnet"
    enabled: true
```

### 3. Set Environment Variables

For services requiring API keys:

```bash
# Add to ~/.bashrc, ~/.zshrc, or .env
export OPENROUTER_API_KEY="your-api-key-here"
export OPENAI_API_KEY="your-api-key-here"
export ANTHROPIC_API_KEY="your-api-key-here"
```

## Verify Installation

### Test Backend API

```bash
# Start the backend
uv run oxide-web

# In another terminal, test the API
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "orchestrator": true,
  "services": 6
}
```

### Test Web Dashboard

1. Open your browser to `http://localhost:8000`
2. You should see the Oxide dashboard
3. Check that services are showing as "Healthy"

## Running Oxide

### Option 1: Run All Components (Recommended)

```bash
uv run oxide-all
```

This starts:
- MCP Server (Model Context Protocol)
- Web Backend API (FastAPI)
- Web Frontend (Vite React app)

### Option 2: Run Components Separately

**Backend only**:
```bash
uv run oxide-web
```

**MCP Server only**:
```bash
uv run oxide-mcp
```

**Frontend development**:
```bash
cd src/oxide/web/frontend
npm run dev
```

## Docker Installation (Alternative)

### Using Docker Compose

1. **Create docker-compose.yml**:

```yaml
version: '3.8'

services:
  oxide:
    image: ghcr.io/yayoboy/oxide:latest
    ports:
      - "8000:8000"
      - "5173:5173"
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./config:/app/config
      - oxide-data:/app/data
    restart: unless-stopped

volumes:
  oxide-data:
```

2. **Start the container**:

```bash
docker-compose up -d
```

### Using Docker Run

```bash
docker run -d \
  --name oxide \
  -p 8000:8000 \
  -p 5173:5173 \
  -e OPENROUTER_API_KEY=$OPENROUTER_API_KEY \
  -v $(pwd)/config:/app/config \
  ghcr.io/yayoboy/oxide:latest
```

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or change Oxide's port
export OXIDE_PORT=8080
uv run oxide-web
```

### Services Showing as Unhealthy

1. **Check service URLs**: Ensure services are accessible
   ```bash
   # Test Ollama
   curl http://localhost:11434/api/tags
   ```

2. **Check API keys**: Verify environment variables are set
   ```bash
   echo $OPENROUTER_API_KEY
   ```

3. **Check logs**: Look for error messages
   ```bash
   tail -f logs/oxide.log
   ```

### Frontend Not Loading

1. **Rebuild frontend**:
   ```bash
   cd src/oxide/web/frontend
   npm install
   npm run build
   ```

2. **Clear browser cache**: Hard refresh with Ctrl+Shift+R (or Cmd+Shift+R on Mac)

## Next Steps

- [Quickstart Guide](./quickstart) - Get up and running in 5 minutes
- [Configuration Guide](./configuration) - Detailed configuration options
- [API Reference](../api/overview) - Complete API documentation
- [Deployment Guide](./deployment) - Deploy Oxide to production

## Getting Help

If you encounter issues:

- Check the [FAQ](./faq)
- Search [GitHub Issues](https://github.com/yayoboy/oxide/issues)
- Ask in [GitHub Discussions](https://github.com/yayoboy/oxide/discussions)
- Join our Discord community
