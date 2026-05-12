"""Kronos 本体の import（プロジェクトルートを sys.path に追加）と model_runtime の可否フラグ。"""

from __future__ import annotations

import sys

from backend import model_runtime as mr
from backend import paths as app_paths

sys.path.append(app_paths.project_root())

try:
    from model import Kronos, KronosTokenizer, KronosPredictor

    mr.set_model_available(True)
except ImportError:
    Kronos = KronosTokenizer = KronosPredictor = None  # type: ignore[misc, assignment]
    mr.set_model_available(False)
    print("警告: Kronos モデルをインポートできません。デモ用のシミュレーションデータを使用します")
