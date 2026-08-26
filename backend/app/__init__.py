"""Application factory.

One process serves both the JSON API under ``/api/v1`` and, in production, the
built React app. Everything configurable comes from :class:`Settings`.
"""

import logging
import os
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from .api.routes.auth import auth_bp
from .api.routes.chat import chat_bp
from .api.routes.checkins import checkins_bp
from .api.routes.daily_tasks import daily_tasks_bp
from .api.routes.goals import goals_bp
from .api.routes.health import health_bp
from .api.routes.insights import insights_bp
from .api.routes.life_rules import life_rules_bp
from .core.config import Settings
from .core.database import db
from .core.errors import register_error_handlers

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> Flask:
    config = settings or Settings()
    logging.basicConfig(
        level=logging.INFO if config.is_production else logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    for problem in config.validate():
        logging.getLogger(__name__).error("Configuration problem: %s", problem)

    dist = Path(config.frontend_dist)
    app = Flask(
        __name__,
        static_folder=str(dist) if dist.is_dir() else None,
        static_url_path="/static-assets",
    )
    app.config.from_mapping(
        SECRET_KEY=config.secret_key,
        SQLALCHEMY_DATABASE_URI=config.database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True}
        if not config.database_url.startswith("sqlite")
        else {},
        APP_SETTINGS=config,
        JSON_SORT_KEYS=False,
    )

    CORS(
        app,
        resources={r"/api/*": {"origins": config.cors_origins}},
        supports_credentials=False,
    )
    db.init_app(app)

    for blueprint in (
        health_bp,
        auth_bp,
        goals_bp,
        life_rules_bp,
        daily_tasks_bp,
        checkins_bp,
        insights_bp,
        chat_bp,
    ):
        app.register_blueprint(blueprint, url_prefix=API_PREFIX)

    register_error_handlers(app)
    _register_frontend(app, dist)
    _register_cli(app)

    if config.auto_create_tables:
        with app.app_context():
            from . import models  # noqa: F401  (registers every table)

            db.create_all()

    return app


def _register_frontend(app: Flask, dist: Path) -> None:
    """Serve the built SPA, letting client-side routing own unknown paths."""
    if not dist.is_dir():
        @app.get("/")
        def api_root():
            return jsonify(
                {
                    "service": "consistency-ai",
                    "api": API_PREFIX,
                    "note": "Frontend build not found; run the Vite dev server instead.",
                }
            )

        return

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def spa(path: str):
        candidate = dist / path
        if path and candidate.is_file():
            return send_from_directory(dist, path)
        return send_from_directory(dist, "index.html")


def _register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db() -> None:
        """Create every table that does not yet exist."""
        from . import models  # noqa: F401

        db.create_all()
        print("Database ready.")

    @app.cli.command("seed")
    def seed() -> None:
        """Populate a demo account with a month of believable history."""
        from .seed import seed_demo_data

        email = os.getenv("SEED_EMAIL", "demo@consistency.ai")
        password = os.getenv("SEED_PASSWORD", "demo-password-123")
        seed_demo_data(email, password)
        print(f"Seeded demo account: {email} / {password}")
