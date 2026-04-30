"""Model drift detection using 7-day rolling MAPE comparison."""

from __future__ import annotations

import structlog

from src.database.repository import query_recent_mape
from src.notifications.hierarchy import Notification, NotificationRouter

logger = structlog.get_logger(__name__)
DRIFT_THRESHOLD_PCT: float = 0.5


async def check_model_drift(
    method_type: str,
    baseline_mape: float,
    router: NotificationRouter,
    user_ids: list[str],
) -> bool:
    """Alert via notification hierarchy if drift > DRIFT_THRESHOLD_PCT."""
    current_mape = await query_recent_mape(method_type=method_type, days=7)
    drift = abs(current_mape - baseline_mape)
    if drift > DRIFT_THRESHOLD_PCT:
        for uid in user_ids:
            await router.dispatch(
                Notification(
                    user_id=uid,
                    title=f"Drift detected: {method_type}",
                    body=(
                        f"MAPE rose from {baseline_mape:.4f}% to {current_mape:.4f}%. "
                        f"Drift: {drift:.4f}%. Trigger retraining via /dashboard/mlops."
                    ),
                    severity="warning",
                    action_url="/dashboard/mlops",
                )
            )
        return True
    return False
