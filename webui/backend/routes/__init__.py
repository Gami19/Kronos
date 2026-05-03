"""Web UI API 用 Blueprint。各モジュールが view 関数を保持する。"""

from __future__ import annotations


def register_api_blueprints(app) -> None:
    """Register API blueprints in a fixed order. Catch-all SPA routes stay on the Flask app."""
    from backend.routes.backtest import backtest_bp
    from backend.routes.data import data_bp
    from backend.routes.misc import misc_bp
    from backend.routes.models import models_bp
    from backend.routes.prediction import prediction_bp
    from backend.routes.train import train_bp

    app.register_blueprint(misc_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(train_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(backtest_bp)
