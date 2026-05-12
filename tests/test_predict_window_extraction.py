"""predict_window: 評価モードの末尾窓選択。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_WEBUI = Path(__file__).resolve().parent.parent / "webui"
if str(_WEBUI) not in sys.path:
    sys.path.insert(0, str(_WEBUI))

from backend.services.predict_window import select_predict_window  # noqa: E402


def _make_df(n: int = 20) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "timestamps": dates,
            "open": list(range(n)),
            "high": list(range(n)),
            "low": list(range(n)),
            "close": list(range(n)),
            "volume": [1.0] * n,
            "amount": [0.0] * n,
        }
    )


def test_no_filter_takes_last_lookback_plus_pred_len():
    df = _make_df(20)
    lookback, pred_len = 3, 2
    sel, err = select_predict_window(df, start_date=None, end_date=None, lookback=lookback, pred_len=pred_len)
    assert err is None
    assert sel is not None
    assert len(sel.window_df) == 5
    assert sel.historical_start_idx == 15
    assert sel.window_df["close"].iloc[0] == 15
    assert sel.window_df["close"].iloc[-1] == 19


def test_start_date_only_filters_then_tail():
    df = _make_df(20)
    sel, err = select_predict_window(
        df,
        start_date="2024-01-10",
        end_date=None,
        lookback=3,
        pred_len=2,
    )
    assert err is None
    assert sel is not None
    # Jan10 is index 9; last 5 of rows >= Jan10 are indices 15..19
    assert sel.historical_start_idx == 15


def test_end_date_only_filters_then_tail():
    df = _make_df(20)
    sel, err = select_predict_window(
        df,
        start_date=None,
        end_date="2024-01-15",
        lookback=3,
        pred_len=2,
    )
    assert err is None
    assert sel is not None
    # Jan1..Jan15 -> indices 0..14 (15 rows); last 5 start at 10
    assert sel.historical_start_idx == 10


def test_start_and_end_both():
    df = _make_df(20)
    sel, err = select_predict_window(
        df,
        start_date="2024-01-05",
        end_date="2024-01-12",
        lookback=3,
        pred_len=2,
    )
    assert err is None
    assert sel is not None
    # Jan5..Jan12 -> 8 rows (indices 4..11); need 5 -> only one window, start_row=4+8-5=7
    assert sel.historical_start_idx == 7
    assert len(sel.window_df) == 5


def test_insufficient_rows_returns_error():
    df = _make_df(4)
    sel, err = select_predict_window(df, start_date=None, end_date=None, lookback=3, pred_len=2)
    assert sel is None
    assert err is not None
    assert "不足" in err


def test_filtered_range_too_short():
    df = _make_df(20)
    sel, err = select_predict_window(
        df,
        start_date="2024-01-19",
        end_date="2024-01-20",
        lookback=3,
        pred_len=2,
    )
    assert sel is None
    assert err is not None
    assert "不足" in err


def test_start_after_end_returns_error():
    df = _make_df(10)
    sel, err = select_predict_window(
        df,
        start_date="2024-01-09",
        end_date="2024-01-02",
        lookback=2,
        pred_len=1,
    )
    assert sel is None
    assert err is not None


def test_predict_body_date_order_validation():
    from pydantic import ValidationError

    from backend.schemas.data_requests import PredictBody

    with pytest.raises(ValidationError):
        PredictBody(
            file_path="data/x.csv",
            lookback=2,
            pred_len=1,
            start_date="2024-12-31",
            end_date="2024-01-01",
        )
