"""model.kronos_amount と yfinance 取り込み DataFrame の amount 列。"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module", autouse=True)
def _paths():
    for p in (str(REPO), str(REPO / "webui")):
        if p not in sys.path:
            sys.path.insert(0, p)


def test_amount_log1p_matches_formula():
    from model.kronos_amount import amount_log1p_typical_volume_series

    o, h, l, c, v = 100.0, 102.0, 98.0, 101.0, 1_000_000.0
    typical = (h + l + c) / 3.0
    expected = float(np.log1p(typical * v))
    s = amount_log1p_typical_volume_series([o], [h], [l], [c], [v])
    assert abs(s.iloc[0] - expected) < 1e-6


def test_amount_zero_volume_is_log1p_zero():
    from model.kronos_amount import amount_log1p_typical_volume_series

    s = amount_log1p_typical_volume_series([1.0], [2.0], [3.0], [4.0], [0.0])
    assert abs(s.iloc[0]) < 1e-9


def test_hist_to_import_includes_amount():
    from backend.services.yfinance_market import hist_to_import_ohlcv_dataframe

    hist = pd.DataFrame(
        {
            "Open": [10.0, 11.0],
            "High": [12.0, 12.0],
            "Low": [9.0, 10.0],
            "Close": [11.0, 11.5],
            "Volume": [100.0, 200.0],
        },
        index=pd.DatetimeIndex(["2024-01-01 00:00:00", "2024-01-02 00:00:00"], tz="UTC"),
    )
    out = hist_to_import_ohlcv_dataframe(hist)
    assert "amount" in out.columns
    assert len(out) == 2
    assert (np.isfinite(out["amount"].to_numpy())).all()
    assert (out["amount"] >= 0).all()
