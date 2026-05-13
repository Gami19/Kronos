"""FastAPI application entry (phase 0: health + config stub)."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kronos_py import __version__


def _cors_origins() -> list[str]:
    raw = os.environ.get("KRONOS_CORS_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def create_app() -> FastAPI:
    app = FastAPI(title="kronos-py API", version=__version__)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "service": "kronos-py-api",
            "version": __version__,
        }

    @app.get("/api/config")
    def config_stub():
        """Phase 1 でフロントと検証を揃えるためのプレースホルダ。"""
        return {
            "max_context": 512,
            "intervals": [
                "1m",
                "5m",
                "15m",
                "30m",
                "60m",
                "1h",
                "1d",
                "1wk",
            ],
            "periods": [
                "1d",
                "5d",
                "1mo",
                "3mo",
                "6mo",
                "1y",
                "max",
            ],
            "note": "フェーズ0のスタブです。許容組み合わせは yfinance 制約と整合させます（フェーズ1）。",
        }

    return app


app = create_app()
