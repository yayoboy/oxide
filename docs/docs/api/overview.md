---
sidebar_position: 1
---

# API Overview

Oxide provides a comprehensive REST API and WebSocket interface for LLM orchestration.

## Base URL

```
http://localhost:8000
```

## Authentication

Authentication is **optional** and disabled by default. To enable:

```bash
export OXIDE_AUTH_ENABLED=true
```

### Obtaining a Token

```bash
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your-password"
}
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### Using the Token

Include the token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/services/
```

## Rate Limiting

API endpoints are rate-limited:
- **Unauthenticated**: 100 requests/minute
- **Authenticated**: 1000 requests/minute

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## API Endpoints

### Services

#### List Services

```bash
GET /api/services/
```

Response:
```json
{
  "total": 6,
  "healthy": 5,
  "enabled": 6,
  "services": {
    "ollama_local": {
      "enabled": true,
      "healthy": true,
      "info": {
        "type": "http",
        "base_url": "http://localhost:11434",
        "model": "llama2"
      }
    },
    ...
  }
}
```

#### Get Service Details

```bash
GET /api/services/{service_name}/
```

### Tasks

#### Execute Task

```bash
POST /api/tasks/execute/
Content-Type: application/json

{
  "prompt": "Explain quantum computing",
  "task_type": "question_answer",
  "max_tokens": 500,
  "temperature": 0.7,
  "service": "auto"  // optional, auto-routes if not specified
}
```

Response:
```json
{
  "task_id": "abc123",
  "status": "completed",
  "result": "Quantum computing is...",
  "execution_time": 2.34,
  "service_used": "ollama_local",
  "model_used": "llama2",
  "tokens_used": 450,
  "cost": 0.0
}
```

#### Get Task History

```bash
GET /api/tasks/history/?limit=10&offset=0
```

Response:
```json
{
  "total": 100,
  "tasks": [
    {
      "id": "abc123",
      "prompt": "Explain...",
      "status": "completed",
      "created_at": "2024-12-27T12:00:00Z",
      "completed_at": "2024-12-27T12:00:02Z"
    },
    ...
  ]
}
```

#### Get Task by ID

```bash
GET /api/tasks/{task_id}/
```

### Monitoring

#### Get Metrics

```bash
GET /api/monitoring/metrics/
```

Response:
```json
{
  "services": {
    "total": 6,
    "healthy": 5,
    "unhealthy": 1
  },
  "tasks": {
    "total": 100,
    "running": 2,
    "completed": 95,
    "failed": 3
  },
  "system": {
    "cpu_percent": 45.2,
    "memory_percent": 62.8,
    "memory_used_mb": 3072,
    "memory_total_mb": 4896
  }
}
```

#### Get System Stats

```bash
GET /api/monitoring/stats/
```

### Routing

#### List Routing Rules

```bash
GET /api/routing/rules/
```

Response:
```json
{
  "rules": [
    {
      "id": "rule-1",
      "task_type": "code_generation",
      "service": "openrouter",
      "model": "anthropic/claude-3.5-sonnet",
      "priority": 1
    },
    ...
  ]
}
```

#### Create Routing Rule

```bash
POST /api/routing/rules/
Content-Type: application/json

{
  "task_type": "code_generation",
  "service": "openrouter",
  "model": "anthropic/claude-3.5-sonnet",
  "priority": 1
}
```

### API Keys

#### Get API Key Status

```bash
GET /api/api-keys/status/openrouter/
```

Response:
```json
{
  "service": "openrouter",
  "configured": true,
  "valid": true,
  "key_preview": "sk-o...xyz"
}
```

#### Test API Key

```bash
POST /api/api-keys/test/
Content-Type: application/json

{
  "service": "openrouter",
  "api_key": "sk-or-..."  // optional if already configured
}
```

Response:
```json
{
  "success": true,
  "valid": true,
  "message": "API key is valid. 200+ models available.",
  "details": {
    "model_count": 200,
    "service": "openrouter"
  }
}
```

#### Update API Key

```bash
POST /api/api-keys/update/
Content-Type: application/json

{
  "service": "openrouter",
  "api_key": "sk-or-..."
}
```

**Warning**: This saves the API key in plain text to `config/default.yaml`. For production, use environment variables instead.

### Configuration

#### Get Configuration

```bash
GET /api/config/
```

Response:
```json
{
  "services": { ... },
  "routing": { ... },
  "security": { ... }
}
```

#### Update Configuration

```bash
POST /api/config/reload/
```

Hot-reloads the configuration without restarting.

## WebSocket API

Connect to `/ws` for real-time updates.

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  console.log('Connected to Oxide WebSocket');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

### Message Types

#### Service Status Update

```json
{
  "type": "service_status",
  "service": "ollama_local",
  "data": {
    "healthy": true,
    "enabled": true
  }
}
```

#### Metrics Update

```json
{
  "type": "metrics",
  "data": {
    "services": { ... },
    "tasks": { ... },
    "system": { ... }
  }
}
```

#### Task Progress

```json
{
  "type": "task_progress",
  "task_id": "abc123",
  "status": "running",
  "progress": 45
}
```

### Ping/Pong

```javascript
// Send ping
ws.send('ping');

// Receive pong
{
  "type": "pong"
}
```

## Task Types

Oxide recognizes the following task types for intelligent routing:

- `question_answer` - Question answering
- `summarization` - Text summarization
- `code_generation` - Code generation and programming
- `creative_writing` - Creative content generation
- `translation` - Language translation
- `analysis` - Data analysis and interpretation
- `chat` - Conversational interactions
- `general` - General purpose tasks

## Error Handling

### HTTP Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests (rate limit)
- `500` - Internal Server Error

### Error Response Format

```json
{
  "error": "Error message",
  "detail": "Detailed explanation",
  "code": "ERROR_CODE"
}
```

### Common Errors

#### Service Not Available

```json
{
  "error": "Service not available",
  "detail": "ollama_local is currently unhealthy",
  "code": "SERVICE_UNAVAILABLE"
}
```

#### Invalid API Key

```json
{
  "error": "Authentication failed",
  "detail": "Invalid API key for service openrouter",
  "code": "INVALID_API_KEY"
}
```

#### Rate Limit Exceeded

```json
{
  "error": "Rate limit exceeded",
  "detail": "Too many requests. Retry after 60 seconds.",
  "code": "RATE_LIMIT_EXCEEDED"
}
```

## Interactive API Documentation

Oxide provides interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## SDK & Libraries

### Python

```python
import aiohttp
import asyncio

class OxideClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    async def execute_task(self, prompt, task_type="general", **kwargs):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/tasks/execute/",
                json={
                    "prompt": prompt,
                    "task_type": task_type,
                    **kwargs
                }
            ) as response:
                return await response.json()

# Usage
client = OxideClient()
result = await client.execute_task(
    "Explain quantum computing",
    task_type="question_answer"
)
```

### JavaScript/TypeScript

```typescript
class OxideClient {
  constructor(private baseUrl: string = 'http://localhost:8000') {}

  async executeTask(
    prompt: string,
    taskType: string = 'general',
    options: any = {}
  ): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/tasks/execute/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt,
        task_type: taskType,
        ...options,
      }),
    });

    return response.json();
  }
}

// Usage
const client = new OxideClient();
const result = await client.executeTask(
  'Explain quantum computing',
  'question_answer'
);
```

## Next Steps

- [Task Execution Guide](./tasks) - Detailed task execution examples
- [WebSocket Guide](./websocket) - Real-time updates and streaming
- [Routing Configuration](./routing) - Custom routing rules
- [Cost Tracking](./costs) - Monitor and optimize costs
