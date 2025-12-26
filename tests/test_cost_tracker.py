"""
Tests for Cost Tracker

Tests LLM cost tracking and analytics:
- Cost recording
- Token counting
- Cost calculations
- Budget alerts
- Statistics
"""
import pytest
import tempfile
import time
from pathlib import Path

from oxide.analytics.cost_tracker import CostTracker, ServicePricing


@pytest.fixture
def temp_tracker():
    """Create a temporary cost tracker for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_costs.db"
        tracker = CostTracker(db_path=db_path)
        yield tracker


def test_tracker_initialization(temp_tracker):
    """Test tracker initialization"""
    assert temp_tracker.db_path.exists()
    assert len(temp_tracker.pricing) > 0
    # Default pricing should include main services
    assert "gemini" in temp_tracker.pricing
    assert "qwen" in temp_tracker.pricing
    assert "ollama_local" in temp_tracker.pricing


def test_estimate_tokens(temp_tracker):
    """Test token estimation"""
    # ~4 characters per token
    text = "Hello world! This is a test."  # 29 characters
    tokens = temp_tracker.estimate_tokens(text)

    assert tokens > 0
    assert 5 <= tokens <= 10  # Should be around 7-8 tokens


def test_record_cost_with_token_counts(temp_tracker):
    """Test recording cost with explicit token counts"""
    record = temp_tracker.record_cost(
        task_id="test_task_1",
        service="gemini",
        tokens_input=1000,
        tokens_output=500
    )

    assert record.task_id == "test_task_1"
    assert record.service == "gemini"
    assert record.tokens_input == 1000
    assert record.tokens_output == 500
    assert record.cost_usd > 0  # Gemini has cost


def test_record_cost_with_text_estimation(temp_tracker):
    """Test recording cost with text estimation"""
    prompt = "Write a Python function to calculate factorial"
    response = "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)"

    record = temp_tracker.record_cost(
        task_id="test_task_2",
        service="gemini",
        prompt=prompt,
        response=response
    )

    assert record.tokens_input > 0
    assert record.tokens_output > 0
    assert record.cost_usd > 0


def test_free_services_have_zero_cost(temp_tracker):
    """Test that local/free services have zero cost"""
    # Ollama is free (self-hosted)
    record = temp_tracker.record_cost(
        task_id="test_task_3",
        service="ollama_local",
        tokens_input=1000,
        tokens_output=1000
    )

    assert record.cost_usd == 0.0


def test_get_total_cost(temp_tracker):
    """Test getting total cost"""
    # Record some costs
    temp_tracker.record_cost("task1", "gemini", tokens_input=1000, tokens_output=500)
    temp_tracker.record_cost("task2", "gemini", tokens_input=2000, tokens_output=1000)

    total = temp_tracker.get_total_cost()
    assert total > 0


def test_get_total_cost_filtered_by_service(temp_tracker):
    """Test getting total cost filtered by service"""
    # Record costs for different services
    temp_tracker.record_cost("task1", "gemini", tokens_input=1000, tokens_output=500)
    temp_tracker.record_cost("task2", "ollama_local", tokens_input=1000, tokens_output=500)

    gemini_cost = temp_tracker.get_total_cost(service="gemini")
    ollama_cost = temp_tracker.get_total_cost(service="ollama_local")

    assert gemini_cost > 0
    assert ollama_cost == 0.0  # Ollama is free


def test_get_total_cost_filtered_by_time(temp_tracker):
    """Test getting total cost filtered by time range"""
    now = time.time()
    hour_ago = now - 3600

    # Record old cost
    temp_tracker.record_cost("task_old", "gemini", tokens_input=1000, tokens_output=500)

    # Manually update timestamp to be older
    import sqlite3
    conn = sqlite3.connect(str(temp_tracker.db_path))
    cursor = conn.cursor()
    cursor.execute("UPDATE llm_costs SET timestamp = ? WHERE task_id = ?", (hour_ago - 100, "task_old"))
    conn.commit()
    conn.close()

    # Record new cost
    temp_tracker.record_cost("task_new", "gemini", tokens_input=1000, tokens_output=500)

    # Get costs from last hour only
    recent_cost = temp_tracker.get_total_cost(start_time=hour_ago)

    # Should only include new cost
    assert recent_cost > 0


def test_get_cost_by_service(temp_tracker):
    """Test getting cost breakdown by service"""
    temp_tracker.record_cost("task1", "gemini", tokens_input=1000, tokens_output=500)
    temp_tracker.record_cost("task2", "gemini", tokens_input=1000, tokens_output=500)
    temp_tracker.record_cost("task3", "qwen", tokens_input=1000, tokens_output=500)

    breakdown = temp_tracker.get_cost_by_service()

    assert "gemini" in breakdown
    assert breakdown["gemini"] > 0
    # Qwen should be free
    assert breakdown.get("qwen", 0) == 0


def test_get_token_usage(temp_tracker):
    """Test getting token usage statistics"""
    temp_tracker.record_cost("task1", "gemini", tokens_input=1000, tokens_output=500)
    temp_tracker.record_cost("task2", "gemini", tokens_input=2000, tokens_output=1000)

    usage = temp_tracker.get_token_usage()

    assert usage["input_tokens"] == 3000
    assert usage["output_tokens"] == 1500
    assert usage["total_tokens"] == 4500


def test_set_budget(temp_tracker):
    """Test setting a budget"""
    temp_tracker.set_budget(
        period="2025-01",
        limit_usd=100.0,
        alert_threshold=0.8
    )

    # Verify budget was saved
    import sqlite3
    conn = sqlite3.connect(str(temp_tracker.db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT limit_usd, alert_threshold FROM budgets WHERE period = ? AND active = 1", ("2025-01",))
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[0] == 100.0
    assert result[1] == 0.8


def test_budget_alert_not_exceeded(temp_tracker):
    """Test budget alert when not exceeded"""
    # Set budget
    temp_tracker.set_budget("2025-01", limit_usd=100.0, alert_threshold=0.8)

    # Record small cost
    temp_tracker.record_cost("task1", "gemini", tokens_input=100, tokens_output=50)

    # Check alert
    alert = temp_tracker.check_budget_alert("2025-01")

    # Should not trigger (cost is too small)
    assert alert is None


def test_budget_alert_exceeded(temp_tracker):
    """Test budget alert when threshold exceeded"""
    # Set very low budget for testing
    temp_tracker.set_budget("2025-01", limit_usd=0.001, alert_threshold=0.5)

    # Record cost that exceeds threshold
    temp_tracker.record_cost("task1", "gemini", tokens_input=10000, tokens_output=5000)

    # Manually set timestamp to current month
    import sqlite3
    from datetime import datetime
    current_month = datetime.now().strftime("%Y-%m")

    conn = sqlite3.connect(str(temp_tracker.db_path))
    cursor = conn.cursor()
    cursor.execute("UPDATE llm_costs SET timestamp = ?", (time.time(),))
    cursor.execute("UPDATE budgets SET period = ?", (current_month,))
    conn.commit()
    conn.close()

    # Check alert
    alert = temp_tracker.check_budget_alert(current_month)

    # Should trigger
    assert alert is not None
    assert alert["usage_percent"] >= 0.5


def test_get_statistics(temp_tracker):
    """Test getting overall statistics"""
    # Record some costs
    temp_tracker.record_cost("task1", "gemini", tokens_input=1000, tokens_output=500)
    temp_tracker.record_cost("task2", "qwen", tokens_input=2000, tokens_output=1000)

    stats = temp_tracker.get_statistics()

    assert "total_cost" in stats
    assert "cost_24h" in stats
    assert "by_service" in stats
    assert "token_usage" in stats
    assert "daily_costs" in stats

    assert stats["total_cost"] > 0
    assert len(stats["by_service"]) > 0


def test_daily_costs(temp_tracker):
    """Test getting daily cost breakdown"""
    # Record costs
    temp_tracker.record_cost("task1", "gemini", tokens_input=1000, tokens_output=500)

    daily = temp_tracker.get_daily_costs(days=7)

    assert isinstance(daily, list)
    # Should have at least today's costs
    assert len(daily) >= 1


def test_multiple_budgets_only_latest_active(temp_tracker):
    """Test that only latest budget for a period is active"""
    # Set first budget
    temp_tracker.set_budget("2025-01", limit_usd=50.0)

    # Set second budget (should deactivate first)
    temp_tracker.set_budget("2025-01", limit_usd=100.0)

    # Check that only one budget is active
    import sqlite3
    conn = sqlite3.connect(str(temp_tracker.db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM budgets WHERE period = ? AND active = 1", ("2025-01",))
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
