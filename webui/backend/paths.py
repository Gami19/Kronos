"""Filesystem paths for the Web UI (no Flask, no import of app)."""

from __future__ import annotations

import os


def webui_dir() -> str:
    """Absolute path to the webui/ directory (parent of backend/)."""
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def project_root() -> str:
    """Repository root (parent of webui/)."""
    return os.path.normpath(os.path.join(webui_dir(), ".."))


def project_data_dir() -> str:
    """Repository data/ directory (absolute)."""
    return os.path.normpath(os.path.join(project_root(), "data"))


def prediction_results_dir() -> str:
    """Directory where prediction JSON files are stored (under webui/)."""
    return os.path.join(webui_dir(), "prediction_results")


def finetune_csv_dir() -> str:
    """finetune_csv ディレクトリ（リポジトリルート直下）。"""
    return os.path.normpath(os.path.join(project_root(), "finetune_csv"))


def train_jobs_runs_dir() -> str:
    """学習ジョブ run ディレクトリ（finetune_csv/runs）。"""
    return os.path.normpath(os.path.join(finetune_csv_dir(), "runs"))
