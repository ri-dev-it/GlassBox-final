"""
Application factory for the Explainable AI Loan Approval backend.
"""

from flask import Flask
from flask_cors import CORS

from app.config import get_config
from app.extensions import db, bcrypt, migrate


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    CORS(app, origins=app.config.get("CORS_ORIGINS", "*"))

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    # Register routes before create_all: route imports register all model
    # metadata, including document records, with SQLAlchemy.
    register_blueprints(app)

    # SQLite is the zero-configuration local-development store.  Production
    # and MySQL deployments continue to use Flask-Migrate as usual.
    if app.config.get("DEBUG") and app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:"):
        with app.app_context():
            db.create_all()

    register_error_handlers(app)

    return app


def register_blueprints(app: Flask) -> None:
    from app.routes.health import health_bp
    from app.routes.auth import auth_bp
    from app.routes.applicants import applicants_bp
    from app.routes.predictions import predictions_bp
    from app.routes.explanations import explanations_bp
    from app.routes.counterfactuals import counterfactuals_bp
    from app.routes.fairness import fairness_bp
    from app.routes.analytics import analytics_bp
    from app.routes.documents import documents_bp
    from app.routes.merchants import merchants_bp
    from app.routes.portfolio import portfolio_bp
    from app.routes.models import models_bp
    from app.routes.admin_reviews import admin_reviews_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(applicants_bp, url_prefix="/api")
    app.register_blueprint(predictions_bp, url_prefix="/api")
    app.register_blueprint(explanations_bp, url_prefix="/api")
    app.register_blueprint(counterfactuals_bp, url_prefix="/api")
    app.register_blueprint(fairness_bp, url_prefix="/api")
    app.register_blueprint(analytics_bp, url_prefix="/api")
    app.register_blueprint(documents_bp, url_prefix="/api")
    app.register_blueprint(merchants_bp, url_prefix="/api")
    app.register_blueprint(portfolio_bp, url_prefix="/api")
    app.register_blueprint(models_bp, url_prefix="/api")
    app.register_blueprint(admin_reviews_bp, url_prefix="/api")


def register_error_handlers(app: Flask) -> None:
    from flask import jsonify

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify({"error": "Internal server error"}), 500
