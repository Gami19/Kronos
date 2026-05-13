"""`webui/backend` 直下の `.env` / `.env.local` を os.environ に読み込む（学習ジョブの事前学習パス等）。"""

from __future__ import annotations

from pathlib import Path


def load_dotenv_files() -> None:
    """`.env` を読み込み、続けて `.env.local` で上書き（ローカル専用）。"""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    here = Path(__file__).resolve().parent
    load_dotenv(here / ".env")
    load_dotenv(here / ".env.local", override=True)
