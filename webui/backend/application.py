"""Flask アプリ組み立てと SPA 配信。API ハンドラは ``backend.routes`` にある。"""

from __future__ import annotations

import os
import warnings

import backend.kronos_loader  # noqa: F401  # side effect: sys.path, Kronos import, mr flag

from backend import model_runtime as mr
from backend import paths as app_paths
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

warnings.filterwarnings("ignore")

FRONTEND_DIST = os.path.join(app_paths.webui_dir(), "frontend", "dist")


def build_flask_app(test_config=None):
    """Create and configure the Flask application. Catch-all SPA route must stay last."""
    app = Flask(__name__)
    if test_config:
        app.config.update(test_config)
    CORS(app)

    from backend.routes import register_api_blueprints

    register_api_blueprints(app)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path):
        """React ビルド成果物を配信する（開発時は Vite を別途利用）"""
        if path == "api" or path.startswith("api/"):
            return jsonify({"error": "Not found"}), 404

        dist = FRONTEND_DIST
        dist_norm = os.path.normpath(dist)
        if not os.path.isdir(dist):
            return jsonify(
                {
                    "error": "フロントエンドがビルドされていません。webui/frontend で npm run build を実行してください",
                }
            ), 503

        if path:
            candidate = os.path.normpath(os.path.join(dist, path))
            if candidate.startswith(dist_norm) and os.path.isfile(candidate):
                rel = os.path.relpath(candidate, dist_norm)
                return send_from_directory(dist, rel)

        return send_from_directory(dist, "index.html")

    return app


if __name__ == "__main__":
    print("Kronos Web UI を起動しています…")
    print(f"モデル利用可否: {mr.MODEL_AVAILABLE}")
    if mr.MODEL_AVAILABLE:
        print("ヒント: /api/load-model エンドポイントから Kronos モデルを読み込めます")
    else:
        print("ヒント: デモ用にシミュレーションデータが使われます")
    index_html = os.path.join(FRONTEND_DIST, "index.html")
    if not os.path.isfile(index_html):
        print(
            "警告: frontend/dist/index.html がありません。UI は 503 になります。cd frontend && npm run build を実行してください。"
        )

    app = build_flask_app()
    app.run(debug=True, host="0.0.0.0", port=7070)
