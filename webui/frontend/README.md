# Kronos Web UI — React（フェーズ4）

**Vite + React + TypeScript** のフロントです。本番では Flask（ポート **7070**）が `frontend/dist` を配信します。

## ビルド（必須）

```bash
cd webui/frontend
npm ci
npm run build
```

## 開発モード

1. `cd webui && python run.py`（7070）
2. `cd webui/frontend && npm run dev`（5173）

## メインチャート（Apache ECharts）

予測結果・実測と、`GET /api/market-history`（既定ティッカー **8058.T**・5分足）の履歴を **同一チャート**に重ねたローソクを表示します。ツールチップ・dataZoom（スライダー／ホイール）対応。

バックエンドが保存する **`chart`（Plotly 形式）は参照しません**（フェーズ4で UI は ECharts に統一）。

## 画面

- `/` … ワークスペース
- `/history` … 過去結果
- `/dev/api-check` … API 確認

## 依存のメモ

`echarts` はコア＋ローソク等を tree-shaking 登録しています（[src/echarts/registerEcharts.ts](src/echarts/registerEcharts.ts)）。バンドルは Plotly 時代より大幅に小さくなっています。
