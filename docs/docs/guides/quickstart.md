---
sidebar_position: 2
---

# Quickstart Guide

Get Oxide up and running in 5 minutes!

## Prerequisites

- Python 3.11+
- Node.js 20+
- At least one LLM provider (Ollama recommended for local testing)

## Step 1: Install Ollama (Optional but Recommended)

For quick local testing, install Ollama:

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Download from https://ollama.com/download

# Start Ollama and pull a model
ollama serve &
ollama pull llama2
```

## Step 2: Install Oxide

```bash
# Clone the repository
git clone https://github.com/yayoboy/oxide.git
cd oxide

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --all-extras

# Build frontend
cd src/oxide/web/frontend && npm install && npm run build && cd ../../..
```

## Step 3: Start Oxide

```bash
# Start all components
uv run oxide-all
```

You should see:
```
INFO:     Starting Oxide Web Backend
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 4: Access the Dashboard

Open your browser to **http://localhost:8000**

You should see:
- ✅ **Ollama** showing as "Healthy" (if you installed it)
- Dashboard with service status
- System metrics

## Step 5: Execute Your First Task

### Using the Web UI

1. Click on the **"Execute Tasks"** tab
2. Enter a prompt: `"Explain quantum computing in simple terms"`
3. Select task type: `"question_answer"`
4. Click **"Execute Task"**
5. Watch the real-time response stream in!

### Using the API

```bash
curl -X POST http://localhost:8000/api/tasks/execute/ \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum computing in simple terms",
    "task_type": "question_answer",
    "max_tokens": 500
  }'
```

Expected response:
```json
{
  "task_id": "abc123",
  "status": "completed",
  "result": "Quantum computing is...",
  "execution_time": 2.34,
  "service_used": "ollama_local"
}
```

### Using Python

```python
import asyncio
import aiohttp

async def execute_task():
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/api/tasks/execute/",
            json={
                "prompt": "Explain quantum computing",
                "task_type": "question_answer",
                "max_tokens": 500
            }
        ) as response:
            result = await response.json()
            print(result)

asyncio.run(execute_task())
```

## Step 6: Add More Providers (Optional)

### OpenRouter

1. Get an API key from [OpenRouter](https://openrouter.ai/)
2. Set the environment variable:
   ```bash
   export OPENROUTER_API_KEY="your-key-here"
   ```
3. Update `config/default.yaml`:
   ```yaml
   openrouter:
     enabled: true
     api_key: "${OPENROUTER_API_KEY}"
   ```
4. Restart Oxide

### OpenAI

```bash
export OPENAI_API_KEY="sk-..."
```

Update config:
```yaml
openai:
  enabled: true
  api_key: "${OPENAI_API_KEY}"
```

## Step 7: Configure Custom Routing

Create routing rules to route tasks to specific services:

1. Go to **"Routing Rules"** tab in the dashboard
2. Click **"Add Rule"**
3. Configure:
   - **Task Type**: `code_generation`
   - **Service**: `openrouter`
   - **Model**: `anthropic/claude-3.5-sonnet`
   - **Priority**: `1`
4. Click **"Save"**

Now all code generation tasks will route to OpenRouter!

## Step 8: Monitor Real-Time Metrics

The dashboard automatically updates every 2 seconds via WebSocket:

- **Service Health**: Green = healthy, Red = unhealthy
- **Active Tasks**: Tasks currently executing
- **System Resources**: CPU and memory usage
- **Task History**: Recent task executions

## Common Use Cases

### 1. Question Answering

```bash
curl -X POST http://localhost:8000/api/tasks/execute/ \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is the capital of France?",
    "task_type": "question_answer"
  }'
```

### 2. Code Generation

```bash
curl -X POST http://localhost:8000/api/tasks/execute/ \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a Python function to calculate fibonacci numbers",
    "task_type": "code_generation",
    "max_tokens": 500
  }'
```

### 3. Summarization

```bash
curl -X POST http://localhost:8000/api/tasks/execute/ \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Summarize this article: [long text here]",
    "task_type": "summarization",
    "max_tokens": 200
  }'
```

### 4. Creative Writing

```bash
curl -X POST http://localhost:8000/api/tasks/execute/ \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a short story about a robot learning to paint",
    "task_type": "creative_writing",
    "temperature": 0.9
  }'
```

## What's Next?

You're now up and running with Oxide! Here are some next steps:

- **[Configuration Guide](./configuration)** - Learn about all configuration options
- **[API Reference](../api/overview)** - Explore the complete API
- **[Deployment Guide](./deployment)** - Deploy Oxide to production
- **[Advanced Features](./advanced)** - Clustering, context memory, cost tracking

## Troubleshooting

### Ollama Not Showing as Healthy

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### Frontend Not Loading

```bash
# Rebuild frontend
cd src/oxide/web/frontend
npm run build
```

### API Key Not Working

```bash
# Verify environment variable is set
echo $OPENROUTER_API_KEY

# Test API key directly
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

## Need Help?

- Join our Discord community
- Check the [FAQ](./faq)
- Browse [GitHub Issues](https://github.com/yayoboy/oxide/issues)
- Read the full [Documentation](../)
