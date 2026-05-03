"""Unit tests for backend.services.yfinance_market (no network for invalid params)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_WEBUI = Path(__file__).resolve().parent.parent / "webui"
if str(_WEBUI) not in sys.path:
    sys.path.insert(0, str(_WEBUI))

pytest.importorskip("pandas")
from backend.services import yfinance_market as yfm  # noqa: E402


def test_fetch_rejects_bad_interval():
    hist, err = yfm.fetch_yfinance_hist_df("8058.T", "99x", "5d")
    assert hist is None
    assert err is not None
    assert err["status"] == 400
    assert "interval" in err["body"]["error"]


def test_fetch_rejects_bad_period():
    hist, err = yfm.fetch_yfinance_hist_df("8058.T", "1d", "invalid_period_xyz")
    assert hist is None
    assert err is not None
    assert err["status"] == 400
    assert "period" in err["body"]["error"]
