"""
tests/test_health.py
-----------------------
Pruebas unitarias para services/health_service.py y el simulador de
datos biométricos, incluyendo el aislamiento de datos entre usuarios.
"""

import pytest
from services import health_service
from services.simulator_service import generate_random_metric
from utils.error_handlers import NotFoundError


def test_get_current_metric_raises_not_found_when_empty(fake_db):
    with pytest.raises(NotFoundError):
        health_service.get_current_metric("user-1")


def test_generate_random_metric_persists_and_is_isolated_per_user(fake_db):
    generate_random_metric("user-1")
    generate_random_metric("user-2")
    generate_random_metric("user-1")

    user1_docs = list(fake_db.health_metrics.find({"user_id": "user-1"}))
    user2_docs = list(fake_db.health_metrics.find({"user_id": "user-2"}))

    assert len(user1_docs) == 2
    assert len(user2_docs) == 1
    assert all(doc["user_id"] == "user-1" for doc in user1_docs)


def test_get_current_metric_returns_latest(fake_db):
    generate_random_metric("user-1")
    latest = generate_random_metric("user-1")

    current = health_service.get_current_metric("user-1")
    assert current["id"] == latest["id"]


def test_get_history_pagination(fake_db):
    for _ in range(5):
        generate_random_metric("user-1")

    page_1 = health_service.get_history("user-1", page=1, limit=2)
    assert len(page_1["items"]) == 2
    assert page_1["total"] == 5
    assert page_1["total_pages"] == 3


def test_get_statistics_empty_returns_zero_defaults(fake_db):
    stats = health_service.get_statistics("user-without-data")
    assert stats["sample_count"] == 0
    assert stats["total_steps"] == 0


def test_get_statistics_aggregates_correctly(fake_db):
    for _ in range(3):
        generate_random_metric("user-1")

    stats = health_service.get_statistics("user-1")
    assert stats["sample_count"] == 3
    assert stats["avg_heart_rate"] is not None
