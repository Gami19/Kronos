"""Unit tests for backend.services.prediction_results."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

_WEBUI = Path(__file__).resolve().parent.parent / "webui"
if str(_WEBUI) not in sys.path:
    sys.path.insert(0, str(_WEBUI))

from backend.services import prediction_results as pr_svc  # noqa: E402

_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def test_list_result_metas_empty_dir(tmp_path):
    assert pr_svc.list_result_metas(str(tmp_path / "missing")) == []


def test_list_result_metas_and_read_payload(tmp_path):
    d = tmp_path / "prediction_results"
    d.mkdir()
    doc = {
        "timestamp": "2026-01-01T00:00:00",
        "prediction_type": "test",
        "file_path": "/data/foo/bar.csv",
        "prediction_params": {},
        "prediction_results": [{"open": 1}],
        "actual_data": [],
    }
    (d / "prediction_abc123.json").write_text(json.dumps(doc), encoding="utf-8")

    metas = pr_svc.list_result_metas(str(d))
    assert len(metas) == 1
    assert metas[0]["id"] == "prediction_abc123"
    assert metas[0]["filename"] == "prediction_abc123.json"
    assert metas[0]["file_path"] == "bar.csv"
    assert metas[0]["counts"]["prediction_results"] == 1
    assert metas[0]["counts"]["actual_data"] == 0

    payload, err, code = pr_svc.read_result_payload(str(d), "prediction_abc123", _ID_PATTERN)
    assert err is None and code is None
    assert payload == doc


def test_read_result_invalid_id(tmp_path):
    d = tmp_path / "prediction_results"
    d.mkdir()
    payload, err, code = pr_svc.read_result_payload(str(d), "../x", _ID_PATTERN)
    assert payload is None
    assert code == 400


def test_read_result_not_found(tmp_path):
    d = tmp_path / "prediction_results"
    d.mkdir()
    payload, err, code = pr_svc.read_result_payload(str(d), "missing_id", _ID_PATTERN)
    assert payload is None
    assert code == 404
