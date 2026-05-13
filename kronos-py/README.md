# kronos-py

リポジトリ内の **`standalone` とは独立した** Web アプリケーションです。import や `sys.path` で `standalone` に依存しません。Kronos モデルによる株価予測と、ろうそく足チャートでの可視化を目的とします。

## 全体像

| レイヤ | 役割 |
|--------|------|
| **frontend** | React（Vite）。銘柄・期間・予測パラメータの指定、確定 OHLC と Kronos 予測の表示。UX 詳細は [frontend/README.md](./frontend/README.md)。 |
| **backend** | Python 3.12、FastAPI + uvicorn。yfinance による市場データ取得、`/api/model/load` 後の推論 API。詳細は [backend/README.md](./backend/README.md)。 |

### バージョン方針

- **v1**: 推論と表示のみ（モデル読込 → データ取得 → 予測）。
- **v2**: ファインチューニング（別フェーズで backend に追加）。

### 目指す体験（UX の芯）

ユーザーが迷わず、「確定した過去」と「モデルが推した未来」を混同しない状態を目指す。

1. **モデルを用意してから予測する**  
   起動直後は推論できないことが分かり、`/api/model/load` が成功するまで「モデル読込」を完了させる。成功後のみ「予測」を有効にする。読込失敗時は理由が伝わること。

2. **銘柄とデータの取り方が分かる**  
   ティッカー（例: 日本株 `8058.T`）、足（`interval`）、期間（`period` または日付範囲）を指定し、サーバーが yfinance で取得する。取れない組み合わせ・本数不足（日内の取得制限や `lookback` 未満など）は、**日本語で次に何を試せばよいか**が分かるエラーにする。

3. **ろうそく足で状況把握してから予測する**  
   取得した履歴をチャートで確認したうえで、`lookback`・`pred_len`・サンプリング等を指定して予測する。`lookback` はモデルの **`max_context` を超えない**こと、かつ **取得バー本数で足りる**ことをフロント・API で揃えて検証する。

4. **予測は「履歴の延長」として見える**  
   確定バーと予測バーを **色・透明度・境界線** で分ける（詳細は [frontend/README.md](./frontend/README.md)）。予測 ON/OFF で表示を切り替えられるとよい。

5. **v1 は学習に触れない**  
   ファインチューニングの導線は出さず、推論と表示に集中する（v2 で backend に追加）。

### UX の芯（短縮メモ）

| # | 内容 |
|---|------|
| 1 | **`/api/model/load` 後だけ推論する。** |
| 2 | **市場データはサーバーが yfinance で取得**し、`lookback` / `max_context` / 取得本数を整合させる。 |
| 3 | **過去（確定）と未来（予測）を画面上で誤認しない。** |

実装フェーズの粒度は [frontend/README.md](./frontend/README.md) と [backend/README.md](./backend/README.md) を参照。

### 技術スタック（要約）

| 領域 | 選定 |
|------|------|
| フロント | React, Vite |
| API | FastAPI, uvicorn |
| ランタイム | Python 3.12 |
| 市場データ | yfinance（[API Reference](https://ranaroussi.github.io/yfinance/reference/index.html) を前提に検証） |
| モデル | Hugging Face Hub 上の Kronos（キャッシュは `HF_HOME` 等の環境変数で指定） |
| 開発機の例 | Apple Silicon（例: M4）では `mps` を環境変数等で選択可能にする想定 |

### ディレクトリ構成（目標）

```
kronos-py/
├── README.md          ← 本ファイル（全体像）
├── backend/           ← API・モデル・推論ロジック（README あり）
├── frontend/          ← SPA（README あり）
└── …                  ← model / finetune 等は実装フェーズで backend 配下などに配置（詳細は backend/README）
```

### Kronos モデルについて

Kronos は金融ローソク足向けのオープンソース基盤モデルです。概要・論文・モデル一覧は上流プロジェクトの資料（例: [arXiv](https://arxiv.org/abs/2508.02739)、[Hugging Face NeoQuasar](https://huggingface.co/NeoQuasar)）を参照してください。本 README では推論パラメータや `max_context` の注意は **backend README** とアプリ実装に寄せます。

## ドキュメント一覧

| ファイル | 内容 |
|----------|------|
| [frontend/README.md](./frontend/README.md) | UI/UX 設計・レイアウト・**実装フェーズ** |
| [backend/README.md](./backend/README.md) | API・環境・データ取得・推論・**実装フェーズ** |

## ライセンス

プロジェクトルートのライセンスに従います（未配置の場合はリポジトリルートの `LICENSE` を参照）。
