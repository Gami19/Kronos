"""事前学習ディレクトリ・checkpoint パスの検証。"""

from __future__ import annotations

import os

from backend import paths as app_paths


def validate_pretrained_dir(abs_path, label):
    """事前学習ディレクトリ: 実在し、プロジェクトルート配下のみ。"""
    if not abs_path or not isinstance(abs_path, str):
        return (
            False,
            None,
            f"{label} を指定するか、環境変数 KRONOS_PRETRAINED_TOKENIZER / KRONOS_PRETRAINED_PREDICTOR を設定してください",
        )
    try:
        norm = os.path.normpath(os.path.realpath(abs_path.strip()))
    except OSError:
        return False, None, f"{label}: 無効なパスです"
    root = os.path.realpath(app_paths.project_root())
    if norm != root and not norm.startswith(root + os.sep):
        return False, None, f"{label}: プロジェクトルート配下のディレクトリのみ指定できます"
    if not os.path.isdir(norm):
        return False, None, f"{label}: ディレクトリが存在しません"
    return True, norm, None


def validate_checkpoint_dir(abs_path, label):
    """学習済み checkpoint ディレクトリ（from_pretrained 向け）。"""
    return validate_pretrained_dir(abs_path, label)
