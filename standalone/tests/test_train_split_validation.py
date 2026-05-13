"""train_split_validation: finetune 分割式と窓長の事前検証。"""

from __future__ import annotations

import sys
from pathlib import Path

_WEBUI = Path(__file__).resolve().parent.parent / "webui"
if str(_WEBUI) not in sys.path:
    sys.path.insert(0, str(_WEBUI))

from backend.services.train_split_validation import (  # noqa: E402
    finetune_time_split_lengths,
    validate_train_job_window_vs_split,
)


def test_finetune_time_split_lengths_matches_int_truncation():
    n = 4698
    train_end, val_end, val_len = finetune_time_split_lengths(n, 0.9, 0.1)
    assert train_end == int(n * 0.9)
    assert val_end == int(n * 1.0)
    assert val_len == val_end - train_end


def test_validate_rejects_small_val_with_default_like_ratios():
    n = 4698
    window = 512 + 48 + 1
    ok, err = validate_train_job_window_vs_split(n, 512, 48, 0.9, 0.1, 0.0)
    assert ok is False
    assert err is not None
    assert str(window) in err


def test_validate_accepts_quality_ratios_for_typical_n():
    n = 4698
    ok, err = validate_train_job_window_vs_split(n, 512, 48, 0.85, 0.15, 0.0)
    assert ok is True
    assert err is None


def test_validate_rejects_ratio_sum_not_one():
    ok, err = validate_train_job_window_vs_split(10000, 512, 48, 0.85, 0.15, 0.01)
    assert ok is False
    assert err is not None
    assert "1.0" in err
