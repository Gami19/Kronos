"""Request bodies and query models for data / market-history endpoints (see frontend api/types.ts)."""

from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LoadDataBody(BaseModel):
    """POST /api/load-data"""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    file_path: str = Field(min_length=1, description="Path to CSV or feather under data/")


class ValidateDataBody(BaseModel):
    """POST /api/data/validate — invalid shapes must not become HTTP 400 (use 200 + valid: false)."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    file_path: str | None = None

    @field_validator("file_path", mode="before")
    @classmethod
    def coerce_file_path(cls, v: object) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        return None


class ImportMarketBody(BaseModel):
    """POST /api/data/import-market"""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    ticker_id: str = Field(min_length=1)
    interval: str | None = Field(default=None, description="Defaults to 5m in the view if omitted")
    period: str | None = Field(default=None, description="Defaults to 5d in the view if omitted")
    start: str | None = Field(default=None, description="YYYY-MM-DD 等。end と併せて指定時は period を無視")
    end: str | None = Field(default=None, description="YYYY-MM-DD 等。yfinance の end は排他的の場合がある")

    @field_validator("start", "end", mode="before")
    @classmethod
    def empty_str_to_none_import_range(cls, v: object) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        return None

    @model_validator(mode="after")
    def validate_import_range_pair_and_order(self) -> ImportMarketBody:
        has_s = self.start is not None
        has_e = self.end is not None
        if has_s ^ has_e:
            raise ValueError("start と end は両方指定するか、両方省略してください")
        if has_s and has_e:
            s = pd.to_datetime(self.start)
            e = pd.to_datetime(self.end)
            if pd.notna(s) and pd.notna(e) and s > e:
                raise ValueError("start は end 以下である必要があります")
        return self


class MarketHistoryQuery(BaseModel):
    """GET /api/market-history query string (allowed interval/period enforced in yfinance service)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    ticker: str | None = None
    interval: str = Field(default="5m")
    period: str = Field(default="5d")


class PredictBody(BaseModel):
    """POST /api/predict — 評価モード（末尾 lookback + 末尾 pred_len を実測比較）。"""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    file_path: str = Field(min_length=1)
    lookback: int = Field(default=400, ge=1, le=32768)
    pred_len: int = Field(default=120, ge=1, le=32768)
    temperature: float = Field(default=1.0)
    top_p: float = Field(default=0.9)
    sample_count: int = Field(default=1, ge=1, le=256)
    start_date: str | None = None
    end_date: str | None = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: object) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        return None

    @model_validator(mode="after")
    def validate_date_order(self) -> PredictBody:
        if self.start_date and self.end_date:
            s = pd.to_datetime(self.start_date)
            e = pd.to_datetime(self.end_date)
            if pd.notna(s) and pd.notna(e) and s > e:
                raise ValueError("start_date は end_date 以下である必要があります")
        return self
