"""webui/data_path_rules — データファイルパス検証のユニットテスト"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from webui.backend.lib.data_path_rules import validate_data_file_path_against_base  # noqa: E402


def test_rejects_path_outside_base(tmp_path: Path):
    base = str(tmp_path.resolve())
    evil = tmp_path.parent / "outside.csv"
    evil.write_text("x", encoding="utf-8")
    ok, err = validate_data_file_path_against_base(str(evil.resolve()), base, True, False)
    assert ok is False
    assert err is not None
    assert "許可されていない" in err or "無効" in err


def test_two_level_csv_ok(tmp_path: Path):
    base = str(tmp_path.resolve())
    ticker = tmp_path / "8058.T"
    ticker.mkdir()
    f = ticker / "a.csv"
    f.write_text("x", encoding="utf-8")
    ok, err = validate_data_file_path_against_base(str(f.resolve()), base, True, False)
    assert ok is True
    assert err is None


def test_flat_file_requires_legacy(tmp_path: Path):
    base = str(tmp_path.resolve())
    f = tmp_path / "root.csv"
    f.write_text("x", encoding="utf-8")
    ok, err = validate_data_file_path_against_base(str(f.resolve()), base, True, legacy_flat_layout=False)
    assert ok is False
    assert err and "直下" in err


def test_flat_file_allowed_with_legacy(tmp_path: Path):
    base = str(tmp_path.resolve())
    f = tmp_path / "root.csv"
    f.write_text("x", encoding="utf-8")
    ok, err = validate_data_file_path_against_base(str(f.resolve()), base, True, legacy_flat_layout=True)
    assert ok is True
    assert err is None


def test_rejects_deep_path(tmp_path: Path):
    base = str(tmp_path.resolve())
    ticker = tmp_path / "8058.T"
    ticker.mkdir()
    sub = ticker / "nested"
    sub.mkdir()
    f = sub / "a.csv"
    f.write_text("x", encoding="utf-8")
    ok, err = validate_data_file_path_against_base(str(f.resolve()), base, True, False)
    assert ok is False
    assert err and "無効" in err


def test_invalid_ticker_folder_name(tmp_path: Path):
    base = str(tmp_path.resolve())
    bad = tmp_path / "..bad"
    bad.mkdir()
    f = bad / "a.csv"
    f.write_text("x", encoding="utf-8")
    ok, err = validate_data_file_path_against_base(str(f.resolve()), base, True, False)
    assert ok is False
