"""backend.services.yfinance_limits の境界テスト（ネットワークなし）。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

_WEBUI = Path(__file__).resolve().parent.parent / "webui"
if str(_WEBUI) not in sys.path:
    sys.path.insert(0, str(_WEBUI))

from backend.schemas.data_requests import ImportMarketBody  # noqa: E402
from backend.services.yfinance_limits import INTERVAL_RULES, validate_yfinance_range  # noqa: E402


def test_interval_rules_table_has_expected_keys():
    assert INTERVAL_RULES["1m"]["max_lookback_days"] == 30
    assert INTERVAL_RULES["1m"]["max_range_days"] == 7
    assert INTERVAL_RULES["5m"]["max_range_days"] == 60


@pytest.mark.parametrize(
    ("start", "end", "expect_ok"),
    [
        ("2026-04-24", "2026-05-01", True),  # ちょうど 7 日幅
        ("2026-04-23", "2026-05-01", False),  # 8 日幅 → NG
    ],
)
def test_1m_max_range_days_boundary(start, end, expect_ok):
    now = pd.Timestamp("2026-05-01")
    ok, msg = validate_yfinance_range("1m", start, end, now=now)
    assert ok is expect_ok
    if not expect_ok:
        assert msg and "7" in msg


@pytest.mark.parametrize(
    ("start", "end", "expect_ok"),
    [
        # 幅は 7 日以内に抑え、開始が「ちょうど 30 日前」なら OK（5/1 基準で 4/1 開始は 30 日遡り）
        ("2026-04-01", "2026-04-07", True),
        # 幅は短いが開始が 31 日前 → 遡及 NG
        ("2026-03-31", "2026-04-06", False),
    ],
)
def test_1m_max_lookback_days_boundary(start, end, expect_ok):
    now = pd.Timestamp("2026-05-01")
    ok, msg = validate_yfinance_range("1m", start, end, now=now)
    assert ok is expect_ok
    if not expect_ok:
        assert msg and "30" in msg


def test_5m_span_60_ok_61_ng():
    now = pd.Timestamp("2026-05-01")
    ok60, _ = validate_yfinance_range("5m", "2026-03-02", "2026-05-01", now=now)
    assert ok60
    ok61, msg = validate_yfinance_range("5m", "2026-03-01", "2026-05-01", now=now)
    assert not ok61
    assert msg and "60" in msg


def test_1d_unlimited_span_ok():
    now = pd.Timestamp("2026-05-01")
    ok, msg = validate_yfinance_range("1d", "2010-01-01", "2020-01-01", now=now)
    assert ok and msg is None


def test_start_after_end_rejected():
    now = pd.Timestamp("2026-05-01")
    ok, msg = validate_yfinance_range("5m", "2026-04-10", "2026-04-01", now=now)
    assert not ok
    assert msg and "end" in msg


def test_unknown_interval_rejected():
    now = pd.Timestamp("2026-05-01")
    ok, msg = validate_yfinance_range("bogus", "2026-04-01", "2026-04-02", now=now)
    assert not ok
    assert msg and "bogus" in msg


def test_end_in_future_rejected_even_for_1d():
    now = pd.Timestamp("2026-05-01")
    ok, msg = validate_yfinance_range("1d", "2026-04-01", "2026-06-01", now=now)
    assert not ok
    assert msg and "今日" in msg


def test_import_market_body_range_requires_both_dates():
    with pytest.raises(ValidationError, match="start と end"):
        ImportMarketBody(ticker_id="8058.T", start="2026-01-01")


def test_import_market_body_start_after_end_raises():
    with pytest.raises(ValidationError, match="end"):
        ImportMarketBody(ticker_id="8058.T", start="2026-02-01", end="2026-01-01")
