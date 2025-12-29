---
sidebar_position: 1
---

# Python API Examples

Learn how to integrate Oxide into your Python applications.

## Basic Usage

### Simple Task Execution

```python
import asyncio
import aiohttp

async def execute_task():
    """Execute a simple question-answering task."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/api/tasks/execute/",
            json={
                "prompt": "Explain quantum computing in simple terms",
                "task_type": "question_answer",
                "max_tokens": 500
            }
        ) as response:
            result = await response.json()
            print(f"Task ID: {result['task_id']}")
            print(f"Service Used: {result['service_used']}")
            print(f"Result: {result['result']}")
            print(f"Execution Time: {result['execution_time']}s")

# Run
asyncio.run(execute_task())
```

### With File Context

```python
import asyncio
import aiohttp

async def analyze_code():
    """Analyze code files for bugs."""
    files_to_analyze = [
        "/path/to/auth.py",
        "/path/to/database.py",
        "/path/to/api.py"
    ]

    # Read file contents
    file_contents = {}
    for file_path in files_to_analyze:
        with open(file_path, 'r') as f:
            file_contents[file_path] = f.read()

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/api/tasks/execute/",
            json={
                "prompt": "Review these files for potential security vulnerabilities",
                "task_type": "code_review",
                "files": file_contents,
                "max_tokens": 2000
            }
        ) as response:
            result = await response.json()
            print(f"Analysis Result:\\n{result['result']}")

asyncio.run(analyze_code())
```

## Oxide Client Class

### Complete Python Client

```python
import aiohttp
import asyncio
from typing import Optional, Dict, List, Any
import json

class OxideClient:
    """Python client for Oxide LLM Orchestrator API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None
    ):
        """
        Initialize Oxide client.

        Args:
            base_url: Oxide API base URL
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        headers = {}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def execute_task(
        self,
        prompt: str,
        task_type: str = "general",
        files: Optional[Dict[str, str]] = None,
        service: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a task with Oxide.

        Args:
            prompt: The task prompt
            task_type: Type of task (question_answer, code_generation, etc.)
            files: Optional dictionary of file_path: file_content
            service: Optional service override
            max_tokens: Maximum tokens for response
            temperature: Sampling temperature (0-1)
            **kwargs: Additional parameters

        Returns:
            Task execution result
        """
        payload = {
            "prompt": prompt,
            "task_type": task_type,
            **kwargs
        }

        if files:
            payload["files"] = files
        if service:
            payload["service"] = service
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature

        async with self.session.post(
            f"{self.base_url}/api/tasks/execute/",
            json=payload
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """
        Get task details by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task details
        """
        async with self.session.get(
            f"{self.base_url}/api/tasks/{task_id}/"
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def list_services(self) -> Dict[str, Any]:
        """
        List all available LLM services.

        Returns:
            Service status and information
        """
        async with self.session.get(
            f"{self.base_url}/api/services/"
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics.

        Returns:
            System and service metrics
        """
        async with self.session.get(
            f"{self.base_url}/api/monitoring/metrics/"
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def get_task_history(
        self,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get task execution history.

        Args:
            limit: Number of tasks to return
            offset: Number of tasks to skip

        Returns:
            Task history
        """
        async with self.session.get(
            f"{self.base_url}/api/tasks/history/",
            params={"limit": limit, "offset": offset}
        ) as response:
            response.raise_for_status()
            return await response.json()


# Example usage
async def main():
    """Example usage of OxideClient."""
    async with OxideClient() as client:
        # Execute a task
        result = await client.execute_task(
            prompt="Write a Python function to calculate fibonacci numbers",
            task_type="code_generation",
            max_tokens=500
        )
        print(f"Generated Code:\\n{result['result']}")

        # List available services
        services = await client.list_services()
        print(f"\\nAvailable Services: {services['total']}")

        # Get system metrics
        metrics = await client.get_metrics()
        print(f"\\nCPU Usage: {metrics['system']['cpu_percent']}%")

        # Get task history
        history = await client.get_task_history(limit=5)
        print(f"\\nRecent Tasks: {history['total']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Batch Processing

### Process Multiple Tasks

```python
import asyncio
import aiohttp
from typing import List, Dict

async def batch_execute(
    tasks: List[Dict],
    base_url: str = "http://localhost:8000"
) -> List[Dict]:
    """
    Execute multiple tasks in parallel.

    Args:
        tasks: List of task configurations
        base_url: Oxide API URL

    Returns:
        List of results
    """
    async with aiohttp.ClientSession() as session:
        async def execute_single(task):
            async with session.post(
                f"{base_url}/api/tasks/execute/",
                json=task
            ) as response:
                return await response.json()

        # Execute all tasks concurrently
        results = await asyncio.gather(*[
            execute_single(task) for task in tasks
        ])

        return results


# Example usage
async def main():
    tasks = [
        {
            "prompt": "Explain quantum computing",
            "task_type": "question_answer"
        },
        {
            "prompt": "Write a sorting algorithm in Python",
            "task_type": "code_generation"
        },
        {
            "prompt": "Summarize this article: [long text]",
            "task_type": "summarization"
        }
    ]

    results = await batch_execute(tasks)

    for i, result in enumerate(results, 1):
        print(f"\\nTask {i}:")
        print(f"Service: {result['service_used']}")
        print(f"Time: {result['execution_time']}s")

asyncio.run(main())
```

## Stream Processing

### Handle Streaming Responses

```python
import aiohttp
import asyncio
import json

async def stream_task():
    """Stream task execution in real-time."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/api/tasks/execute/",
            json={
                "prompt": "Write a detailed explanation of machine learning",
                "task_type": "question_answer",
                "stream": True  # Enable streaming
            }
        ) as response:
            # Process streaming response
            async for line in response.content:
                if line:
                    try:
                        chunk = json.loads(line.decode())
                        if chunk.get('type') == 'content':
                            print(chunk['data'], end='', flush=True)
                        elif chunk.get('type') == 'done':
                            print(f"\\n\\nCompleted in {chunk['execution_time']}s")
                    except json.JSONDecodeError:
                        pass

asyncio.run(stream_task())
```

## Error Handling

### Robust Error Handling

```python
import aiohttp
import asyncio
from typing import Optional, Dict

class OxideAPIError(Exception):
    """Custom exception for Oxide API errors."""
    def __init__(self, status_code: int, message: str, details: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.details = details
        super().__init__(f"{status_code}: {message}")


async def execute_with_retry(
    prompt: str,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> Dict:
    """
    Execute task with automatic retry on failure.

    Args:
        prompt: Task prompt
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        Task result

    Raises:
        OxideAPIError: If all retries fail
    """
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8000/api/tasks/execute/",
                    json={"prompt": prompt, "task_type": "question_answer"},
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_data = await response.json()
                        raise OxideAPIError(
                            status_code=response.status,
                            message=error_data.get('error', 'Unknown error'),
                            details=error_data
                        )

        except aiohttp.ClientError as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay * (attempt + 1))
            else:
                raise OxideAPIError(
                    status_code=500,
                    message=f"Connection error: {str(e)}"
                )


# Example usage
async def main():
    try:
        result = await execute_with_retry(
            "Explain artificial intelligence",
            max_retries=3
        )
        print(f"Success: {result['task_id']}")
    except OxideAPIError as e:
        print(f"Error: {e.message}")
        if e.details:
            print(f"Details: {e.details}")

asyncio.run(main())
```

## Monitoring Integration

### Real-time Monitoring

```python
import aiohttp
import asyncio
import json

async def monitor_metrics(interval: int = 5):
    """Monitor Oxide metrics in real-time."""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(
                    "http://localhost:8000/api/monitoring/metrics/"
                ) as response:
                    metrics = await response.json()

                    print(f"\\n=== Oxide Metrics ===")
                    print(f"Services: {metrics['services']['healthy']}/{metrics['services']['total']} healthy")
                    print(f"Tasks: {metrics['tasks']['running']} running, {metrics['tasks']['completed']} completed")
                    print(f"CPU: {metrics['system']['cpu_percent']}%")
                    print(f"Memory: {metrics['system']['memory_percent']}%")

            except Exception as e:
                print(f"Error fetching metrics: {e}")

            await asyncio.sleep(interval)

# Run monitoring
asyncio.run(monitor_metrics(interval=5))
```

## Next Steps

- [JavaScript Examples](./javascript-api) - Using Oxide with JavaScript
- [WebSocket Example](./websocket) - Real-time updates
- [MCP Integration](./mcp-integration) - Using with Claude Code
