"""Regression tests for backend hardening (SSRF guard, input validation, key lookup)."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.api_key_service import authenticate, get_sandbox_key

client = TestClient(app)


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "ftp://example.com/x",
    "http://127.0.0.1:9/hook",
    "http://169.254.169.254/latest/meta-data",
])
def test_webhook_rejects_unsafe_urls(url):
    r = client.post("/api/v1/webhooks", json={"url": url, "events": ["ohi.alert"], "label": "t"})
    assert r.status_code == 400


def test_webhook_secret_hint_is_masked():
    from backend.routers.webhooks import _wh_dict
    from backend.services.webhook_service import WebhookRegistration
    wh = WebhookRegistration("id", "https://example.com", [], "supersecret", "l")
    assert "super" not in _wh_dict(wh)["secret_hint"]


def test_v1_impact_limit_bounds():
    h = {"Authorization": f"Bearer {get_sandbox_key()}"}
    assert client.get("/api/v1/impact?limit=-1", headers=h).status_code == 422
    assert client.get("/api/v1/impact?limit=501", headers=h).status_code == 422
    assert client.get("/api/v1/impact?limit=2", headers=h).json()["count"] == 2


def test_authenticate_rejects_empty_and_unknown():
    assert authenticate("") is None
    assert authenticate("eibo_demo_nope") is None
    assert authenticate(get_sandbox_key()) is not None


@pytest.mark.parametrize("path", ["pulse", "ohi", "dashboard", "v1/dashboard"])
def test_invalid_scenario_is_rejected_not_500(path):
    h = {"Authorization": f"Bearer {get_sandbox_key()}"}
    assert client.get(f"/api/{path}?scenario=Z", headers=h).status_code == 422


def test_post_bodies_validate_scenario():
    assert client.post("/api/ohi/preview", json={"scenario": "Z"}).status_code == 422
    assert client.post("/api/ld/pareto", json={"size": "huge"}).status_code == 422


def test_mobility_endpoint_works():
    """Regression: dict(groupby) raised TypeError and the endpoint returned 500."""
    assert client.get("/api/mobility?scenario=A&size=small").status_code == 200


def test_numeric_sanitizers_handle_nan_and_inf():
    from utils.sanitization import (
        sanitize_budget_value,
        sanitize_percentage,
        sanitize_positive_int,
    )
    assert sanitize_budget_value("nan") == 0.0
    assert sanitize_percentage(float("inf")) == 0.0
    assert sanitize_positive_int("inf") == 0


def test_ld_attrition_reduction_is_a_bounded_average():
    """Regression: summing per-allocation reductions showed '1049%' in the UI."""
    r = client.post("/api/ld/optimize", json={"budget": 567000, "max_per_employee": 2})
    assert r.status_code == 200
    red = r.json()["expected_attrition_reduction"]
    assert 0.0 <= red <= 1.0
