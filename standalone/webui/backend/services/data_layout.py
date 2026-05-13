"""data ディレクトリレイアウト・ティッカー一覧・パス検証（Flask 非依存）。"""

from __future__ import annotations

import os

from backend import paths as app_paths
from backend.lib.data_path_rules import TICKER_FOLDER_PATTERN, validate_data_file_path_against_base

FLAT_TICKER_ID = "__flat__"
DEFAULT_YFIN_TICKER = "8058.T"


def project_data_dir():
    return app_paths.project_data_dir()


def _directory_has_data_files(dir_path):
    if not os.path.isdir(dir_path):
        return False
    for name in os.listdir(dir_path):
        if name.endswith((".csv", ".feather")):
            child = os.path.join(dir_path, name)
            if os.path.isfile(child):
                return True
    return False


def list_ticker_subdirs_with_data():
    """銘柄サブフォルダのうちデータファイルを1つ以上含むものの ID 一覧。"""
    base = project_data_dir()
    found = []
    if not os.path.isdir(base):
        return found
    for name in sorted(os.listdir(base)):
        sub = os.path.join(base, name)
        if not os.path.isdir(sub) or name.startswith("."):
            continue
        if not TICKER_FOLDER_PATTERN.fullmatch(name):
            continue
        if _directory_has_data_files(sub):
            found.append(name)
    return found


def legacy_flat_layout_active():
    """銘柄サブフォルダにデータがなく、ルート直下にのみ CSV/Feather がある。"""
    if list_ticker_subdirs_with_data():
        return False
    base = project_data_dir()
    if not os.path.isdir(base):
        return False
    for name in os.listdir(base):
        if name.endswith((".csv", ".feather")):
            fp = os.path.join(base, name)
            if os.path.isfile(fp):
                return True
    return False


def get_tickers_payload():
    """GET /api/tickers 用のエントリ一覧。"""
    items = []
    for tid in list_ticker_subdirs_with_data():
        items.append({"id": tid, "label": tid, "legacy_root": False})
    if legacy_flat_layout_active():
        items.append(
            {
                "id": FLAT_TICKER_ID,
                "label": "ルート直下（レガシー）",
                "legacy_root": True,
            }
        )
    return items


def default_ticker_id():
    """既定銘柄。"""
    subs = list_ticker_subdirs_with_data()
    if "8058.T" in subs:
        return "8058.T"
    if subs:
        return subs[0]
    if legacy_flat_layout_active():
        return FLAT_TICKER_ID
    return FLAT_TICKER_ID


def load_data_files_for_ticker(ticker_id):
    """指定銘柄ディレクトリまたはレガシールートのファイル一覧。"""
    base = project_data_dir()
    data_files = []

    if ticker_id == FLAT_TICKER_ID:
        if not os.path.isdir(base):
            return data_files
        for file in sorted(os.listdir(base)):
            if not file.endswith((".csv", ".feather")):
                continue
            file_path = os.path.join(base, file)
            if not os.path.isfile(file_path):
                continue
            file_size = os.path.getsize(file_path)
            data_files.append(
                {
                    "name": file,
                    "path": file_path,
                    "size": (
                        f"{file_size / 1024:.1f} KB"
                        if file_size < 1024 * 1024
                        else f"{file_size / (1024 * 1024):.1f} MB"
                    ),
                }
            )
        return data_files

    sub = os.path.join(base, ticker_id)
    if not os.path.isdir(sub):
        return data_files

    for file in sorted(os.listdir(sub)):
        if not file.endswith((".csv", ".feather")):
            continue
        file_path = os.path.join(sub, file)
        if not os.path.isfile(file_path):
            continue
        file_size = os.path.getsize(file_path)
        data_files.append(
            {
                "name": file,
                "path": file_path,
                "size": (
                    f"{file_size / 1024:.1f} KB"
                    if file_size < 1024 * 1024
                    else f"{file_size / (1024 * 1024):.1f} MB"
                ),
            }
        )
    return data_files


def validate_data_file_path(file_path):
    """load-data / predict で許可するパスか検証する。"""
    base = os.path.realpath(project_data_dir())
    return validate_data_file_path_against_base(
        file_path,
        base,
        os.path.isdir(base),
        legacy_flat_layout_active(),
    )


def yfinance_ticker_from_client_param(raw_ticker):
    """UI の銘柄 ID を yfinance シンボルに変換。"""
    if raw_ticker is None:
        return DEFAULT_YFIN_TICKER
    s = raw_ticker.strip()
    if not s or s == FLAT_TICKER_ID:
        return DEFAULT_YFIN_TICKER
    return s
