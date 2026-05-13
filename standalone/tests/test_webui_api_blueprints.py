"""Smoke tests: Flask blueprints register the same /api/* routes as before phase 2."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_WEBUI = Path(__file__).resolve().parent.parent / "webui"
if str(_WEBUI) not in sys.path:
    sys.path.insert(0, str(_WEBUI))

pytest.importorskip("pandas")
pytest.importorskip("flask")


def _client():
    from backend.app_factory import create_app

    return create_app().test_client()


def test_api_model_status_get():
    rv = _client().get("/api/model-status")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "available" in data and "loaded" in data


def test_api_available_models_get():
    rv = _client().get("/api/available-models")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "models" in data and "model_available" in data


def test_api_tickers_get():
    rv = _client().get("/api/tickers")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data.get("success") is True
    assert "tickers" in data


def test_api_load_data_empty_json_returns_400():
    rv = _client().post("/api/load-data", json={})
    assert rv.status_code == 400
    data = rv.get_json()
    assert "error" in data
