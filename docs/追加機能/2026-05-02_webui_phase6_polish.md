# WebUI フェーズ6: 仕上げ（型・エラー・yfinance）

## 概要

- フロントの API 型（`chart`・エラーボディ）と catch 時の表示を整理した。
- `GET /api/market-history` のクエリ検証と yfinance 失敗時メッセージを改善した。

## バックエンド（`webui/app.py`）

- **`interval` / `period`**: ホワイトリスト外は **400**、`success: false` と `error` に許可値一覧を含む。
- **例外**: `TimeoutError` / `ConnectionError` は短い日本語メッセージ。その他は要約付きの一文（長い `str(e)` は切り詰め）。
- **空の履歴**: 分足・時間足のときは、期間上限・日足への誘導文を `error` に追記（**422**）。

## フロントエンド

- **`ApiErrorBody`**, **`PlotlyFigureJSON`**（`types.ts`）と `client.ts` の `ApiErrorBody` キャスト。
- **`formatUserFacingError`**（`utils/formatError.ts`）で Workspace / History / TickerContext / API 確認ページの catch を統一。

## 検証の目安

- `interval=invalid` で 400 と分かる `error` が返ること。
- `npm run build`（`webui/frontend`）が通ること。
