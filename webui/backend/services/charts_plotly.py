"""Plotly による予測チャート生成。"""

from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import plotly.utils
from plotly.subplots import make_subplots


def figure_to_plotly_dict(fig):
    """Plotly Figure を JSON 互換の dict に変換する。"""
    return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))


def _candlestick_trace(x, open_, high, low, close, name, inc_color, dec_color):
    return go.Candlestick(
        x=x,
        open=open_,
        high=high,
        low=low,
        close=close,
        name=name,
        increasing_line_color=inc_color,
        decreasing_line_color=dec_color,
        increasing_line_width=1.5,
        decreasing_line_width=1.5,
        whiskerwidth=0.72,
    )


def create_prediction_chart(df, pred_df, lookback, pred_len, actual_df=None, historical_start_idx=0):
    """予測結果のチャート用 Figure を生成する（縦分割サブプロット）。"""
    if historical_start_idx + lookback + pred_len <= len(df):
        historical_df = df.iloc[historical_start_idx : historical_start_idx + lookback]
    else:
        available_lookback = min(lookback, len(df) - historical_start_idx)
        historical_df = df.iloc[historical_start_idx : historical_start_idx + available_lookback]

    has_pred = pred_df is not None and len(pred_df) > 0
    has_actual = actual_df is not None and len(actual_df) > 0

    pred_timestamps = None
    if has_pred:
        if "timestamps" in df.columns and len(historical_df) > 0:
            last_timestamp = historical_df["timestamps"].iloc[-1]
            time_diff = (
                df["timestamps"].iloc[1] - df["timestamps"].iloc[0]
                if len(df) > 1
                else pd.Timedelta(hours=1)
            )
            pred_timestamps = pd.date_range(
                start=last_timestamp + time_diff,
                periods=len(pred_df),
                freq=time_diff,
            )
        else:
            pred_timestamps = range(len(historical_df), len(historical_df) + len(pred_df))

    actual_timestamps = None
    if has_actual:
        if "timestamps" in df.columns:
            if pred_timestamps is not None:
                actual_timestamps = pred_timestamps
            elif len(historical_df) > 0:
                last_timestamp = historical_df["timestamps"].iloc[-1]
                time_diff = (
                    df["timestamps"].iloc[1] - df["timestamps"].iloc[0]
                    if len(df) > 1
                    else pd.Timedelta(hours=1)
                )
                actual_timestamps = pd.date_range(
                    start=last_timestamp + time_diff,
                    periods=len(actual_df),
                    freq=time_diff,
                )
            else:
                actual_timestamps = range(len(historical_df), len(historical_df) + len(actual_df))
        else:
            actual_timestamps = range(len(historical_df), len(historical_df) + len(actual_df))

    nrows = 1 + (1 if has_pred else 0) + (1 if has_actual else 0)
    if nrows == 1:
        row_heights = [1.0]
        layout_height = 600
    elif nrows == 2:
        row_heights = [0.55, 0.45]
        layout_height = 750
    else:
        row_heights = [0.48, 0.28, 0.24]
        layout_height = 920

    fig = make_subplots(
        rows=nrows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=row_heights,
    )

    row_hist = 1
    x_hist = historical_df["timestamps"] if "timestamps" in historical_df.columns else historical_df.index
    fig.add_trace(
        _candlestick_trace(
            x_hist,
            historical_df["open"],
            historical_df["high"],
            historical_df["low"],
            historical_df["close"],
            "実データ（履歴 400 本）",
            "#26A69A",
            "#EF5350",
        ),
        row=row_hist,
        col=1,
    )
    fig.update_yaxes(title_text="履歴（価格）", row=row_hist, col=1)

    current_row = row_hist
    if has_pred:
        current_row += 1
        fig.add_trace(
            _candlestick_trace(
                pred_timestamps,
                pred_df["open"],
                pred_df["high"],
                pred_df["low"],
                pred_df["close"],
                "予測データ（120 本）",
                "#66BB6A",
                "#FF7043",
            ),
            row=current_row,
            col=1,
        )
        fig.update_yaxes(title_text="予測（価格）", row=current_row, col=1)

    if has_actual:
        current_row += 1
        fig.add_trace(
            _candlestick_trace(
                actual_timestamps,
                actual_df["open"],
                actual_df["high"],
                actual_df["low"],
                actual_df["close"],
                "検証用 実データ（120 本）",
                "#FF9800",
                "#F44336",
            ),
            row=current_row,
            col=1,
        )
        fig.update_yaxes(title_text="検証・実データ（価格）", row=current_row, col=1)

    fig.update_layout(
        title="Kronos 予測結果（履歴 400 本 + 予測 120 本 vs 実データ 120 本）",
        template="plotly_white",
        height=layout_height,
        showlegend=True,
        hovermode="x unified",
    )
    fig.update_xaxes(title_text="時刻", row=nrows, col=1)

    if "timestamps" in historical_df.columns:
        all_timestamps = []
        if len(historical_df) > 0:
            all_timestamps.extend(historical_df["timestamps"])
        if pred_timestamps is not None:
            all_timestamps.extend(pred_timestamps)
        if actual_timestamps is not None:
            all_timestamps.extend(actual_timestamps)
        if all_timestamps:
            all_timestamps = sorted(all_timestamps)
            fig.update_xaxes(
                range=[all_timestamps[0], all_timestamps[-1]],
                rangeslider_visible=False,
                type="date",
            )

    return figure_to_plotly_dict(fig)
