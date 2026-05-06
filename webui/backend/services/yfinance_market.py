"""yfinance market history fetch and OHLC conversion (no Flask)."""

from __future__ import annotations

import warnings
from typing import Any

import pandas as pd
import yfinance as yf

from model.kronos_amount import amount_log1p_typical_volume_series

# GET /api/market-history: query validation (aligned with frontend intervals/periods)
MARKET_HISTORY_ALLOWED_INTERVALS = frozenset(
    {
        "1m",
        "2m",
        "5m",
        "15m",
        "30m",
        "60m",
        "90m",
        "1h",
        "1d",
        "5d",
        "1wk",
        "1mo",
        "3mo",
    }
)
MARKET_HISTORY_ALLOWED_PERIODS = frozenset(
    {
        "1d",
        "5d",
        "30d",
        "60d",
        "1mo",
        "3mo",
        "6mo",
        "1y",
        "2y",
        "5y",
        "10y",
        "ytd",
        "max",
    }
)


def yfinance_exception_user_message(exc: BaseException) -> str:
    """Map yfinance/network exceptions to a short user-facing Japanese message."""
    if isinstance(exc, TimeoutError):
        return "市場データの取得がタイムアウトしました。時間をおいて再度お試しください。"
    if isinstance(exc, ConnectionError):
        return "ネットワーク接続エラーです。インターネット接続を確認してください。"
    detail = str(exc).strip()
    if len(detail) > 180:
        detail = detail[:177] + "..."
    if not detail:
        detail = type(exc).__name__
    return f"市場データの取得に失敗しました。（{detail}）"


def fetch_yfinance_hist_df(
    ticker: str,
    interval: str,
    period: str,
) -> tuple[pd.DataFrame | None, dict[str, Any] | None]:
    """
    Fetch OHLCV history via yfinance.

    On success: (hist, None). On failure: (None, err) where err is
    {'status': int, 'body': dict} compatible with jsonify(err['body']), err['status'].
    """
    warnings_list: list[str] = []

    if interval not in MARKET_HISTORY_ALLOWED_INTERVALS:
        allowed = ", ".join(sorted(MARKET_HISTORY_ALLOWED_INTERVALS))
        return None, {
            "status": 400,
            "body": {
                "success": False,
                "error": f"無効な interval です。次のいずれかを指定してください: {allowed}",
                "ticker": ticker,
                "interval": interval,
                "period": period,
                "warnings": warnings_list,
            },
        }

    if period not in MARKET_HISTORY_ALLOWED_PERIODS:
        allowed = ", ".join(sorted(MARKET_HISTORY_ALLOWED_PERIODS))
        return None, {
            "status": 400,
            "body": {
                "success": False,
                "error": f"無効な period です。次のいずれかを指定してください: {allowed}",
                "ticker": ticker,
                "interval": interval,
                "period": period,
                "warnings": warnings_list,
            },
        }

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period=period, interval=interval, auto_adjust=False)
        except Exception as e:
            return None, {
                "status": 502,
                "body": {
                    "success": False,
                    "error": yfinance_exception_user_message(e),
                    "ticker": ticker,
                    "interval": interval,
                    "period": period,
                    "warnings": warnings_list,
                },
            }

    if hist is None or hist.empty:
        hint_intraday = ""
        if interval.endswith("m") or interval.endswith("h"):
            hint_intraday = (
                " 分足・時間足は取得できる期間に上限があることが多く、長い period では空になりやすいです。"
                "期間を短くするか、日足（interval=1d）を試してください。"
            )
        return None, {
            "status": 422,
            "body": {
                "success": False,
                "error": (
                    "データが取得できませんでした（ティッカー・期間・間隔の組み合わせを確認してください）。"
                    + hint_intraday
                ),
                "ticker": ticker,
                "interval": interval,
                "period": period,
                "warnings": warnings_list,
            },
        }

    return hist, None


def historical_to_api_rows(hist: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert yfinance history DataFrame to API row dicts (timestamp, OHLC, volume, amount)."""
    vol_series = hist["Volume"] if "Volume" in hist.columns else pd.Series(0.0, index=hist.index)
    amt_series = amount_log1p_typical_volume_series(
        hist["Open"], hist["High"], hist["Low"], hist["Close"], vol_series
    )
    rows: list[dict[str, Any]] = []
    for j, (idx, row) in enumerate(hist.iterrows()):
        ts = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
        vol = float(row["Volume"]) if "Volume" in row and pd.notna(row["Volume"]) else None
        rows.append(
            {
                "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": vol,
                "amount": float(amt_series.iloc[j]),
            }
        )
    return rows


def hist_to_import_ohlcv_dataframe(hist: pd.DataFrame) -> pd.DataFrame:
    """Build timestamps + OHLC (+ volume) DataFrame for CSV import (timezone-naive UTC index)."""
    idx = pd.DatetimeIndex(pd.to_datetime(hist.index))
    if idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)

    out_df = pd.DataFrame(
        {
            "timestamps": idx,
            "open": pd.to_numeric(hist["Open"], errors="coerce"),
            "high": pd.to_numeric(hist["High"], errors="coerce"),
            "low": pd.to_numeric(hist["Low"], errors="coerce"),
            "close": pd.to_numeric(hist["Close"], errors="coerce"),
        }
    )
    if "Volume" in hist.columns:
        out_df["volume"] = pd.to_numeric(hist["Volume"], errors="coerce")
    else:
        out_df["volume"] = 0.0
    out_df["amount"] = amount_log1p_typical_volume_series(
        out_df["open"], out_df["high"], out_df["low"], out_df["close"], out_df["volume"]
    )
    return out_df.dropna(subset=["open", "high", "low", "close"])
