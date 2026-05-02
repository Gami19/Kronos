# Web UI フェーズ2: React 基盤（2026-05-02）

## 概要

[docs/追加機能/2026-05-02_webui_react_echarts_implementation_phases.md](2026-05-02_webui_react_echarts_implementation_phases.md) のフェーズ2に沿い、[webui/frontend](../../webui/frontend) に Vite + React + TypeScript を追加した。

## 追加・更新ファイル（主なもの）

- [webui/frontend/package.json](../../webui/frontend/package.json), `package-lock.json`
- [webui/frontend/vite.config.ts](../../webui/frontend/vite.config.ts) … `/api` → `http://localhost:7070` プロキシ
- [webui/frontend/tsconfig.json](../../webui/frontend/tsconfig.json) ほか TS 設定
- [webui/frontend/index.html](../../webui/frontend/index.html), [webui/frontend/src/main.tsx](../../webui/frontend/src/main.tsx), [webui/frontend/src/App.tsx](../../webui/frontend/src/App.tsx)
- [webui/frontend/src/router.tsx](../../webui/frontend/src/router.tsx) … `createBrowserRouter`
- [webui/frontend/src/layouts/MainLayout.tsx](../../webui/frontend/src/layouts/MainLayout.tsx)
- [webui/frontend/src/pages/HomePage.tsx](../../webui/frontend/src/pages/HomePage.tsx), [ApiCheckPage.tsx](../../webui/frontend/src/pages/ApiCheckPage.tsx)
- [webui/frontend/src/api/client.ts](../../webui/frontend/src/api/client.ts), [types.ts](../../webui/frontend/src/api/types.ts), [endpoints.ts](../../webui/frontend/src/api/endpoints.ts)
- [.gitignore](../../.gitignore) … `node_modules/`（既存の `dist/` でビルド出力も除外）
- [webui/frontend/README.md](../../webui/frontend/README.md)

## 起動手順

1. ターミナル1: `cd webui && python run.py`（Flask · 7070）
2. ターミナル2: `cd webui/frontend && npm install && npm run dev`
3. ブラウザで Vite の URL（通常 `http://localhost:5173`）を開く

## フェーズ2の境界（本フェーズでは未実施）

- Flask の `/` を React ビルドに差し替え、`templates/index.html` の削除 → **フェーズ3**
- モデル読込・データプレビュー・予測・過去結果の本実装 → **フェーズ3以降**
