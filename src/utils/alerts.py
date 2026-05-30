from __future__ import annotations

from typing import Iterable


ALERT_THRESHOLD = 150


def has_hazardous_aqi(values: Iterable[float], threshold: int = ALERT_THRESHOLD) -> bool:
    return any(v is not None and v >= threshold for v in values)
