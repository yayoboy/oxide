"""
Cost Tracking API Endpoints

Provides REST API for LLM cost analytics:
- Cost statistics and breakdowns
- Budget management
- Cost reports and exports
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import csv
import io
import time

from ....analytics import get_cost_tracker
from ....utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/costs", tags=["costs"])


# Request/Response models
class BudgetRequest(BaseModel):
    """Request to set a budget"""
    period: str  # e.g., "2025-01" for January 2025
    limit_usd: float
    alert_threshold: float = 0.8  # Alert at 80% by default


class CostStats(BaseModel):
    """Cost statistics response"""
    total_cost: float
    cost_24h: float
    cost_7d: float
    cost_30d: float
    by_service: Dict[str, float]
    token_usage: Dict[str, int]
    daily_costs: List[Dict[str, Any]]


class BudgetAlert(BaseModel):
    """Budget alert response"""
    period: str
    limit_usd: float
    current_cost: float
    usage_percent: float
    alert_threshold: float
    exceeded: bool


# API Endpoints

@router.get("/stats", response_model=CostStats)
async def get_cost_stats():
    """
    Get cost statistics.

    Returns comprehensive cost analytics including:
    - Total cost (all-time, 24h, 7d, 30d)
    - Cost breakdown by service
    - Token usage statistics
    - Daily cost history
    """
    try:
        tracker = get_cost_tracker()
        stats = tracker.get_statistics()

        return CostStats(**stats)

    except Exception as e:
        logger.error(f"Failed to get cost stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/total")
async def get_total_cost(
    start_time: Optional[float] = Query(None, description="Start timestamp (Unix)"),
    end_time: Optional[float] = Query(None, description="End timestamp (Unix)"),
    service: Optional[str] = Query(None, description="Filter by service")
):
    """
    Get total cost for a time period.

    Can filter by time range and/or service.
    """
    try:
        tracker = get_cost_tracker()
        total = tracker.get_total_cost(
            start_time=start_time,
            end_time=end_time,
            service=service
        )

        return {
            "total_cost_usd": total,
            "start_time": start_time,
            "end_time": end_time,
            "service": service
        }

    except Exception as e:
        logger.error(f"Failed to get total cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-service")
async def get_cost_by_service(
    start_time: Optional[float] = Query(None, description="Start timestamp (Unix)"),
    end_time: Optional[float] = Query(None, description="End timestamp (Unix)")
):
    """
    Get cost breakdown by service.

    Returns a dict mapping service names to their total cost.
    """
    try:
        tracker = get_cost_tracker()
        breakdown = tracker.get_cost_by_service(
            start_time=start_time,
            end_time=end_time
        )

        return {
            "by_service": breakdown,
            "start_time": start_time,
            "end_time": end_time
        }

    except Exception as e:
        logger.error(f"Failed to get cost by service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily")
async def get_daily_costs(
    days: int = Query(30, ge=1, le=365, description="Number of days to include")
):
    """
    Get daily cost breakdown.

    Returns cost per day for the last N days.
    """
    try:
        tracker = get_cost_tracker()
        daily = tracker.get_daily_costs(days=days)

        return {
            "daily_costs": daily,
            "days": days
        }

    except Exception as e:
        logger.error(f"Failed to get daily costs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tokens")
async def get_token_usage(
    start_time: Optional[float] = Query(None, description="Start timestamp (Unix)"),
    end_time: Optional[float] = Query(None, description="End timestamp (Unix)")
):
    """
    Get token usage statistics.

    Returns total input/output/total tokens used.
    """
    try:
        tracker = get_cost_tracker()
        usage = tracker.get_token_usage(
            start_time=start_time,
            end_time=end_time
        )

        return usage

    except Exception as e:
        logger.error(f"Failed to get token usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/budget", status_code=201)
async def set_budget(request: BudgetRequest):
    """
    Set budget for a period.

    Creates a budget limit with optional alert threshold.
    Alert triggers when spending reaches the threshold percentage.
    """
    try:
        tracker = get_cost_tracker()
        tracker.set_budget(
            period=request.period,
            limit_usd=request.limit_usd,
            alert_threshold=request.alert_threshold
        )

        logger.info(f"Budget set for {request.period}: ${request.limit_usd}")

        return {
            "message": f"Budget set for {request.period}",
            "period": request.period,
            "limit_usd": request.limit_usd,
            "alert_threshold": request.alert_threshold
        }

    except Exception as e:
        logger.error(f"Failed to set budget: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/budget/{period}/alert")
async def check_budget_alert(period: str):
    """
    Check budget alert for a period.

    Returns alert information if budget threshold is exceeded.
    Returns None if no alert or budget not set.
    """
    try:
        tracker = get_cost_tracker()
        alert = tracker.check_budget_alert(period)

        if alert:
            return BudgetAlert(**alert)
        else:
            return {
                "alert": False,
                "period": period,
                "message": "No budget alert"
            }

    except Exception as e:
        logger.error(f"Failed to check budget alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/csv")
async def export_costs_csv(
    start_time: Optional[float] = Query(None, description="Start timestamp (Unix)"),
    end_time: Optional[float] = Query(None, description="End timestamp (Unix)")
):
    """
    Export cost data as CSV.

    Downloads a CSV file with all cost records in the time range.
    """
    try:
        tracker = get_cost_tracker()

        # Get all cost records (via SQL query)
        import sqlite3
        conn = sqlite3.connect(str(tracker.db_path))
        cursor = conn.cursor()

        query = "SELECT task_id, service, tokens_input, tokens_output, cost_usd, timestamp FROM llm_costs WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["task_id", "service", "tokens_input", "tokens_output", "cost_usd", "timestamp", "date"])

        # Data
        for row in rows:
            task_id, service, tokens_in, tokens_out, cost, timestamp = row
            from datetime import datetime
            date_str = datetime.fromtimestamp(timestamp).isoformat()
            writer.writerow([task_id, service, tokens_in, tokens_out, f"{cost:.6f}", timestamp, date_str])

        # Prepare response
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=oxide_costs_{int(time.time())}.csv"
            }
        )

    except Exception as e:
        logger.error(f"Failed to export costs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pricing")
async def get_pricing():
    """
    Get current pricing configuration.

    Returns pricing per service (cost per input/output token).
    """
    try:
        tracker = get_cost_tracker()

        pricing_list = []
        for service, pricing in tracker.pricing.items():
            pricing_list.append({
                "service": pricing.service,
                "cost_per_input_token": pricing.cost_per_input_token,
                "cost_per_output_token": pricing.cost_per_output_token,
                "currency": pricing.currency
            })

        return {"pricing": pricing_list}

    except Exception as e:
        logger.error(f"Failed to get pricing: {e}")
        raise HTTPException(status_code=500, detail=str(e))
