# kronos-py / backend

Python 3.12 想定の API 層です。**`standalone` とはコード・パスともに共有しません。** Kronos モデル、`yfinance`、推論オーケストレーションをここに閉じます。

## フェーズ0の起動（依存の宣言と実行）

依存関係は **[pyproject.toml](./pyproject.toml)** にのみ記載しています。環境への入れ方は利用者のポリシーに従ってください（**本 README に `pip install` 手順は記載しません**）。

### パッケージを site-packages に入れずに起動する（推奨）

**[`app.py`](./app.py)** が `src` を import パスに追加するため、次だけで起動できます。

```bash
cd kronos-py/backend
python app.py
```

既定は `127.0.0.1:8000`、ホットリロード有効。ホスト・ポートは環境変数で変更できます。

| 変数 | 既定 | 説明 |
|------|------|------|
| `KRONOS_HOST` | `127.0.0.1` | バインドアドレス |
| `KRONOS_PORT` | `8000` | ポート |
| `KRONOS_RELOAD` | `1` | `0` / `false` / `no` でリロード無効 |

### 代替: PYTHONPATH + uvicorn

`backend` ディレクトリで `src` を `PYTHONPATH` に含め、`uvicorn` をモジュールとして実行する方法です。

```bash
cd kronos-py/backend
export PYTHONPATH=src
python -m uvicorn kronos_py.main:app --reload --host 127.0.0.1 --port 8000
```

別シェルで確認する例:

```bash
curl -s http://127.0.0.1:8000/api/health
```

### 環境変数（CORS）

ブラウザから Vite（既定ポート 5173）で叩く場合、既定で `localhost` / `127.0.0.1` の Origin を許可しています。上書きする場合は **カンマ区切り**で指定します。

```bash
export KRONOS_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### その他のツール

[Astral uv](https://github.com/astral-sh/uv) 等で `pyproject.toml` に沿って環境を用意する場合は、そのツールのドキュメントに従ってください。

---

## 役割

| 領域 | 内容 |
|------|------|
| HTTP | FastAPI + uvicorn |
| 市場データ | `yfinance`（ティッカー・`interval`・`period` または `start`/`end`）。公式の [`PriceHistory.history`](https://ranaroussi.github.io/yfinance/reference/yfinance.price_history.html) の引数・制約に合わせて検証する |
| モデル | Hugging Face Hub から `KronosTokenizer` / `Kronos` を読み込み、`KronosPredictor` を組み立てる |
| 推論 | 履歴バー本数 `lookback` ≤ `max_context`、取得行数が足りることの検証のうえで `predict` |
| キャッシュ | `HF_HOME`、`TRANSFORMERS_CACHE` 等でキャッシュディレクトリを指定可能にする想定 |

## ライフサイクル（v1）

1. **`POST /api/model/load`** … 成功するまで推論 API は拒否（503 / 400 等、実装で統一）。  
2. **市場データ取得** … クライアントは銘柄・期間などを POST。サーバーが `yfinance` で OHLCV を取得し、正規化する。  
3. **`POST /api/predict`** … モデル已ロードかつデータ本数が `lookback` を満たすとき、末尾 `lookback` 本で Kronos 予測。

日内データは公式どおり **直近の範囲に制限がある**ため、`lookback` を満たせない場合は **422** と日本語メッセージで返す想定です。

## 環境変数（例・実装時に確定）

| 変数 | 用途 |
|------|------|
| `HF_HOME` / `HF_HUB_CACHE` 等 | Hugging Face のモデルキャッシュ場所 |
| `KRONOS_DEVICE` 等（名前は実装で統一） | `cpu` / `mps` / `cuda` の選択（Apple Silicon では `mps` を任意） |

## ディレクトリ配置（実装フェーズで確定）

- `model`（PyTorch 実装）および必要なら `finetune` / `finetune_csv` は **本パッケージ配下**に置き、`standalone` へパスを通さない。

## 実装フェーズ

「目指す体験」は [../README.md](../README.md) と揃える。`standalone` とはパス・import とも共有しない。

### フェーズ 0（土台）

- Python 3.12、[pyproject.toml](./pyproject.toml)、FastAPI + uvicorn の最小アプリ（起動手順は上記「フェーズ0の起動」）。
- **`GET /api/health`** で生存確認。
- CORS（`KRONOS_CORS_ORIGINS`）、標準出力ログ。
- **`GET /api/config`** … `max_context` 等のスタブ（フェーズ1で本実装と整合）。

### フェーズ 1（v1 コア）

- **`POST /api/model/load`** … Hugging Face から tokenizer / model を読み、`KronosPredictor` をプロセス内に保持。成功まで **`POST /api/predict` は拒否**。
- **市場データ** … `POST` でティッカー・`interval`・`period` または `start`/`end`。サーバーが `yfinance` で取得し、OHLCV + `timestamps` を正規化して返す（本数・最初/最後の時刻・警告）。
- **`POST /api/predict`** … モデル已ロードかつ取得本数 ≥ `lookback`、かつ `lookback` ≤ `max_context`。末尾 `lookback` 本で推論し、履歴 + 予測系列を JSON で返す。
- **yfinance** … [PriceHistory.history](https://ranaroussi.github.io/yfinance/reference/yfinance.price_history.html) の制約（例: 日内と直近範囲）を満たさないときは **422** と日本語メッセージ。
- **環境変数** … `HF_HOME` 等でキャッシュ、`KRONOS_DEVICE` 等で `cpu` / `mps` / `cuda`。
- **`model` パッケージ** … リポジトリ内 `kronos-py/backend` 配下などに配置し、`standalone` に依存しない。

### フェーズ 2（v1 磨き）

- `repair` / `auto_adjust` の既定値とドキュメント化、タイムアウト・エラー文言。
- 構造化ログ（ティッカー、取得本数、レイテンシ）。
- 429・ネットワークエラー時の再試行方針（軽量）。

### フェーズ 3（v2）

- ファインチューニング: ジョブ投入・状態・ログ・checkpoint 解決（`finetune_csv` 等を **本パッケージ内**に閉じて実装）。API・ワーカー設計はこのフェーズで追記する。

### フェーズ別と UX の対応（一覧）

| UX の芯（抜粋） | 主に該当フェーズ |
|-----------------|------------------|
| ロード後だけ推論 | 1 |
| サーバーが yfinance で取得・本数整合 | 1 → 2 |
| lookback / max_context | 1 |

## 関連ドキュメント

- リポジトリ全体・目指す体験: [../README.md](../README.md)
- フロントの UX・画面フェーズ: [../frontend/README.md](../frontend/README.md)
