from datetime import datetime, timezone

from app.models import Source


def freshness_status(
    source: Source, latest_checked_at: datetime | None, now: datetime | None = None
) -> str:
    if latest_checked_at is None:
        return "UNKNOWN"
    now = now or datetime.now(timezone.utc)
    checked_at = (
        latest_checked_at.replace(tzinfo=timezone.utc)
        if latest_checked_at.tzinfo is None
        else latest_checked_at
    )
    age_minutes = (now - checked_at).total_seconds() / 60
    threshold = source.expected_frequency_minutes * source.freshness_tolerance
    return "STALE" if age_minutes > threshold else "FRESH"
