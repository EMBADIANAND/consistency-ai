from flask import Flask
from flask_cors import CORS
from .core.config import Settings
from .core.database import db
from .api.routes.health import health_bp
from .api.routes.goals import goals_bp
from .api.routes.auth import auth_bp
from .api.routes.life_rules import life_rules_bp
from .api.routes.daily_tasks import daily_tasks_bp
from .api.routes.checkins import checkins_bp

def create_app(settings: Settings | None = None) -> Flask:
    app = Flask(__name__)
    config = settings or Settings()
    app.config.from_mapping(
        SECRET_KEY=config.secret_key,
        SQLALCHEMY_DATABASE_URI=config.database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    CORS(app, origins=config.cors_origins)
    db.init_app(app)

    app.register_blueprint(health_bp, url_prefix="/api/v1")
    app.register_blueprint(goals_bp, url_prefix="/api/v1")
    app.register_blueprint(auth_bp, url_prefix="/api/v1")
    app.register_blueprint(life_rules_bp, url_prefix="/api/v1")
    app.register_blueprint(daily_tasks_bp, url_prefix="/api/v1")
    app.register_blueprint(checkins_bp, url_prefix="/api/v1")

    return app
