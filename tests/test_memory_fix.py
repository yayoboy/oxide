"""
Test suite for memory system fix (YAY-25, YAY-19).

Verifies that context memory is properly retrieved and injected into prompts.
"""
import pytest
from pathlib import Path
from oxide.memory.context_memory import ContextMemory
from oxide.core.orchestrator import Orchestrator


def test_memory_storage_and_retrieval():
    """Test that memory can store and retrieve conversations."""
    # Use temporary storage
    temp_storage = Path("/tmp/test_memory.json")
    if temp_storage.exists():
        temp_storage.unlink()

    memory = ContextMemory(storage_path=temp_storage)

    # Add some context
    memory.add_context(
        conversation_id="test_1",
        role="user",
        content="What is Python?"
    )

    memory.add_context(
        conversation_id="test_1",
        role="assistant",
        content="Python is a high-level programming language."
    )

    # Retrieve conversation
    conv = memory.get_conversation("test_1")
    assert conv is not None
    assert len(conv["messages"]) == 2
    assert conv["messages"][0]["content"] == "What is Python?"
    assert conv["messages"][1]["content"] == "Python is a high-level programming language."

    # Clean up
    temp_storage.unlink()


def test_context_retrieval_for_task():
    """Test that relevant context can be retrieved for new tasks."""
    temp_storage = Path("/tmp/test_memory_context.json")
    if temp_storage.exists():
        temp_storage.unlink()

    memory = ContextMemory(storage_path=temp_storage)

    # Add context about Python
    memory.add_context(
        conversation_id="python_conv",
        role="user",
        content="Tell me about Python programming"
    )

    memory.add_context(
        conversation_id="python_conv",
        role="assistant",
        content="Python is a versatile programming language"
    )

    # Retrieve context for similar task
    context = memory.get_context_for_task(
        task_type="quick_query",
        prompt="What language is good for beginners? I heard about Python.",
        max_messages=5,
        max_age_hours=24
    )

    # Should find relevant context
    assert len(context) > 0
    assert any("Python" in msg["content"] for msg in context)

    # Clean up
    temp_storage.unlink()


def test_format_context_for_prompt():
    """Test that context is properly formatted for prompt injection."""
    orch = Orchestrator()

    # Create sample context messages
    context_messages = [
        {
            "role": "user",
            "content": "What is Python?",
            "timestamp": 1234567890
        },
        {
            "role": "assistant",
            "content": "Python is a programming language.",
            "timestamp": 1234567891
        }
    ]

    # Format context
    formatted = orch._format_context_for_prompt(context_messages)

    # Verify formatting
    assert "Previous relevant conversation history:" in formatted
    assert "User: What is Python?" in formatted
    assert "Assistant: Python is a programming language." in formatted
    assert "Current task:" in formatted


def test_empty_context_formatting():
    """Test that empty context is handled gracefully."""
    orch = Orchestrator()

    formatted = orch._format_context_for_prompt([])
    assert formatted == ""

    formatted = orch._format_context_for_prompt(None)
    assert formatted == ""


if __name__ == "__main__":
    # Run tests
    print("Running memory system tests...")

    try:
        test_memory_storage_and_retrieval()
        print("✓ Memory storage and retrieval test passed")
    except AssertionError as e:
        print(f"✗ Memory storage test failed: {e}")

    try:
        test_context_retrieval_for_task()
        print("✓ Context retrieval for task test passed")
    except AssertionError as e:
        print(f"✗ Context retrieval test failed: {e}")

    try:
        test_format_context_for_prompt()
        print("✓ Context formatting test passed")
    except AssertionError as e:
        print(f"✗ Context formatting test failed: {e}")

    try:
        test_empty_context_formatting()
        print("✓ Empty context formatting test passed")
    except AssertionError as e:
        print(f"✗ Empty context formatting test failed: {e}")

    print("\nAll memory system tests completed!")
