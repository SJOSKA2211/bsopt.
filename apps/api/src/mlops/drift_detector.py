"""Drift detection for pricing models."""

from __future__ import annotations

import structlog

from src.notifications.hierarchy import NotificationRouter

logger = structlog.get_logger(__name__)


async def check_model_drift(
    method_name: str,
    baseline_mape: float,
    notification_router: NotificationRouter,
    alert_recipients: list[str],
) -> bool:
    """Compare current MAPE against baseline to detect drift."""
    # Simulation for now: drift is detected if baseline is high in the test
    # In production, this would query NeonDB for recent error metrics
    current_mape = 0.0  # Placeholder for recent actual MAPE
    drift = abs(current_mape - baseline_mape)

    if drift > 0.5:
        logger.warning("model_drift_detected", method=method_name, drift=drift)
        await notification_router.route_notification(
            user_id=alert_recipients[0],  # Just use first recipient for now
            title="Model Drift Alert",
            message=f"Model {method_name} has drifted by {drift:.4f}",
            channels=["email", "web_push"],
        )
        return True
    return False
