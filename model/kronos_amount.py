"""Kronos 6 次元入力の amount 列: log1p(TypicalPrice × volume)。yfinance 等で代金が無い場合の共通導出。"""

from __future__ import annotations

import numpy as np
import pandas as pd


def amount_log1p_typical_volume_series(
    open_,
    high,
    low,
    close,
    volume,
) -> pd.Series:
    """
    Typical Price = (high + low + close) / 3、raw = max(typical * volume, 0)、amount = log1p(raw)。
    volume 欠損は 0。raw が NaN の行は 0 として log1p。
    """
    frame = pd.DataFrame(
        {
            "open": pd.to_numeric(open_, errors="coerce"),
            "high": pd.to_numeric(high, errors="coerce"),
            "low": pd.to_numeric(low, errors="coerce"),
            "close": pd.to_numeric(close, errors="coerce"),
            "volume": pd.to_numeric(volume, errors="coerce"),
        }
    )
    v = frame["volume"].fillna(0.0).clip(lower=0)
    typical = (frame["high"] + frame["low"] + frame["close"]) / 3.0
    raw = (typical * v).fillna(0.0).clip(lower=0)
    out = np.log1p(raw.to_numpy(dtype=np.float64))
    return pd.Series(out, index=frame.index, dtype="float64")
