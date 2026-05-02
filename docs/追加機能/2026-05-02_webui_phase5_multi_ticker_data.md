# WebUI フェーズ5: 複数銘柄と `data/` 整理

## 概要

- データの第一配置を `data/<ticker>/`（CSV / Feather）に統一し、Flask でパス検証を一本化した。
- ルート直下のみファイルがある従来構成は合成銘柄 `__flat__` で後方互換する。

## バックエンド（`webui/app.py`）

- **`GET /api/tickers`**: データを含むサブディレクトリ名を銘柄 ID として返す。直下のみのときは `[{ id: __flat__, legacy_root: true, ... }]`。
- **`GET /api/data-files?ticker=`**: 銘柄別ファイル一覧。省略時は `8058.T` を優先した既定 ID。
- **`POST /api/load-data` / `POST /api/predict`**: `file_path` を `data/` 配下に限定し、`legacy_flat_layout_active()` でないとき直下ファイルは 400。
- **`GET /api/market-history`**: クエリ `ticker` が `__flat__` のとき yfinance 用に既定 `8058.T` を適用。

## フロントエンド

- `getTickers()` / `getDataFiles(ticker?)`。
- `TickerProvider`（`App.tsx` で `RouterProvider` をラップ）で選択銘柄を共有。
- ワークスペース・過去結果で `market-history` の ticker をコンテキストと同期。

## 検証の目安

- `data/8058.T/*.csv` で銘柄選択・一覧・読込・予測が通ること。
- 直下のみで `__flat__` が出ること。
- `data` 外を指す `file_path` が 400 になること。
