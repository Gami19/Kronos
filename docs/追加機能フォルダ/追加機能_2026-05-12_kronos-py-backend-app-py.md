# 追加: kronos-py backend `app.py` 起動（2026-05-12）

## 変更内容

- [kronos-py/backend/app.py](kronos-py/backend/app.py) を追加。`kronos-py/backend` で **`python app.py`** により uvicorn を起動。起動前に `src` を `sys.path` に追加するため **`PYTHONPATH` 不要**。
- 環境変数: `KRONOS_HOST` / `KRONOS_PORT` / `KRONOS_RELOAD`（README に表で記載）。
- [kronos-py/backend/README.md](kronos-py/backend/README.md): 推奨起動を `python app.py` に変更し、`PYTHONPATH` + uvicorn を「代替」に整理。

## 備考

`pip install` 手順は README に追加していない（既存方針のまま）。
