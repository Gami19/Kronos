"""finetune_csv.CustomKlineDataset と同じ時系列分割式に基づく学習ジョブ事前検証。"""

from __future__ import annotations


def finetune_time_split_lengths(
    n: int,
    train_ratio: float,
    val_ratio: float,
) -> tuple[int, int, int]:
    """train_end, val_end, val_len（検証区間の行数）を返す。CustomKlineDataset._split_data_by_time と整合。"""
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    val_len = val_end - train_end
    return train_end, val_end, val_len


def validate_train_job_window_vs_split(
    n: int,
    lookback_window: int,
    predict_window: int,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    ratio_sum_epsilon: float = 1e-5,
) -> tuple[bool, str | None]:
    """
    学習・検証それぞれでスライディング窓が1本以上取れるか検証する。
    window = lookback_window + predict_window + 1
    """
    window = lookback_window + predict_window + 1
    ratio_sum = train_ratio + val_ratio + test_ratio
    if abs(ratio_sum - 1.0) > ratio_sum_epsilon:
        return (
            False,
            f"train_ratio + val_ratio + test_ratio の合計は 1.0 である必要があります（現在: {ratio_sum:.6f}）",
        )

    if n <= 0:
        return False, "データ行数が 0 です（読み込み後の有効行がありません）"

    train_end, _val_end, val_len = finetune_time_split_lengths(n, train_ratio, val_ratio)

    if train_end < window:
        return (
            False,
            f"学習区間の行数（先頭から約 {train_end} 行）が窓長 {window} "
            f"(lookback {lookback_window} + predict {predict_window} + 1) 未満です。"
            f" train_ratio を下げる・データを増やす・窓を縮小してください。",
        )

    if val_len < window:
        return (
            False,
            f"検証区間の行数（約 {val_len} 行）が窓長 {window} 未満です。"
            f" val_ratio を上げる・データを増やす・窓を縮小してください。"
            f"（全行数の目安: {n}）",
        )

    return True, None
