"""POST /api/predict 用: start/end で範囲を絞り、末尾 lookback+pred_len 本の窓を選ぶ。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PredictWindowSelection:
    """評価モード: 先頭 lookback 本を入力、末尾 pred_len 本を実測比較用に使うための連続窓。"""

    window_df: pd.DataFrame
    historical_start_idx: int


def select_predict_window(
    df: pd.DataFrame,
    *,
    start_date: str | None,
    end_date: str | None,
    lookback: int,
    pred_len: int,
) -> tuple[PredictWindowSelection | None, str | None]:
    """
    timestamps でフィルタした範囲の末尾から ``lookback + pred_len`` 本を取る。

    Returns:
        (PredictWindowSelection, None) または (None, error_message)
    """
    if "timestamps" not in df.columns:
        return None, "timestamps 列がありません"

    needed = lookback + pred_len
    if len(df) < needed:
        return None, f"データが不足しています（必要 {needed} 本、現在 {len(df)} 本）"

    ts = df["timestamps"]
    mask = np.ones(len(df), dtype=bool)

    if start_date:
        try:
            start_dt = pd.to_datetime(start_date)
        except Exception as e:
            return None, f"start_date を解釈できませんでした: {e}"
        if pd.isna(start_dt):
            return None, "start_date が無効です"
        mask &= ts >= start_dt

    if end_date:
        try:
            end_dt = pd.to_datetime(end_date)
        except Exception as e:
            return None, f"end_date を解釈できませんでした: {e}"
        if pd.isna(end_dt):
            return None, "end_date が無効です"
        mask &= ts <= end_dt

    if start_date and end_date:
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        if start_dt > end_dt:
            return None, "start_date は end_date 以下である必要があります"

    pos = np.flatnonzero(mask)
    if pos.size < needed:
        return None, f"指定範囲のデータが不足しています（必要 {needed} 本、現在 {pos.size} 本）"

    start_row = int(pos[-needed])
    window_df = df.iloc[start_row : start_row + needed].copy()
    historical_start_idx = start_row

    if len(window_df) != needed:
        return None, "内部エラー: 窓の行数が一致しません"

    return PredictWindowSelection(window_df=window_df, historical_start_idx=historical_start_idx), None
