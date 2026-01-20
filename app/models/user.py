import random
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    """User model for authentication and player profiles."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar_path = db.Column(db.String(256), nullable=True)
    tagline = db.Column(db.String(100), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    registrations = db.relationship('Registration', back_populates='user', lazy='dynamic')
    tournament_wins = db.relationship('TournamentWinner', back_populates='user', lazy='dynamic')

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def display_tagline(self):
        """Return tagline or a random default."""
        if self.tagline:
            return self.tagline
        from app.utils.defaults import DEFAULT_TAGLINES
        random.seed(self.id)
        return random.choice(DEFAULT_TAGLINES)

    @property
    def display_avatar(self):
        """Return avatar path or a random default."""
        if self.avatar_path:
            return self.avatar_path
        from app.utils.avatars import get_random_default_avatar
        return get_random_default_avatar(self.id)

    def __repr__(self):
        return f'<User {self.username}>'
