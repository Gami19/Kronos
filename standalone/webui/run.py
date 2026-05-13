#!/usr/bin/env python3
"""
Kronos Web UI 起動スクリプト
"""

import os
import sys
import subprocess
import webbrowser
import time

def check_dependencies():
    """依存パッケージが入っているか確認する"""
    try:
        import flask
        import flask_cors
        import pandas
        import numpy
        import plotly
        print("✅ 依存パッケージはすべてインストール済みです")
        return True
    except ImportError as e:
        print(f"❌ 不足しているパッケージがあります: {e}")
        print("次を実行してください: pip install -r requirements.txt")
        return False

def install_dependencies():
    """依存パッケージをインストールする"""
    print("依存パッケージをインストールしています…")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依存パッケージのインストールが完了しました")
        return True
    except subprocess.CalledProcessError:
        print("❌ 依存パッケージのインストールに失敗しました")
        return False

def check_frontend_dist():
    """React ビルド済みか確認する"""
    base = os.path.dirname(os.path.abspath(__file__))
    index_html = os.path.join(base, 'frontend', 'dist', 'index.html')
    if os.path.isfile(index_html):
        return True
    print("❌ フロントエンドがビルドされていません。")
    print("   次を実行してください: cd frontend && npm ci && npm run build")
    return False


def main():
    """エントリポイント"""
    print("🚀 Kronos Web UI を起動しています…")
    print("=" * 50)
    
    # 依存関係の確認
    if not check_dependencies():
        print("\n依存パッケージを自動インストールしますか？ (y/n): ", end="")
        if input().lower() == 'y':
            if not install_dependencies():
                return
        else:
            print("手動で依存パッケージをインストールしてから再度実行してください")
            return
    
    # モデル利用可否
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from model import Kronos, KronosTokenizer, KronosPredictor
        print("✅ Kronos モデルライブラリを利用できます")
    except ImportError:
        print("⚠️  Kronos モデルライブラリが利用できません。シミュレーション予測になります")
    
    if not check_frontend_dist():
        return
    
    # Flask アプリ起動
    print("\n🌐 Web サーバを起動しています…")
    
    try:
        from backend.app_factory import create_app

        app = create_app()
        print("✅ Web サーバの起動に成功しました")
        print(f"🌐 アクセス URL: http://localhost:7070")
        print("💡 ヒント: サーバを止めるには Ctrl+C を押してください")
        
        time.sleep(2)
        webbrowser.open('http://localhost:7070')
        
        app.run(debug=True, host='0.0.0.0', port=7070)
        
    except Exception as e:
        print(f"❌ 起動に失敗しました: {e}")
        print("ポート 7070 が他プロセスで使われていないか確認してください")

if __name__ == "__main__":
    main()
