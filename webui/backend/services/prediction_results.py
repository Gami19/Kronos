"""Read prediction result JSON files from disk (metadata list and full payload)."""

from __future__ import annotations

import json
import os
import re
from typing import Any


def list_result_metas(results_dir: str) -> list[dict[str, Any]]:
    """Return list of summary dicts for each *.json in results_dir (newest names first)."""
    if not os.path.isdir(results_dir):
        return []

    items: list[dict[str, Any]] = []
    for name in sorted(os.listdir(results_dir), reverse=True):
        if not name.endswith(".json"):
            continue
        path = os.path.join(results_dir, name)
        try:
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        stem = os.path.splitext(name)[0]
        pr = doc.get("prediction_results")
        ad = doc.get("actual_data")
        fp = doc.get("file_path") or ""
        items.append(
            {
                "id": stem,
                "filename": name,
                "timestamp": doc.get("timestamp"),
                "prediction_type": doc.get("prediction_type"),
                "file_path": os.path.basename(fp) if fp else "",
                "prediction_params": doc.get("prediction_params"),
                "counts": {
                    "prediction_results": len(pr) if isinstance(pr, list) else 0,
                    "actual_data": len(ad) if isinstance(ad, list) else 0,
                },
            }
        )
    return items


def read_result_payload(
    results_dir: str,
    result_id: str,
    id_pattern: re.Pattern,
) -> tuple[dict[str, Any] | None, str | None, int | None]:
    """
    Load one prediction JSON by id.

    Returns (payload, error_message, http_status). On success, payload is set and the others are None.
    """
    if not id_pattern.fullmatch(result_id):
        return None, "無効な id です", 400

    path = os.path.join(results_dir, f"{result_id}.json")
    if not os.path.isfile(path):
        return None, "見つかりません", 404

    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        return None, f"読み込みに失敗しました: {str(e)}", 500

    return payload, None, None
