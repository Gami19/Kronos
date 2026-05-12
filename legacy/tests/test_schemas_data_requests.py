"""Pydantic schemas for data / market-history API (phase 4 slice 1)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

_WEBUI = Path(__file__).resolve().parent.parent / "webui"
if str(_WEBUI) not in sys.path:
    sys.path.insert(0, str(_WEBUI))

from backend.schemas.data_requests import (  # noqa: E402
    ImportMarketBody,
    LoadDataBody,
    MarketHistoryQuery,
    ValidateDataBody,
)


def test_load_data_body_requires_nonempty_file_path():
    with pytest.raises(ValidationError):
        LoadDataBody.model_validate({})
    with pytest.raises(ValidationError):
        LoadDataBody.model_validate({"file_path": ""})
    with pytest.raises(ValidationError):
        LoadDataBody.model_validate({"file_path": "   "})


def test_load_data_body_accepts_path():
    m = LoadDataBody.model_validate({"file_path": "  data/foo.csv  "})
    assert m.file_path == "data/foo.csv"


def test_validate_data_body_omits_file_path():
    m = ValidateDataBody.model_validate({})
    assert m.file_path is None


def test_validate_data_body_coerces_invalid_file_path_to_none():
    m = ValidateDataBody.model_validate({"file_path": 123})
    assert m.file_path is None


def test_import_market_body_defaults_optional_strings():
    m = ImportMarketBody.model_validate({"ticker_id": "8058.T"})
    assert m.ticker_id == "8058.T"
    assert m.interval is None
    assert m.period is None


def test_market_history_query_defaults():
    m = MarketHistoryQuery.model_validate({})
    assert m.ticker is None
    assert m.interval == "5m"
    assert m.period == "5d"
