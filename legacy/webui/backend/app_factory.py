"""Flask application factory (delegates to backend.application.build_flask_app)."""


def create_app(test_config=None):
    """Create and return the Flask application instance."""
    import backend.application as webui_app

    return webui_app.build_flask_app(test_config)
