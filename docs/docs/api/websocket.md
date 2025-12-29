---
sidebar_position: 2
---

# WebSocket API

Oxide provides a real-time WebSocket API for live updates on task execution, service health, and system metrics.

## Connection

### Endpoint

```
ws://localhost:8000/ws
```

or with HTTPS:

```
wss://your-domain.com/ws
```

### Authentication (Optional)

If authentication is enabled, include the JWT token in the connection URL:

```javascript
const token = 'your-jwt-token';
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);
```

## Connection Lifecycle

### Establishing Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  console.log('✅ Connected to Oxide WebSocket');
};

ws.onclose = (event) => {
  console.log('❌ Disconnected:', event.code, event.reason);
};

ws.onerror = (error) => {
  console.error('⚠️ WebSocket error:', error);
};
```

### Automatic Reconnection

```javascript
class OxideWebSocket {
  constructor(url) {
    this.url = url;
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 30000;
    this.reconnectAttempts = 0;
    this.connect();
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('Connected to Oxide');
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;
    };

    this.ws.onclose = () => {
      console.log('Disconnected, attempting reconnect...');
      this.scheduleReconnect();
    };

    this.ws.onmessage = (event) => {
      this.handleMessage(JSON.parse(event.data));
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  scheduleReconnect() {
    setTimeout(() => {
      this.reconnectAttempts++;
      this.reconnectDelay = Math.min(
        this.reconnectDelay * 2,
        this.maxReconnectDelay
      );
      this.connect();
    }, this.reconnectDelay);
  }

  handleMessage(data) {
    // Handle incoming messages
    console.log('Received:', data);
  }

  send(data) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  close() {
    this.ws.close();
  }
}

// Usage
const oxide = new OxideWebSocket('ws://localhost:8000/ws');
```

## Message Types

### 1. Ping/Pong (Keepalive)

The server sends periodic ping messages to keep connections alive.

**Server → Client (Ping):**
```json
{
  "type": "ping",
  "timestamp": 1640995200
}
```

**Client → Server (Pong):**
```json
{
  "type": "pong",
  "timestamp": 1640995200
}
```

### 2. Metrics Update

Real-time system and service metrics.

**Server → Client:**
```json
{
  "type": "metrics",
  "timestamp": 1640995200,
  "data": {
    "services": {
      "total": 6,
      "healthy": 5,
      "unhealthy": 1,
      "enabled": 6
    },
    "tasks": {
      "total": 150,
      "running": 3,
      "completed": 145,
      "failed": 2,
      "success_rate": 0.987
    },
    "system": {
      "cpu_percent": 45.2,
      "memory_percent": 62.8,
      "memory_used_mb": 3072,
      "memory_total_mb": 4896,
      "disk_percent": 34.1
    },
    "costs": {
      "total_usd": 12.45,
      "today_usd": 0.82
    }
  }
}
```

### 3. Service Status Update

Service health status changes.

**Server → Client:**
```json
{
  "type": "service_status",
  "timestamp": 1640995200,
  "service": "ollama_local",
  "data": {
    "healthy": true,
    "enabled": true,
    "last_check": 1640995195,
    "response_time_ms": 45,
    "info": {
      "type": "http",
      "base_url": "http://localhost:11434",
      "model": "llama2"
    }
  }
}
```

### 4. Task Progress

Real-time task execution updates.

**Server → Client (Task Started):**
```json
{
  "type": "task_progress",
  "timestamp": 1640995200,
  "task_id": "abc123",
  "status": "started",
  "data": {
    "prompt": "Explain quantum computing",
    "task_type": "question_answer",
    "service": "ollama_local"
  }
}
```

**Server → Client (Task Running):**
```json
{
  "type": "task_progress",
  "timestamp": 1640995202,
  "task_id": "abc123",
  "status": "running",
  "data": {
    "progress": 45,
    "tokens_generated": 120
  }
}
```

**Server → Client (Task Completed):**
```json
{
  "type": "task_progress",
  "timestamp": 1640995205,
  "task_id": "abc123",
  "status": "completed",
  "data": {
    "result": "Quantum computing is...",
    "execution_time": 5.2,
    "tokens_used": 450,
    "cost": 0.002
  }
}
```

**Server → Client (Task Failed):**
```json
{
  "type": "task_progress",
  "timestamp": 1640995205,
  "task_id": "abc123",
  "status": "failed",
  "data": {
    "error": "Service timeout",
    "error_code": "TIMEOUT",
    "execution_time": 30.0
  }
}
```

### 5. Task History Update

Notification of new tasks in history.

**Server → Client:**
```json
{
  "type": "task_history",
  "timestamp": 1640995200,
  "data": {
    "id": "abc123",
    "prompt": "Explain quantum computing",
    "task_type": "question_answer",
    "service": "ollama_local",
    "status": "completed",
    "created_at": "2024-12-27T12:00:00Z",
    "completed_at": "2024-12-27T12:00:05Z",
    "execution_time": 5.2
  }
}
```

### 6. Configuration Update

Notification of configuration changes.

**Server → Client:**
```json
{
  "type": "config_update",
  "timestamp": 1640995200,
  "data": {
    "changed": ["services.ollama.enabled", "routing.rules"],
    "reload_required": false
  }
}
```

### 7. Error Notification

Server-side errors or warnings.

**Server → Client:**
```json
{
  "type": "error",
  "timestamp": 1640995200,
  "severity": "warning",
  "data": {
    "message": "Service 'gemini' is currently unavailable",
    "code": "SERVICE_UNAVAILABLE",
    "service": "gemini"
  }
}
```

## Client Messages (Optional)

### Subscribe to Topics

Request specific update types:

**Client → Server:**
```json
{
  "type": "subscribe",
  "topics": ["metrics", "tasks", "services"]
}
```

### Unsubscribe from Topics

**Client → Server:**
```json
{
  "type": "unsubscribe",
  "topics": ["metrics"]
}
```

### Request Snapshot

Get current state immediately:

**Client → Server:**
```json
{
  "type": "snapshot",
  "include": ["metrics", "services"]
}
```

## Complete React Example

```jsx
import { useEffect, useState, useCallback } from 'react';

function useOxideWebSocket() {
  const [connected, setConnected] = useState(false);
  const [metrics, setMetrics] = useState(null);
  const [services, setServices] = useState({});
  const [tasks, setTasks] = useState([]);
  const [ws, setWs] = useState(null);

  const connect = useCallback(() => {
    const websocket = new WebSocket('ws://localhost:8000/ws');

    websocket.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);

      // Subscribe to all topics
      websocket.send(JSON.stringify({
        type: 'subscribe',
        topics: ['metrics', 'services', 'tasks']
      }));

      // Request initial snapshot
      websocket.send(JSON.stringify({
        type: 'snapshot',
        include: ['metrics', 'services']
      }));
    };

    websocket.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);

      // Reconnect after 3 seconds
      setTimeout(connect, 3000);
    };

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);

      switch (message.type) {
        case 'ping':
          // Respond to ping
          websocket.send(JSON.stringify({ type: 'pong' }));
          break;

        case 'metrics':
          setMetrics(message.data);
          break;

        case 'service_status':
          setServices(prev => ({
            ...prev,
            [message.service]: message.data
          }));
          break;

        case 'task_progress':
          setTasks(prev => {
            const existing = prev.find(t => t.id === message.task_id);
            if (existing) {
              return prev.map(t =>
                t.id === message.task_id
                  ? { ...t, status: message.status, ...message.data }
                  : t
              );
            }
            return [...prev, {
              id: message.task_id,
              status: message.status,
              ...message.data
            }];
          });
          break;

        default:
          console.log('Unknown message type:', message.type);
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, []);

  useEffect(() => {
    const cleanup = connect();
    return cleanup;
  }, [connect]);

  return {
    connected,
    metrics,
    services,
    tasks,
    ws
  };
}

// Usage in component
function Dashboard() {
  const { connected, metrics, services, tasks } = useOxideWebSocket();

  return (
    <div>
      <div>Status: {connected ? '🟢 Connected' : '🔴 Disconnected'}</div>

      {metrics && (
        <div>
          <h2>System Metrics</h2>
          <p>CPU: {metrics.system.cpu_percent}%</p>
          <p>Memory: {metrics.system.memory_percent}%</p>
          <p>Tasks: {metrics.tasks.running} running, {metrics.tasks.completed} completed</p>
        </div>
      )}

      <div>
        <h2>Services</h2>
        {Object.entries(services).map(([name, data]) => (
          <div key={name}>
            {name}: {data.healthy ? '✅' : '❌'}
          </div>
        ))}
      </div>

      <div>
        <h2>Active Tasks</h2>
        {tasks.filter(t => t.status === 'running').map(task => (
          <div key={task.id}>
            Task {task.id}: {task.progress}%
          </div>
        ))}
      </div>
    </div>
  );
}
```

## Rate Limiting

WebSocket connections are rate-limited:
- **Maximum connections per IP**: 5
- **Message rate**: 100 messages per minute
- **Idle timeout**: 5 minutes

## Compression

WebSocket messages support per-message deflate compression. Enable in your client:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws', {
  perMessageDeflate: true
});
```

## Error Codes

| Code | Reason | Description |
|------|--------|-------------|
| 1000 | Normal Closure | Connection closed normally |
| 1001 | Going Away | Server shutting down |
| 1002 | Protocol Error | Invalid message format |
| 1003 | Unsupported Data | Invalid message type |
| 1008 | Policy Violation | Rate limit exceeded |
| 1011 | Internal Error | Server error |

## Best Practices

### 1. Implement Reconnection Logic

Always implement automatic reconnection with exponential backoff:

```javascript
let reconnectDelay = 1000;
const maxDelay = 30000;

function connect() {
  const ws = new WebSocket('ws://localhost:8000/ws');

  ws.onclose = () => {
    setTimeout(() => {
      reconnectDelay = Math.min(reconnectDelay * 2, maxDelay);
      connect();
    }, reconnectDelay);
  };

  ws.onopen = () => {
    reconnectDelay = 1000; // Reset delay on successful connection
  };
}
```

### 2. Handle Connection State

Track connection state to show users when they're disconnected:

```javascript
const [connectionState, setConnectionState] = useState('connecting');

ws.onopen = () => setConnectionState('connected');
ws.onclose = () => setConnectionState('disconnected');
ws.onerror = () => setConnectionState('error');
```

### 3. Respond to Ping Messages

Always respond to ping messages to keep the connection alive:

```javascript
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === 'ping') {
    ws.send(JSON.stringify({ type: 'pong', timestamp: message.timestamp }));
  }
};
```

### 4. Clean Up on Unmount

Close WebSocket connections when components unmount:

```javascript
useEffect(() => {
  const ws = new WebSocket('ws://localhost:8000/ws');

  return () => {
    ws.close();
  };
}, []);
```

## Next Steps

- [REST API](./overview) - Complete REST API reference
- [MCP Tools](./mcp-tools) - Model Context Protocol integration
- [Examples](../examples/websocket) - More WebSocket examples
