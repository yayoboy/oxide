---
sidebar_position: 1
slug: /
---

# Welcome to Oxide

**Intelligent LLM Orchestration for Distributed AI Resources**

Oxide is a powerful orchestration system that provides intelligent routing, monitoring, and management for multiple LLM providers. Think of it as a reverse proxy and load balancer for AI services.

## What is Oxide?

Oxide solves the complexity of managing multiple LLM providers by providing:

- **🎯 Smart Routing**: Automatically route tasks to the best available service based on task type, provider capabilities, cost, and performance
- **📊 Unified Monitoring**: Single dashboard to monitor all your LLM services (local and remote)
- **💰 Cost Tracking**: Track API usage costs across all providers with budget alerts
- **🔐 Secure**: Built-in authentication, rate limiting, and API key management
- **🌐 Distributed**: Multi-node cluster support with automatic failover
- **⚡ High Performance**: Async I/O, connection pooling, and intelligent caching

## Supported Providers

### Local Services
- **Ollama**: Local LLM inference server
- **LM Studio**: Desktop LLM application with OpenAI-compatible API

### Remote APIs
- **OpenRouter**: Unified API for 200+ LLM models
- **OpenAI**: GPT-4, GPT-3.5-turbo, and more
- **Anthropic**: Claude 3 family
- **Google**: Gemini Pro and Gemini Ultra
- **Groq**: Ultra-fast LLM inference

### CLI Tools
- **aichat**: Versatile CLI LLM client
- **fabric**: AI-powered content processing
- **llm**: Simon Willison's LLM CLI tool

## Quick Example

```python
from oxide import Orchestrator
from oxide.config import load_config

# Initialize orchestrator
config = load_config("config/default.yaml")
orchestrator = Orchestrator(config)

# Execute a task (auto-routed to best service)
result = await orchestrator.execute({
    "prompt": "Explain quantum computing",
    "task_type": "question_answer",
    "max_tokens": 500
})

print(result)
```

## Why Use Oxide?

### Problem: Managing Multiple LLM Providers is Complex

- Different APIs, authentication methods, and response formats
- No unified way to track costs across providers
- Manual failover when services go down
- Difficult to optimize routing for cost and performance

### Solution: Oxide Handles Everything

Oxide acts as a centralized orchestration layer:
- **Your Application** → **Oxide Orchestrator** → **Multiple LLM Providers**

## Key Features

### Intelligent Routing

Tasks are automatically routed based on:
- **Task Type**: Questions, summarization, code generation, etc.
- **Provider Capabilities**: Model features, context windows, speed
- **Cost**: Optimize for budget constraints
- **Performance**: Track response times and reliability

### Real-time Monitoring

WebSocket-based live dashboard showing:
- Service health status
- Active tasks and queue depth
- System resources (CPU, memory)
- Cost tracking and budget alerts

### Context Memory

Oxide maintains conversation context across multiple interactions:
- **Session Management**: Track conversation threads
- **Vector Storage**: Semantic search for relevant context
- **Auto-cleanup**: Configurable retention policies

### Cluster Support

Deploy Oxide across multiple machines for:
- **High Availability**: Automatic failover
- **Load Balancing**: Distribute tasks across nodes
- **Horizontal Scaling**: Add capacity on demand

## Getting Started

Ready to get started? Check out the guides:

- [Installation Guide](./guides/installation) - Set up Oxide in your environment
- [Quickstart](./guides/quickstart) - Get running in 5 minutes
- [Configuration](./guides/configuration) - Configure services and routing
- [API Reference](./api/overview) - Complete API documentation

## Community & Support

- **Documentation**: You're reading it! 📖
- **GitHub**: [yayoboy/oxide](https://github.com/yayoboy/oxide)
- **Issues**: Report bugs and feature requests
- **Discussions**: Ask questions and share ideas

## License

Oxide is open-source software licensed under the [MIT License](https://opensource.org/licenses/MIT).
