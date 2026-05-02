# Web UI フェーズ4: メインチャート（Apache ECharts）（2026-05-02）

## 概要

[docs/追加機能/2026-05-02_webui_react_echarts_implementation_phases.md](2026-05-02_webui_react_echarts_implementation_phases.md) のフェーズ4に沿い、`GET /api/market-history` の履歴と `prediction_results` / `actual_data` を **Apache ECharts** のローソクで統合表示した。Plotly 依存は削除しバンドルを縮小した。

## 変更ファイル（主なもの）

- [webui/frontend/package.json](../../webui/frontend/package.json): `echarts`, `echarts-for-react` 追加、`plotly.js` / `react-plotly.js` 削除
- [webui/frontend/src/echarts/registerEcharts.ts](../../webui/frontend/src/echarts/registerEcharts.ts): tree-shaking 用コンポーネント登録
- [webui/frontend/src/utils/ohlcMerge.ts](../../webui/frontend/src/utils/ohlcMerge.ts): 時刻キーで履歴から予測・実測区間を除外してマージ
- [webui/frontend/src/components/EChartsCandlestick.tsx](../../webui/frontend/src/components/EChartsCandlestick.tsx): 複数系列・tooltip・dataZoom
- [webui/frontend/src/components/OhlcCandlestickPreview.tsx](../../webui/frontend/src/components/OhlcCandlestickPreview.tsx): ECharts 化
- [webui/frontend/src/pages/WorkspacePage.tsx](../../webui/frontend/src/pages/WorkspacePage.tsx): 予測成功後に `marketHistory` を取得して統合チャート
- [webui/frontend/src/pages/HistoryPage.tsx](../../webui/frontend/src/pages/HistoryPage.tsx): 詳細選択時に同様。保存 JSON の Plotly `chart` は未使用
- 削除: `PlotlyFigure.tsx`, `plotlyChart.ts`

## UI

- 市場履歴の取得期間セレクト: `5d` / `30d` / `60d` / `1mo`（ティッカーは当面 `8058.T` 固定。フェーズ5で拡張予定）
- 履歴取得失敗時はメッセージを出し、**予測・実測のみ**でチャート表示

## 検証

- `cd webui/frontend && npm run build` が成功すること
- 予測後および `/history` 詳細でズーム・ツールチップが動作すること
