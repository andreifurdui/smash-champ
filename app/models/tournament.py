from datetime import datetime
from enum import Enum

from app.extensions import db


class TournamentStatus(str, Enum):
    """Tournament status enum."""
    REGISTRATION = 'registration'
    GROUP_STAGE = 'group_stage'
    PLAYOFFS = 'playoffs'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


class PlayoffFormat(str, Enum):
    """Playoff format enum."""
    GAUNTLET = 'gauntlet'


class Tournament(db.Model):
    """Tournament model for championship events."""
    __tablename__ = 'tournaments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default=TournamentStatus.REGISTRATION.value, nullable=False)
    phase = db.Column(db.Integer, default=0, nullable=False)  # For tracking sub-phases
    playoff_format = db.Column(db.String(20), default=PlayoffFormat.GAUNTLET.value, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    registrations = db.relationship('Registration', back_populates='tournament', lazy='dynamic',
                                   cascade='all, delete-orphan')
    matches = db.relationship('Match', back_populates='tournament', lazy='dynamic',
                             cascade='all, delete-orphan')
    winners = db.relationship('TournamentWinner', back_populates='tournament', lazy='dynamic',
                             cascade='all, delete-orphan')

    @property
    def is_registration_open(self):
        """Check if registration is open."""
        return self.status == TournamentStatus.REGISTRATION.value

    @property
    def is_active(self):
        """Check if tournament is in progress."""
        return self.status in (TournamentStatus.GROUP_STAGE.value, TournamentStatus.PLAYOFFS.value)

    @property
    def is_completed(self):
        """Check if tournament has ended."""
        return self.status == TournamentStatus.COMPLETED.value

    @property
    def player_count(self):
        """Get number of registered players."""
        return self.registrations.count()

    def __repr__(self):
        return f'<Tournament {self.name}>'
