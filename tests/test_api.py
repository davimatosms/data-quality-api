from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
client = TestClient(app)


def test_source_check_and_status():
    source = client.post(
        "/sources",
        json={"name": "customers", "expected_frequency_minutes": 60, "quality_rules": ["no_nulls"]},
    )
    assert source.status_code == 201
    source_id = source.json()["id"]
    check = client.post(
        f"/sources/{source_id}/checks",
        json={
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "status": "PASSING",
            "rule_results": [{"rule_name": "no_nulls", "passed": True}],
        },
    )
    assert check.status_code == 201
    status = client.get(f"/sources/{source_id}/status")
    assert status.status_code == 200
    assert status.json()["freshness"] == "FRESH"
    assert status.json()["quality"] == "PASSING"


def test_source_crud_and_overview():
    source = client.post(
        "/sources",
        json={"name": "orders", "expected_frequency_minutes": 30},
    )
    source_id = source.json()["id"]
    updated = client.put(
        f"/sources/{source_id}",
        json={"name": "orders-v2", "expected_frequency_minutes": 60},
    )
    assert updated.status_code == 200
    overview = client.get("/sources")
    item = next(item for item in overview.json() if item["id"] == source_id)
    assert item["name"] == "orders-v2"
    assert item["freshness"] == "UNKNOWN"
    assert item["quality"] == "UNKNOWN"
    assert client.delete(f"/sources/{source_id}").status_code == 204


def test_health_checks_database():
    response = client.get("/health")
    assert response.json() == {"status": "ok", "database": "ok"}
