from flask import Flask

from app.config import config
from app.extensions import db, login_manager, migrate


def create_app(config_name='default'):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # User loader for Flask-Login
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints (placeholder for Phase 1+)
    # from app.routes import auth, main, tournament, match, admin, stats, api
    # app.register_blueprint(auth.bp)
    # etc.

    return app
