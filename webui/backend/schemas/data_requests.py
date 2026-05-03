"""Request bodies and query models for data / market-history endpoints (see frontend api/types.ts)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class MarketHistoryQuery(BaseModel):
    """GET /api/market-history query string (allowed interval/period enforced in yfinance service)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    ticker: str | None = None
    interval: str = Field(default="5m")
    period: str = Field(default="5d")
