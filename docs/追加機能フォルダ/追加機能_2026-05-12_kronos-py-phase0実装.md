# 追加: kronos-py フェーズ0（土台）実装（2026-05-12）

## 概要

kronos-py Phase0 計画に基づき、backend（FastAPI）と frontend（Vite + React）の最小構成を追加した。

## backend

- [kronos-py/backend/pyproject.toml](kronos-py/backend/pyproject.toml): Python 3.12、`fastapi`、`uvicorn[standard]`。
- [kronos-py/backend/src/kronos_py/main.py](kronos-py/backend/src/kronos_py/main.py): `GET /api/health`、`GET /api/config`（スタブ）、CORS（`KRONOS_CORS_ORIGINS`）。
- [kronos-py/backend/README.md](kronos-py/backend/README.md): **`PYTHONPATH=src` + `python -m uvicorn`** で起動（`pip install` 手順は記載しない）。

## frontend

- Vite + React + TS、[vite.config.ts](kronos-py/frontend/vite.config.ts) で `/api` を `127.0.0.1:8000` にプロキシ。
- [src/App.tsx](kronos-py/frontend/src/App.tsx): `/api/health` を取得して表示、読み込み中は Skeleton。
- [frontend/README.md](kronos-py/frontend/README.md): 開発サーバ・プロキシ・バックエンド先行起動を追記。

## その他

- ルート [.gitignore](.gitignore): `docs/` 一括無視をやめ、`docs/追加機能フォルダ/` のみ追跡対象にする例外を追加。

## 備考

依存のインストールは利用者の環境に委ねる（計画どおり README に `pip install` は書かない）。
