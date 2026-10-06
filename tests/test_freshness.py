from datetime import datetime, timedelta, timezone

from app.models import Source
from app.services.freshness import freshness_status


def source():
    return Source(expected_frequency_minutes=60, freshness_tolerance=1.5)


def test_unknown_without_check():
    assert freshness_status(source(), None) == "UNKNOWN"


def test_fresh_within_tolerance():
    now = datetime.now(timezone.utc)
    assert freshness_status(source(), now - timedelta(minutes=89), now) == "FRESH"


def test_stale_after_tolerance():
    now = datetime.now(timezone.utc)
    assert freshness_status(source(), now - timedelta(minutes=91), now) == "STALE"
