"""Statistics and data export utilities — Python 3.14."""

from __future__ import annotations

import csv
import io
import json
from typing import Any


def export_to_csv(data: list[dict[str, Any]]) -> str:
    """Convert a list of dictionaries to a CSV string."""
    if not data:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def export_to_json(data: list[dict[str, Any]]) -> str:
    """Convert a list of dictionaries to a formatted JSON string."""
    return json.dumps(data, indent=2, default=str)


def compute_basic_stats(prices: list[float]) -> dict[str, float]:
    """Compute basic descriptive statistics for a list of prices."""
    import numpy as np

    if not prices:
        return {}

    arr = np.array(prices)
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "median": float(np.median(arr)),
    }
