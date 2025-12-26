"""
Tests for Context Memory System

Tests all core functionality:
- Add and retrieve conversations
- Recent context retrieval
- Similarity search
- Conversation pruning
- Memory statistics
"""
import pytest
import tempfile
import time
from pathlib import Path

from oxide.memory.context_memory import ContextMemory


@pytest.fixture
def temp_memory():
    """Create a temporary memory instance for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_memory.json"
        memory = ContextMemory(storage_path=storage_path)
        yield memory


def test_add_context(temp_memory):
    """Test adding context to memory"""
    msg_id = temp_memory.add_context(
        conversation_id="test_conv_1",
        role="user",
        content="Hello, world!",
        metadata={"task_type": "quick_query"}
    )

    assert msg_id is not None
    assert msg_id.startswith("test_conv_1_")

    # Verify conversation exists
    conv = temp_memory.get_conversation("test_conv_1")
    assert conv is not None
    assert len(conv["messages"]) == 1
    assert conv["messages"][0]["content"] == "Hello, world!"
    assert conv["messages"][0]["role"] == "user"


def test_multiple_messages(temp_memory):
    """Test adding multiple messages to same conversation"""
    conv_id = "test_conv_2"

    # Add user message
    temp_memory.add_context(conv_id, "user", "What is Python?")

    # Add assistant response
    temp_memory.add_context(
        conv_id,
        "assistant",
        "Python is a high-level programming language."
    )

    # Add follow-up
    temp_memory.add_context(conv_id, "user", "Tell me more.")

    conv = temp_memory.get_conversation(conv_id)
    assert len(conv["messages"]) == 3
    assert conv["messages"][0]["role"] == "user"
    assert conv["messages"][1]["role"] == "assistant"
    assert conv["messages"][2]["role"] == "user"


def test_get_recent_context(temp_memory):
    """Test retrieving recent context"""
    conv_id = "test_conv_3"

    # Add 10 messages
    for i in range(10):
        role = "user" if i % 2 == 0 else "assistant"
        temp_memory.add_context(conv_id, role, f"Message {i}")

    # Get recent 5 messages
    recent = temp_memory.get_recent_context(conv_id, max_messages=5)

    assert len(recent) == 5
    # Should be in reverse order (most recent first)
    assert recent[0]["content"] == "Message 9"
    assert recent[4]["content"] == "Message 5"


def test_get_recent_context_with_age_filter(temp_memory):
    """Test retrieving recent context with age filter"""
    conv_id = "test_conv_4"

    # Add old message
    temp_memory.add_context(conv_id, "user", "Old message")

    # Wait a bit
    time.sleep(0.1)

    # Add new message
    temp_memory.add_context(conv_id, "user", "New message")

    # Get messages from last 1 second
    recent = temp_memory.get_recent_context(conv_id, max_age_hours=1)

    assert len(recent) == 2  # Both should be within 1 hour


def test_search_similar_conversations(temp_memory):
    """Test similarity search"""
    # Add conversations about Python
    temp_memory.add_context("conv_python_1", "user", "How do I use Python decorators?")
    temp_memory.add_context("conv_python_1", "assistant", "Decorators are functions that modify other functions.")

    temp_memory.add_context("conv_python_2", "user", "Explain Python generators")
    temp_memory.add_context("conv_python_2", "assistant", "Generators use yield to produce values lazily.")

    # Add conversation about JavaScript
    temp_memory.add_context("conv_js_1", "user", "How do JavaScript promises work?")
    temp_memory.add_context("conv_js_1", "assistant", "Promises represent asynchronous operations.")

    # Search for Python-related conversations
    results = temp_memory.search_similar_conversations(
        query="Python decorators generators",
        limit=5,
        min_similarity=0.05  # Lower threshold for keyword-based matching
    )

    # Should find Python conversations
    assert len(results) >= 2
    # Verify at least one result contains "python" in the conversation_id or has similarity
    python_results = [r for r in results if "python" in r["conversation_id"].lower()]
    assert len(python_results) >= 1


def test_get_context_for_task(temp_memory):
    """Test getting context for a new task"""
    # Add relevant conversation
    temp_memory.add_context(
        "conv_coding_1",
        "user",
        "Write a Python function to calculate factorial",
        metadata={"task_type": "code_generation"}
    )
    temp_memory.add_context(
        "conv_coding_1",
        "assistant",
        "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"
    )

    # Get context for similar task
    context = temp_memory.get_context_for_task(
        task_type="code_generation",
        prompt="Write a Python function for fibonacci",
        max_messages=5,
        max_age_hours=24
    )

    # Should retrieve relevant context
    assert isinstance(context, list)


def test_prune_old_conversations(temp_memory):
    """Test pruning old conversations"""
    # Add some conversations
    for i in range(5):
        temp_memory.add_context(f"conv_{i}", "user", f"Message {i}")

    # Manually set some as old (hack for testing)
    old_time = time.time() - (31 * 86400)  # 31 days ago
    temp_memory._memory["conv_0"]["updated_at"] = old_time
    temp_memory._memory["conv_1"]["updated_at"] = old_time
    temp_memory._save_memory()

    # Prune conversations older than 30 days
    removed = temp_memory.prune_old_conversations(max_age_days=30)

    assert removed == 2
    assert "conv_0" not in temp_memory._memory
    assert "conv_1" not in temp_memory._memory
    assert "conv_2" in temp_memory._memory


def test_get_statistics(temp_memory):
    """Test memory statistics"""
    # Add some data
    for i in range(3):
        conv_id = f"conv_{i}"
        for j in range(i + 1):  # Different message counts
            temp_memory.add_context(conv_id, "user", f"Message {j}")

    stats = temp_memory.get_statistics()

    assert stats["total_conversations"] == 3
    assert stats["total_messages"] == 6  # 1 + 2 + 3
    assert stats["average_messages_per_conversation"] == 2.0
    assert stats["oldest_conversation"] is not None
    assert stats["newest_conversation"] is not None
    assert "storage_path" in stats


def test_clear_all(temp_memory):
    """Test clearing all memory"""
    # Add data
    temp_memory.add_context("conv_1", "user", "Hello")
    temp_memory.add_context("conv_2", "user", "World")

    assert len(temp_memory._memory) == 2

    # Clear
    temp_memory.clear_all()

    assert len(temp_memory._memory) == 0

    # Verify stats are zeroed
    stats = temp_memory.get_statistics()
    assert stats["total_conversations"] == 0
    assert stats["total_messages"] == 0


def test_persistence(temp_memory):
    """Test that memory persists to disk"""
    # Add data
    temp_memory.add_context("conv_persist", "user", "Persistent message")

    storage_path = temp_memory.storage_path

    # Create new instance with same storage
    new_memory = ContextMemory(storage_path=storage_path)

    # Should load existing data
    conv = new_memory.get_conversation("conv_persist")
    assert conv is not None
    assert len(conv["messages"]) == 1
    assert conv["messages"][0]["content"] == "Persistent message"


def test_metadata_storage(temp_memory):
    """Test that metadata is properly stored"""
    metadata = {
        "task_type": "code_review",
        "service": "qwen",
        "files": ["test.py"],
        "custom": "value"
    }

    temp_memory.add_context(
        "conv_meta",
        "user",
        "Review this code",
        metadata=metadata
    )

    conv = temp_memory.get_conversation("conv_meta")
    msg = conv["messages"][0]

    assert msg["metadata"] == metadata
    assert msg["metadata"]["task_type"] == "code_review"
    assert msg["metadata"]["custom"] == "value"


def test_empty_conversation(temp_memory):
    """Test behavior with non-existent conversation"""
    conv = temp_memory.get_conversation("non_existent")
    assert conv is None

    recent = temp_memory.get_recent_context("non_existent")
    assert recent == []


def test_conversation_timestamps(temp_memory):
    """Test that timestamps are properly recorded"""
    before = time.time()

    temp_memory.add_context("conv_time", "user", "Test message")

    after = time.time()

    conv = temp_memory.get_conversation("conv_time")
    assert before <= conv["created_at"] <= after
    assert before <= conv["updated_at"] <= after

    msg = conv["messages"][0]
    assert before <= msg["timestamp"] <= after


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
