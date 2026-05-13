#!/bin/bash

# Kronos Web UI 起動スクリプト

echo "🚀 Kronos Web UI を起動しています…"
echo "================================"

# Python3 の有無
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 がインストールされていません。先に Python3 を入れてください"
    exit 1
fi

# カレントディレクトリ確認
if [ ! -f "run.py" ]; then
    echo "❌ webui ディレクトリでこのスクリプトを実行してください"
    exit 1
fi

# 依存関係
echo "📦 依存パッケージを確認しています…"
if ! python3 -c "import flask, flask_cors, pandas, numpy, plotly" &> /dev/null; then
    echo "⚠️  依存パッケージが不足しています。インストールします…"
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 依存パッケージのインストールに失敗しました"
        exit 1
    fi
    echo "✅ 依存パッケージのインストールが完了しました"
else
    echo "✅ 依存パッケージはすべてインストール済みです"
fi

# React ビルド
if [ ! -f "frontend/dist/index.html" ]; then
    echo "❌ フロントエンドがビルドされていません"
    echo "   cd frontend && npm ci && npm run build を実行してから再度起動してください"
    exit 1
fi

# アプリ起動
echo "🌐 Web サーバを起動しています…"
echo "アクセス URL: http://localhost:7070"
echo "停止するには Ctrl+C を押してください"
echo ""

python3 run.py
