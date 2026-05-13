"""yfinance の start/end 取得時の期間制限（GET market-history / POST import-market 共通）。"""

from __future__ import annotations

import pandas as pd

# (max_lookback_days, max_range_days): 開始日は現在から max_lookback 日以内、レンジ幅は max_range 日以内
_INTRADAY_RULES: dict[str, tuple[int, int]] = {
    "1m": (30, 7),
    "2m": (60, 60),
    "5m": (60, 60),
    "15m": (60, 60),
    "30m": (60, 60),
    "90m": (60, 60),
    "60m": (730, 730),
    "1h": (730, 730),
}

_UNLIMITED_INTERVALS = frozenset({"1d", "5d", "1wk", "1mo", "3mo"})

# プラン・ドキュメント用の公開ルール表（validate と同一の数値）
INTERVAL_RULES: dict[str, dict[str, int]] = {
    k: {"max_lookback_days": v[0], "max_range_days": v[1]} for k, v in _INTRADAY_RULES.items()
}


def _parse_boundary(s: str) -> pd.Timestamp:
    ts = pd.to_datetime(s, errors="coerce")
    if pd.isna(ts):
        raise ValueError(f"日付を解釈できません: {s!r}")
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return pd.Timestamp(ts).normalize()


def validate_yfinance_range(
    interval: str,
    start: str,
    end: str,
    *,
    now: pd.Timestamp | None = None,
) -> tuple[bool, str | None]:
    """
    interval と [start, end]（日付文字列）が yfinance の実務的制限内か検証する。

    Returns:
        (True, None) または (False, 日本語エラーメッセージ)
    """
    ref = now if now is not None else pd.Timestamp.utcnow().normalize()
    if ref.tzinfo is not None:
        ref = ref.tz_convert("UTC").tz_localize(None).normalize()

    if interval in _UNLIMITED_INTERVALS:
        try:
            start_ts = _parse_boundary(start)
            end_ts = _parse_boundary(end)
        except ValueError as e:
            return False, str(e)
        if start_ts > end_ts:
            return False, "start は end 以下である必要があります"
        if end_ts > ref:
            return False, "end は今日以前の日付を指定してください"
        return True, None

    rule = _INTRADAY_RULES.get(interval)
    if rule is None:
        return False, f"interval {interval!r} には start/end レンジ制限が未定義です（サポート外の可能性があります）"

    max_lookback_days, max_range_days = rule

    try:
        start_ts = _parse_boundary(start)
        end_ts = _parse_boundary(end)
    except ValueError as e:
        return False, str(e)

    if start_ts > end_ts:
        return False, "start は end 以下である必要があります"

    if end_ts > ref:
        return False, "end は今日以前の日付を指定してください"

    span_days = int((end_ts - start_ts).days)
    if span_days > max_range_days:
        return (
            False,
            f"この interval（{interval}）では取得レンジは最大 {max_range_days} 日までです（現在: {span_days} 日）。"
            "期間を短くするか、日足（1d）を選んでください。",
        )

    age_days = int((ref - start_ts).days)
    if age_days > max_lookback_days:
        return (
            False,
            f"この interval（{interval}）では開始日は直近 {max_lookback_days} 日以内である必要があります（開始が約 {age_days} 日前です）。",
        )

    return True, None


def range_rule_hint(interval: str) -> str:
    """UI 用の短い説明文。"""
    if interval in _UNLIMITED_INTERVALS:
        return f"interval={interval}: 日付レンジに実務上の厳しい上限はありません（yfinance の提供範囲内）。"
    rule = _INTRADAY_RULES.get(interval)
    if not rule:
        return f"interval={interval}: 制限情報なし。"
    lb, rg = rule
    return f"interval={interval}: 開始は直近 {lb} 日以内、レンジ幅は最大 {rg} 日まで（1 リクエスト）。"