"""CSV / Feather の読み込みと学習用タイムスタンプ集計（Flask 非依存）。"""

from __future__ import annotations

import pandas as pd


def load_data_file(file_path):
    """データファイルを読み込む。戻り値: (df, None) または (None, error_message)。"""
    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.endswith(".feather"):
            df = pd.read_feather(file_path)
        else:
            return None, "未対応のファイル形式です"

        required_cols = ["open", "high", "low", "close"]
        if not all(col in df.columns for col in required_cols):
            return None, f"必須列が不足しています: {required_cols}"

        if "timestamps" in df.columns:
            df["timestamps"] = pd.to_datetime(df["timestamps"])
        elif "timestamp" in df.columns:
            df["timestamps"] = pd.to_datetime(df["timestamp"])
        elif "date" in df.columns:
            df["timestamps"] = pd.to_datetime(df["date"])
        else:
            df["timestamps"] = pd.date_range(start="2024-01-01", periods=len(df), freq="1H")

        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

        df = df.dropna()
        return df, None

    except Exception as e:
        return None, f"ファイルの読み込みに失敗しました: {str(e)}"


def compute_train_last_timestamp_iso(data_path):
    """学習 CSV 全体の timestamps 最大値（ISO 文字列）。"""
    df, err = load_data_file(data_path)
    if err:
        return None, err
    if "timestamps" not in df.columns or len(df) == 0:
        return None, "timestamps 列がないか、データが空です"
    ts_max = df["timestamps"].max()
    if pd.isna(ts_max):
        return None, "タイムスタンプが無効です"
    if hasattr(ts_max, "isoformat"):
        s = ts_max.isoformat()
    else:
        s = str(ts_max)
    return s, None


def dataframe_to_ohlc_rows(df):
    """プレビュー・チャート用に DataFrame を行 dict のリストへ変換する。"""
    rows = []
    has_volume = "volume" in df.columns
    has_amount = "amount" in df.columns
    for _, row in df.iterrows():
        ts = row["timestamps"]
        item = {
            "timestamp": ts.isoformat() if pd.notna(ts) else None,
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        }
        if has_volume:
            v = row["volume"]
            item["volume"] = float(v) if pd.notna(v) else None
        if has_amount:
            a = row["amount"]
            item["amount"] = float(a) if pd.notna(a) else None
        rows.append(item)
    return rows
