# Web UI フェーズ3: 全面 React と Flask 静的配信（2026-05-02）

## 概要

[docs/追加機能/2026-05-02_webui_react_echarts_implementation_phases.md](2026-05-02_webui_react_echarts_implementation_phases.md) のフェーズ3に沿い、従来の Jinja テンプレートを廃止し、React ビルドを Flask から配信する形に統合した。

## バックエンド

- [webui/app.py](../../webui/app.py): `render_template` をやめ、`frontend/dist` を返す `serve_spa` を追加（`/api` で始まるパスは 404 JSON）。ビルド未検出時は 503。
- [webui/templates/index.html](../../webui/templates/index.html): **削除**（`templates/` ディレクトリも削除）。
- [webui/run.py](../../webui/run.py)、[webui/start.sh](../../webui/start.sh): `frontend/dist/index.html` の存在チェックを追加。

## フロントエンド

- ルート: `/` ワークスペース、`/history` 過去結果、`/dev/api-check` 確認用。
- API: [webui/frontend/src/api/endpoints.ts](../../webui/frontend/src/api/endpoints.ts) に `loadModel` / `predict` / `getPredictionResultDetail` を追加。
- 主要コンポーネント: `TimeWindowSlider`（520 本固定窓）、`PlotlyFigure`、`OhlcCandlestickPreview`、`ComparisonPanel`。
- 依存: `plotly.js`、`react-plotly.js`（バンドルサイズ大。フェーズ4で ECharts 化時に見直し可）。

## 起動手順

1. `cd webui/frontend && npm ci && npm run build`
2. `cd webui && python run.py`（または `python app.py` / `./start.sh`）
3. http://localhost:7070 を開く

開発時は Vite（5173）＋ Flask（7070）の二段でも可。

## フェーズ4以降

メインチャートの ECharts 統合、`market-history` と予測結果の統合表示はフェーズ4で扱う。
