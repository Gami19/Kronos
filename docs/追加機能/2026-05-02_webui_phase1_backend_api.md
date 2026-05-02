# Web UI フェーズ1: バックエンド API 土台（2026-05-02）

## 概要

[docs/追加機能/2026-05-02_webui_react_echarts_implementation_phases.md](2026-05-02_webui_react_echarts_implementation_phases.md) のフェーズ1に沿い、Flask 側の API と予測結果 JSON の保存形式を整備した。

## 変更ファイル

- [webui/app.py](../../webui/app.py): API 追加・`chart` オブジェクト化・`save_prediction_results` 修正・ヘルパ
- [webui/requirements.txt](../../webui/requirements.txt): `yfinance` 追加
- [webui/templates/index.html](../../webui/templates/index.html): `chart` が文字列／オブジェクトの両方で動くよう互換
- [webui/frontend/README.md](../../webui/frontend/README.md): フェーズ2で React を置く予定の旨のみ

## `chart` の型

- `POST /api/predict` のレスポンスおよびディスク保存 JSON の `chart` は、Plotly Figure 相当の **ネストした JSON オブジェクト**（`data` / `layout` を含む dict）に統一した。
- `figure_to_plotly_dict` で `PlotlyJSONEncoder` 経由に変換している。

## `save_prediction_results`（`analysis.continuity`）

- `prediction_results` が空のときに `last_pred` が未定義になるスコープ不具合を修正した。
- `last_prediction` は **最終予測足** `prediction_results[-1]` と先頭実測 `actual_data[0]` のギャップ比較に変更した。

## 新規・変更 API

| メソッド | パス | 内容 |
|----------|------|------|
| `GET` | `/api/prediction-results` | 一覧（メタのみ。`chart`・長大配列は含めない） |
| `GET` | `/api/prediction-results/<id>` | 1 件全文（`id` はファイル名 stem、英数字・`_`・`-` のみ） |
| `GET` | `/api/market-history` | クエリ: `ticker`（既定 `8058.T`）、`interval`（既定 `5m`）、`period`（既定 `5d`）。OHLC 配列を `rows` で返却 |
| `POST` | `/api/load-data` | レスポンスに全行 `ohlc_rows`（`timestamp`, OHLC、任意で `volume` / `amount`）を追加 |

既存の `POST /api/predict` は `chart` をオブジェクトで返すよう変更（テンプレートは後方互換あり）。

## 依存

- `yfinance`（市場履歴 API 用）

## 注意

- 過去に保存された `prediction_results/*.json` に `chart` が無い場合がある。一覧 API はそのまま利用可能。詳細取得では旧ファイルは `chart` キーが欠ける場合がある。
- 5 分足などイントラデイデータは yfinance の制約により取得できる期間に上限がある。空データ時は HTTP 422 と `error` メッセージで返す。
