"""予測結果 JSON の永続化。"""

from __future__ import annotations

import datetime
import json
import os

from backend import paths as app_paths


def save_prediction_results(
    file_path,
    prediction_type,
    prediction_results,
    actual_data,
    input_data,
    prediction_params,
    chart=None,
):
    """予測結果をファイルに保存する。"""
    try:
        results_dir = app_paths.prediction_results_dir()
        os.makedirs(results_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"prediction_{timestamp}.json"
        filepath = os.path.join(results_dir, filename)

        save_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "file_path": file_path,
            "prediction_type": prediction_type,
            "prediction_params": prediction_params,
            "input_data_summary": {
                "rows": len(input_data),
                "columns": list(input_data.columns),
                "price_range": {
                    "open": {
                        "min": float(input_data["open"].min()),
                        "max": float(input_data["open"].max()),
                    },
                    "high": {
                        "min": float(input_data["high"].min()),
                        "max": float(input_data["high"].max()),
                    },
                    "low": {
                        "min": float(input_data["low"].min()),
                        "max": float(input_data["low"].max()),
                    },
                    "close": {
                        "min": float(input_data["close"].min()),
                        "max": float(input_data["close"].max()),
                    },
                },
                "last_values": {
                    "open": float(input_data["open"].iloc[-1]),
                    "high": float(input_data["high"].iloc[-1]),
                    "low": float(input_data["low"].iloc[-1]),
                    "close": float(input_data["close"].iloc[-1]),
                },
            },
            "prediction_results": prediction_results,
            "actual_data": actual_data,
            "chart": chart,
            "analysis": {},
        }

        if actual_data and len(actual_data) > 0 and len(prediction_results) > 0:
            last_pred = prediction_results[-1]
            first_actual = actual_data[0]
            save_data["analysis"]["continuity"] = {
                "last_prediction": {
                    "open": last_pred["open"],
                    "high": last_pred["high"],
                    "low": last_pred["low"],
                    "close": last_pred["close"],
                },
                "first_actual": {
                    "open": first_actual["open"],
                    "high": first_actual["high"],
                    "low": first_actual["low"],
                    "close": first_actual["close"],
                },
                "gaps": {
                    "open_gap": abs(last_pred["open"] - first_actual["open"]),
                    "high_gap": abs(last_pred["high"] - first_actual["high"]),
                    "low_gap": abs(last_pred["low"] - first_actual["low"]),
                    "close_gap": abs(last_pred["close"] - first_actual["close"]),
                },
                "gap_percentages": {
                    "open_gap_pct": (abs(last_pred["open"] - first_actual["open"]) / first_actual["open"]) * 100,
                    "high_gap_pct": (abs(last_pred["high"] - first_actual["high"]) / first_actual["high"]) * 100,
                    "low_gap_pct": (abs(last_pred["low"] - first_actual["low"]) / first_actual["low"]) * 100,
                    "close_gap_pct": (abs(last_pred["close"] - first_actual["close"]) / first_actual["close"]) * 100,
                },
            }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)

        print(f"予測結果を保存しました: {filepath}")
        return filepath

    except Exception as e:
        print(f"予測結果の保存に失敗しました: {e}")
        return None
