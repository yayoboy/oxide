"""
LLM Cost Tracking and Analytics

Tracks token usage and costs for all LLM services:
- Token counting per task
- Cost calculation based on pricing
- Budget management and alerts
- Cost analytics and reports
"""
import sqlite3
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ServicePricing:
    """Pricing configuration for a service"""
    service: str
    cost_per_input_token: float  # USD per token
    cost_per_output_token: float  # USD per token
    currency: str = "USD"


@dataclass
class CostRecord:
    """Record of a task's cost"""
    id: Optional[int]
    task_id: str
    service: str
    tokens_input: int
    tokens_output: int
    cost_usd: float
    timestamp: float


class CostTracker:
    """
    Tracks LLM costs and provides analytics.

    Features:
    - Token counting and cost calculation
    - SQLite storage for historical data
    - Budget management with alerts
    - Cost analytics and reporting
    """

    # Default pricing (based on 2025 rates)
    DEFAULT_PRICING = {
        "gemini": ServicePricing(
            service="gemini",
            cost_per_input_token=0.00000035,   # $0.35 per 1M tokens
            cost_per_output_token=0.0000014    # $1.40 per 1M tokens
        ),
        "qwen": ServicePricing(
            service="qwen",
            cost_per_input_token=0.0,  # Local CLI - free
            cost_per_output_token=0.0
        ),
        "ollama_local": ServicePricing(
            service="ollama_local",
            cost_per_input_token=0.0,  # Local - free
            cost_per_output_token=0.0
        ),
        "ollama_remote": ServicePricing(
            service="ollama_remote",
            cost_per_input_token=0.0,  # Self-hosted - free
            cost_per_output_token=0.0
        ),
        "lmstudio": ServicePricing(
            service="lmstudio",
            cost_per_input_token=0.0,  # Self-hosted - free
            cost_per_output_token=0.0
        ),
        "openrouter": ServicePricing(
            service="openrouter",
            # Average pricing (varies by model - actual cost tracked from API response)
            cost_per_input_token=0.00000015,   # ~$0.15 per 1M tokens average
            cost_per_output_token=0.00000045   # ~$0.45 per 1M tokens average
        )
    }

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize cost tracker.

        Args:
            db_path: Path to SQLite database (default: ~/.oxide/costs.db)
        """
        self.logger = get_logger(__name__)

        if db_path is None:
            db_path = Path.home() / ".oxide" / "costs.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

        # Load pricing
        self.pricing = self.DEFAULT_PRICING.copy()
        self._load_custom_pricing()

        self.logger.info(f"Cost tracker initialized: {self.db_path}")

    def _init_db(self):
        """Initialize SQLite database schema"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Cost records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                service TEXT NOT NULL,
                tokens_input INTEGER NOT NULL,
                tokens_output INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                timestamp REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Service pricing table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_pricing (
                service TEXT PRIMARY KEY,
                cost_per_input_token REAL NOT NULL,
                cost_per_output_token REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Budget configuration table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period TEXT NOT NULL,
                limit_usd REAL NOT NULL,
                alert_threshold REAL DEFAULT 0.8,
                active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_costs_timestamp ON llm_costs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_costs_service ON llm_costs(service)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_costs_task_id ON llm_costs(task_id)")

        conn.commit()
        conn.close()

        self.logger.debug("Database schema initialized")

    def _load_custom_pricing(self):
        """Load custom pricing from database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT service, cost_per_input_token, cost_per_output_token, currency FROM service_pricing")
        rows = cursor.fetchall()

        for row in rows:
            service, input_cost, output_cost, currency = row
            self.pricing[service] = ServicePricing(
                service=service,
                cost_per_input_token=input_cost,
                cost_per_output_token=output_cost,
                currency=currency
            )

        conn.close()

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses simple approximation: ~4 characters per token
        """
        return max(1, len(text) // 4)

    def record_cost(
        self,
        task_id: str,
        service: str,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        prompt: Optional[str] = None,
        response: Optional[str] = None
    ) -> CostRecord:
        """
        Record cost for a task.

        Args:
            task_id: Task identifier
            service: Service name
            tokens_input: Input token count (or will estimate from prompt)
            tokens_output: Output token count (or will estimate from response)
            prompt: Prompt text (for estimation if tokens_input not provided)
            response: Response text (for estimation if tokens_output not provided)

        Returns:
            CostRecord
        """
        # Estimate tokens if not provided
        if tokens_input is None:
            tokens_input = self.estimate_tokens(prompt) if prompt else 0

        if tokens_output is None:
            tokens_output = self.estimate_tokens(response) if response else 0

        # Calculate cost
        pricing = self.pricing.get(service)
        if not pricing:
            self.logger.warning(f"No pricing for service: {service}, defaulting to $0")
            pricing = ServicePricing(service, 0.0, 0.0)

        cost_usd = (
            tokens_input * pricing.cost_per_input_token +
            tokens_output * pricing.cost_per_output_token
        )

        # Store in database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        timestamp = time.time()

        cursor.execute("""
            INSERT INTO llm_costs (task_id, service, tokens_input, tokens_output, cost_usd, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (task_id, service, tokens_input, tokens_output, cost_usd, timestamp))

        record_id = cursor.lastrowid
        conn.commit()
        conn.close()

        record = CostRecord(
            id=record_id,
            task_id=task_id,
            service=service,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost_usd,
            timestamp=timestamp
        )

        self.logger.debug(
            f"Recorded cost: {service} - ${cost_usd:.6f} "
            f"({tokens_input}in + {tokens_output}out tokens)"
        )

        return record

    def get_total_cost(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        service: Optional[str] = None
    ) -> float:
        """
        Get total cost for a time period.

        Args:
            start_time: Start timestamp (default: beginning of time)
            end_time: End timestamp (default: now)
            service: Filter by service

        Returns:
            Total cost in USD
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        query = "SELECT SUM(cost_usd) FROM llm_costs WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        if service:
            query += " AND service = ?"
            params.append(service)

        cursor.execute(query, params)
        result = cursor.fetchone()[0]
        conn.close()

        return result or 0.0

    def get_cost_by_service(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Get cost breakdown by service.

        Returns:
            Dict mapping service name to total cost
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        query = "SELECT service, SUM(cost_usd) FROM llm_costs WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " GROUP BY service"

        cursor.execute(query, params)
        results = {service: cost for service, cost in cursor.fetchall()}
        conn.close()

        return results

    def get_daily_costs(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get daily cost breakdown for last N days.

        Args:
            days: Number of days to include

        Returns:
            List of dicts with date and cost
        """
        cutoff = time.time() - (days * 86400)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DATE(timestamp, 'unixepoch') as date, SUM(cost_usd) as cost
            FROM llm_costs
            WHERE timestamp >= ?
            GROUP BY date
            ORDER BY date DESC
        """, (cutoff,))

        results = [
            {"date": row[0], "cost": row[1]}
            for row in cursor.fetchall()
        ]

        conn.close()
        return results

    def get_token_usage(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> Dict[str, int]:
        """
        Get total token usage.

        Returns:
            Dict with input_tokens and output_tokens
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        query = "SELECT SUM(tokens_input), SUM(tokens_output) FROM llm_costs WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        cursor.execute(query, params)
        input_tokens, output_tokens = cursor.fetchone()
        conn.close()

        return {
            "input_tokens": input_tokens or 0,
            "output_tokens": output_tokens or 0,
            "total_tokens": (input_tokens or 0) + (output_tokens or 0)
        }

    def set_budget(self, period: str, limit_usd: float, alert_threshold: float = 0.8):
        """
        Set budget for a period.

        Args:
            period: Period identifier (e.g., "2025-01", "monthly")
            limit_usd: Budget limit in USD
            alert_threshold: Alert when this fraction of budget is used (0.0-1.0)
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Deactivate existing budgets for this period
        cursor.execute("UPDATE budgets SET active = 0 WHERE period = ?", (period,))

        # Insert new budget
        cursor.execute("""
            INSERT INTO budgets (period, limit_usd, alert_threshold)
            VALUES (?, ?, ?)
        """, (period, limit_usd, alert_threshold))

        conn.commit()
        conn.close()

        self.logger.info(f"Set budget for {period}: ${limit_usd} (alert at {alert_threshold*100}%)")

    def check_budget_alert(self, period: str) -> Optional[Dict[str, Any]]:
        """
        Check if budget alert should trigger.

        Args:
            period: Period identifier

        Returns:
            Alert dict if threshold exceeded, None otherwise
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get active budget
        cursor.execute("""
            SELECT limit_usd, alert_threshold
            FROM budgets
            WHERE period = ? AND active = 1
            LIMIT 1
        """, (period,))

        result = cursor.fetchone()
        if not result:
            conn.close()
            return None

        limit_usd, alert_threshold = result

        # Get current spending for period
        # For monthly periods like "2025-01", match on YYYY-MM
        cursor.execute("""
            SELECT SUM(cost_usd)
            FROM llm_costs
            WHERE strftime('%Y-%m', timestamp, 'unixepoch') = ?
        """, (period,))

        current_cost = cursor.fetchone()[0] or 0.0
        conn.close()

        usage_percent = current_cost / limit_usd if limit_usd > 0 else 0

        if usage_percent >= alert_threshold:
            return {
                "period": period,
                "limit_usd": limit_usd,
                "current_cost": current_cost,
                "usage_percent": usage_percent,
                "alert_threshold": alert_threshold,
                "exceeded": usage_percent >= 1.0
            }

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall cost statistics"""
        now = time.time()
        day_ago = now - 86400
        week_ago = now - (7 * 86400)
        month_ago = now - (30 * 86400)

        return {
            "total_cost": self.get_total_cost(),
            "cost_24h": self.get_total_cost(start_time=day_ago),
            "cost_7d": self.get_total_cost(start_time=week_ago),
            "cost_30d": self.get_total_cost(start_time=month_ago),
            "by_service": self.get_cost_by_service(),
            "token_usage": self.get_token_usage(),
            "daily_costs": self.get_daily_costs(days=30)
        }


# Global cost tracker instance
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get global cost tracker instance"""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
