import os
from pathlib import Path

basedir = Path(__file__).parent.parent


class BaseConfig:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    # App-specific settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    TAGLINE_MAX_LENGTH = 100
    SETS_TO_WIN = 2  # Best of 3
    POINTS_TO_WIN_SET = 11
    MIN_POINT_LEAD = 2  # Must win by 2


class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{basedir / "instance" / "smash.db"}'
    )


class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SECRET_KEY = os.environ.get('SECRET_KEY')

    @classmethod
    def init_app(cls, app):
        assert cls.SECRET_KEY != 'dev-secret-key-change-in-production', \
            'SECRET_KEY must be set in production'
        assert cls.SQLALCHEMY_DATABASE_URI, \
            'DATABASE_URL must be set in production'


class TestingConfig(BaseConfig):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
