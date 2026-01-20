from datetime import datetime
from enum import Enum

from app.extensions import db


class MatchPhase(str, Enum):
    """Match phase enum."""
    GROUP = 'group'
    PLAYOFF = 'playoff'


class MatchStatus(str, Enum):
    """Match status enum."""
    SCHEDULED = 'scheduled'
    PENDING_CONFIRMATION = 'pending_confirmation'
    CONFIRMED = 'confirmed'
    DISPUTED = 'disputed'
    CANCELLED = 'cancelled'
    WALKOVER = 'walkover'


class Match(db.Model):
    """Match model for individual games between players."""
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    player1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Match context
    phase = db.Column(db.String(20), default=MatchPhase.GROUP.value, nullable=False)
    group_number = db.Column(db.Integer, nullable=True)  # For group stage matches
    fixture_number = db.Column(db.Integer, nullable=True)  # Order within group (1=first fixture, 2=return fixture)
    bracket_round = db.Column(db.Integer, nullable=True)  # For playoff matches
    bracket_position = db.Column(db.Integer, nullable=True)  # Position within bracket round

    # Scheduling
    scheduled_at = db.Column(db.DateTime, nullable=True)
    played_at = db.Column(db.DateTime, nullable=True)

    # Status and result
    status = db.Column(db.String(20), default=MatchStatus.SCHEDULED.value, nullable=False)
    winner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Confirmation flow
    submitted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    confirmed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    submitted_at = db.Column(db.DateTime, nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    tournament = db.relationship('Tournament', back_populates='matches')
    player1 = db.relationship('User', foreign_keys=[player1_id], backref='matches_as_player1')
    player2 = db.relationship('User', foreign_keys=[player2_id], backref='matches_as_player2')
    winner = db.relationship('User', foreign_keys=[winner_id], backref='matches_won')
    submitted_by = db.relationship('User', foreign_keys=[submitted_by_id], backref='matches_submitted')
    confirmed_by = db.relationship('User', foreign_keys=[confirmed_by_id], backref='matches_confirmed')
    set_scores = db.relationship('SetScore', back_populates='match', lazy='dynamic',
                                 cascade='all, delete-orphan', order_by='SetScore.set_number')

    @property
    def is_group_match(self):
        """Check if this is a group stage match."""
        return self.phase == MatchPhase.GROUP.value

    @property
    def is_playoff_match(self):
        """Check if this is a playoff match."""
        return self.phase == MatchPhase.PLAYOFF.value

    @property
    def is_pending_confirmation(self):
        """Check if match is awaiting opponent confirmation."""
        return self.status == MatchStatus.PENDING_CONFIRMATION.value

    @property
    def is_confirmed(self):
        """Check if match result is confirmed."""
        return self.status == MatchStatus.CONFIRMED.value

    def get_opponent(self, user_id):
        """Get the opponent for a given user in this match."""
        if self.player1_id == user_id:
            return self.player2
        elif self.player2_id == user_id:
            return self.player1
        return None

    def __repr__(self):
        return f'<Match {self.id}: {self.player1_id} vs {self.player2_id}>'


class SetScore(db.Model):
    """Set score model for individual sets within a match."""
    __tablename__ = 'set_scores'

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    set_number = db.Column(db.Integer, nullable=False)  # 1, 2, or 3
    player1_score = db.Column(db.Integer, nullable=False)
    player2_score = db.Column(db.Integer, nullable=False)

    # Relationships
    match = db.relationship('Match', back_populates='set_scores')

    # Unique constraint - one score per set per match
    __table_args__ = (
        db.UniqueConstraint('match_id', 'set_number', name='unique_match_set'),
    )

    @property
    def winner_is_player1(self):
        """Check if player1 won this set."""
        return self.player1_score > self.player2_score

    @property
    def is_valid_score(self):
        """Validate table tennis scoring rules."""
        high = max(self.player1_score, self.player2_score)
        low = min(self.player1_score, self.player2_score)

        # Regular win: first to 11 with at least 2 point lead
        if high >= 11 and high - low >= 2:
            return True
        return False

    def __repr__(self):
        return f'<SetScore match={self.match_id} set={self.set_number} ({self.player1_score}-{self.player2_score})>'
