# Kronos Web UI

Kronos 金融予測モデル用の Web ユーザーインターフェースです。直感的なグラフィカル操作で利用できます。

## ✨ 機能

- **複数フォーマットのデータ対応**: CSV、Feather などの金融データ形式に対応
- **スマートな時間窓**: 固定 400+120 本の時間窓をスライダーで選択
- **実モデルによる予測**: 実 Kronos モデルを組み込み、複数サイズのモデルに対応
- **予測品質の調整**: 温度、核サンプリング（top_p）、サンプル数などを調整可能
- **マルチデバイス**: CPU、CUDA、MPS などの計算デバイスに対応
- **比較分析**: 予測結果と実データの詳細な比較
- **ローソク足チャート**: 金融向けのローソク足表示

## 🚀 クイックスタート

UI は **React（Vite）** でビルドした成果物を Flask が配信します。初回およびフロント変更後は必ずビルドしてください。

```bash
cd webui/frontend
npm ci
npm run build
```

### 方法 1: Python スクリプトで起動
```bash
cd webui
python run.py
```

### 方法 2: Shell スクリプトで起動
```bash
cd webui
chmod +x start.sh
./start.sh
```

### 方法 3: モジュールとして直接起動（上級者向け）
```bash
cd webui
python -m backend.application
```
（`backend/application.py` 内の `build_flask_app` と `if __name__ == '__main__'` を使います。未ビルドの `frontend/dist` では UI が 503 になり得ます。）

起動後、ブラウザで http://localhost:7070 を開きます。

### 推奨起動（`run.py`）

開発・検証では **`python run.py` を第一推奨**とします（[バックエンド移行計画](../docs/backendフォルダ移行計画.md) の前提とも一致）。`run.py` は依存の有無と `frontend/dist/index.html` の存在を起動前に確認し、未ビルドのときに案内を出します。

## ディレクトリ構成（`frontend` / `backend`）

| パス | 役割 |
|------|------|
| **`frontend/`** | React + TypeScript（Vite）のソース。`npm run build` で **`frontend/dist/`** に静的成果物を出力し、Flask がそれを配信します。 |
| **`backend/`** | Flask 周りの整理用レイヤー。`app_factory.py` の `create_app()` がエントリ。`application.py` に `build_flask_app` と API ハンドラ本体。`routes/` に Blueprint（`/api` 等）、`lib/` に Flask 非依存の純ロジック、`services/` にビジネスロジック、`schemas/` に Pydantic によるリクエスト形の定義があります。 |
| **`run.py`** | 起動前チェックとブラウザオープンなどのエントリ用スクリプト。内部で `create_app()` を呼び出します。 |

移行のマイルストーン（フェーズ0〜5の全体像）は [docs/backendフォルダ移行計画.md](../docs/backendフォルダ移行計画.md) を参照してください。

## 📁 データ配置（複数銘柄）

- **推奨**: リポジトリ直下の `data/<銘柄ID>/` に CSV / Feather を置く。銘柄 ID はディレクトリ名（東証なら yfinance と同じ `1234.T` 形式が履歴取得と対応しやすい）。
- **レガシー**: `data/` 直下にのみファイルがある場合、Web UI では合成銘柄 **`__flat__`**（表示: ルート直下）として一覧され、従来どおり直下ファイルを選べる。
- **API**: `GET /api/tickers` で銘柄一覧、`GET /api/data-files?ticker=<id>` でファイル一覧。`POST /api/load-data` と `POST /api/predict` の `file_path` はプロジェクトの `data/` 配下のみ許可（パストラバーサル不可）。
- **市場履歴**: `GET /api/market-history?ticker=` は銘柄 ID をそのまま yfinance に渡す（`__flat__` のときはサーバ側で既定 `8058.T`）。

## 📋 利用手順

1. **銘柄とデータを選ぶ**: 銘柄セレクトで `data/<銘柄>/` を選び、ファイル一覧から金融データを選択
2. **モデルを読み込む**: Kronos モデルと計算デバイスを選択
3. **パラメータを設定する**: 予測品質に関するパラメータを調整
4. **時間窓を選ぶ**: スライダーで 400+120 本の範囲を指定
5. **予測を開始する**: 予測ボタンで結果を生成
6. **結果を確認する**: チャートと表で予測結果を確認

## `/finetune` ウィザード（初回セットアップ〜バックテスト）

ファインチューン用の一連操作は **`http://localhost:7070/finetune`** のウィザードで行います。

1. `cd webui/frontend && npm ci && npm run build` でフロントをビルドする。
2. `cd webui && python run.py` で Flask を起動する。
3. ブラウザで `/finetune` を開く。
4. **ステップ1 データ** → **2 モデル**（`POST /api/load-model`）→ **3 学習**（任意）→ **4 推論パラメータ** → **5 予測**（`POST /api/predict`）→ **6 バックテスト**（`POST /api/backtest/run`）の順で進める。

**同一 Python 環境（venv）**: WebUI の Flask と、`finetune_csv` の学習ジョブ（`train_sequential.py`）は **同じ venv** で動かす前提です（Phase 0 の運用）。別環境にすると依存やパスがずれます。

**Apple Silicon（M4 等）**: 学習・推論の `device` に **`mps`** を選べます。PyTorch が MPS を認識していること、およびメモリ不足に注意してください。

**ステップガード**: ステッパーは前提を満たさない先のステップは無効化されます（例: 推論パラメータ・予測へはモデル読込とプレビュー読込・十分な行数が必要）。無効なボタンにマウスを載せると理由のツールチップが出ます。

## 🔧 予測品質パラメータ

### 温度（T）
- **範囲**: 0.1 ～ 2.0
- **効果**: 予測のランダム性を制御
- **目安**: 品質重視なら 1.2 ～ 1.5 付近

### 核サンプリング（top_p）
- **範囲**: 0.1 ～ 1.0
- **効果**: 予測の多様性を制御
- **目安**: 0.95 ～ 1.0 でより広い候補を考慮

### サンプル数
- **範囲**: 1 ～ 5
- **効果**: 複数の予測サンプルを生成
- **目安**: 2 ～ 3 サンプルで品質向上を狙う場合が多い

## 📊 対応データ形式

### 必須列
- `open`: 始値
- `high`: 高値
- `low`: 安値
- `close`: 終値

### 任意列
- `volume`: 出来高
- `amount`: 取引金額（予測には使用しない）
- `timestamps` / `timestamp` / `date`: タイムスタンプ

## 🤖 モデル対応

- **Kronos-mini**: 約 4.1M パラメータ。軽量で高速な予測
- **Kronos-small**: 約 24.7M パラメータ。性能と速度のバランス
- **Kronos-base**: 約 102.3M パラメータ。高品質な予測

## 🖥️ GPU 加速

- **CPU**: 汎用計算。互換性が最も高い
- **CUDA**: NVIDIA GPU。性能面で有利なことが多い
- **MPS**: Apple Silicon GPU。Mac 利用時の選択肢

## ⚠️ 注意事項

- `amount` 列は予測には使わず表示用です
- 時間窓は 400+120=520 本に固定されています
- データファイルには十分な履歴が含まれている必要があります
- 初回のモデル読み込みではダウンロードが発生する場合があります

## 🔍 比較分析

予測と実データが揃う場合、次のような比較情報を自動表示します。
- 価格差の統計
- 誤差の分析
- 予測品質の目安

## 🛠️ 技術構成

- **バックエンド**: Flask + Python
- **フロントエンド**: React + TypeScript（Vite ビルド、`frontend/dist` を Flask が配信）
- **チャート**: Apache ECharts（メインローソク）、バックエンドの Plotly `chart` は保存のみで UI では未使用
- **データ処理**: Pandas + NumPy
- **モデル**: Hugging Face Transformers

## 📝 トラブルシューティング

### よくある問題
1. **ポートが使用中**: `run.py` または `backend/application.py` の末尾 `app.run(..., port=7070)` のポートを変更する
2. **依存関係不足**: `pip install -r requirements.txt` を実行する
3. **モデル読み込み失敗**: ネットワークとモデル ID を確認する
4. **データ形式エラー**: 列名と形式が要件を満たしているか確認する

### ログの見方

起動時にコンソールへ実行時情報（モデル状態やエラーなど）が表示されます。

## 📄 ライセンス

本プロジェクトは元の Kronos プロジェクトのライセンス条件に従います。

## 🤝 コントリビューション

Issue や Pull Request での改善提案を歓迎します。

## 📞 サポート

疑問がある場合は次を確認してください。
1. プロジェクトのドキュメント
2. GitHub Issues
3. コンソールのエラーメッセージ
