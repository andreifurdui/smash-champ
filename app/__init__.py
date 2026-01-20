import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template

from app.config import config
from app.extensions import db, login_manager, migrate


def create_app(config_name='default'):
    """Application factory."""
    app = Flask(__name__)
    config_class = config[config_name]
    app.config.from_object(config_class)

    # Call config-specific initialization if available
    if hasattr(config_class, 'init_app'):
        config_class.init_app(app)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # User loader for Flask-Login
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes import auth, main, admin, tournament, match, stats
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(tournament.bp)
    app.register_blueprint(match.bp)
    app.register_blueprint(stats.bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'Server Error: {error}')
        return render_template('errors/500.html'), 500

    # Logging setup for production
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler(
            'logs/smash.log', maxBytes=10240, backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('.smash startup')

    return app
