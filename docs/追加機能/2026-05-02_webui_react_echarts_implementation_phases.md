# Web UI: React / ECharts 移行 実装フェーズ案

会話に基づき、ローソク足チャート中心のフロント改善とバックエンド拡張の**実装フェーズ**を整理したもの。作業前に**別ブランチを切る**こと（ブランチ作成は担当者が行う）。

## 方針の要約

- **本番環境は考慮しない**（ローカル／単一環境。Flask + Vite 想定）。
- 当面 **三菱商事（`8058.T`）に固定**し、**予測用 CSV も三菱用に一本化**。将来 **`data/<銘柄>/` で複数銘柄**。
- **CSV が 5 分足のときは yfinance も 5 分足**（`interval=5m` 等）に揃える。取得できない区間は UI で明示。
- **全面 React 化**（モデル読み込み・データ・予測・プレビュー・ローソク表示）。**メインチャートは Apache ECharts を優先**（Plotly は過渡期・互換用に短く持てる）。
- 予測の保存先は **`webui/prediction_results/*.json`**。**`GET` は一覧＝メタのみ、詳細＝別リクエスト**。

---

## フェーズ 0: 前提・ブランチ

- 作業用ブランチを作成してから着手する。
- 実装完了時、変更点を本ドキュメントの方針に沿って追記・反映する（必要に応じて別日付の `docs/追加機能` も可）。

---

## フェーズ 1: バックエンド API・保存形式の土台

### 予測結果のディスク

- 保存 JSON に **`chart` を含める**。
- **`chart` の型はネストした JSON オブジェクト**（Plotly Figure 相当）。フロントは二重 `JSON.parse` 不要にする。
- 可能なら **`POST /api/predict` のレスポンス `chart` もオブジェクトに統一**し、API／ディスクで型を揃える。
- `save_prediction_results` 内の **`analysis.continuity` 付与ロジック**（`first_actual` のスコープ等）の不具合を修正する。

### 予測 JSON の取得（一覧と詳細の分離）

| メソッド | パス | 内容 |
|----------|------|------|
| `GET` | `/api/prediction-results` | **一覧。メタのみ**（例: id／ファイル名、保存時刻、`prediction_type` や `file_path` の要約など）。**本文・`chart`・長大配列は含めない。** |
| `GET` | `/api/prediction-results/<id>` | **1 件の全文**（`prediction_results`, `actual_data`, `chart`, `prediction_params` 等）。 |

※ `<id>` の具体的なキー（ファイル名 stem・UUID 等）は実装で決める。

### データ読み込み

- **`POST /api/load-data` のレスポンスに全行の OHLC（＋時刻列）を含める**（データプレビュー・軽いローソク・React 用）。

### 履歴（yfinance）

- Flask に **履歴用 `GET` を 1 本追加**（名称例: `/api/market-history`）。
- クエリで **`ticker`**（当面 `8058.T`、将来は複数銘柄）、**間隔（5m）**、期間などを受け取り、OHLC 配列を返す。

---

## フェーズ 2: React 基盤

- **Vite + React + TypeScript** でフロントプロジェクトを追加。
- 開発時は **プロキシで `/api` を Flask に転送**。
- ルーティング・レイアウト・API クライアントの骨組み。

---

## フェーズ 3: 全面 React（現行機能の置き換え）

**終了時に `templates/index.html` を削除し**、`/` は React ビルド成果物を配信する形にする。

含める機能:

- **モデル**: 一覧・デバイス・読み込み・状態。
- **データ**: ファイル選択、`load-data` の**全行**による **データプレビュー** と **軽いローソク**（最小でも可。フェーズ 4 で ECharts に寄せる）。
- **予測**: 時間窓・パラメータ・`POST /api/predict`。
- **過去結果**: **メタ一覧 `GET`** → 行選択 → **詳細 `GET`** で再表示。

※ ECharts を優先するため、本フェーズのプレビューローソクは **必要最小限**でもよい。

---

## フェーズ 4: メインチャート（Apache ECharts）

- **履歴**（market-history）＋ **予測**（詳細 JSON の `prediction_results`）＋ **実測**（`actual_data`）を **ECharts のローソク**で統合。
- 時刻軸・足の整合、ツールチップ、ズーム等。
- **`chart`（Plotly）** はデバッグ用に残すか省略するか、運用で判断。

---

## フェーズ 5: 複数銘柄と `data/` 整理

- **`data/<ticker>/`**（命名は実装で統一）と UI の銘柄選択。
- **履歴 API の `ticker`** と **予測用 CSV のパス解決**をサーバ側ルールで一本化。

---

## フェーズ 6: 仕上げ

- 型・エラー表示・yfinance 失敗時メッセージの整理。
- 必要に応じて `docs/追加機能/` に実装差分を日付付きで追記。

---

## API 一覧（参照用）

| メソッド | パス | 役割 |
|----------|------|------|
| `GET` | `/api/prediction-results` | 予測結果**一覧（メタのみ）** |
| `GET` | `/api/prediction-results/<id>` | 予測結果**1 件フル** |
| `GET` | `/api/market-history` | yfinance 履歴（5m 等） |
| `POST` | `/api/load-data` | メタ＋**全行** |
| 既存 | `/api/available-models`, `/api/load-model`, `/api/model-status`, `/api/data-files`, `/api/predict` | 全面 React から呼び出し |

既存 `POST /api/predict` の `chart` をオブジェクト化する場合は、本表の「既存」に合わせてレスポンス形を更新する。

---

## 更新履歴

- 2026-05-02: 初版（会話ベースのフェーズ案を文書化）。
- 2026-05-02: フェーズ6（仕上げ: 型・エラー表示・`market-history` の yfinance メッセージ）を実装完了。詳細は [2026-05-02_webui_phase6_polish.md](./2026-05-02_webui_phase6_polish.md) を参照。
