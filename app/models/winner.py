from datetime import datetime

from app.extensions import db


class TournamentWinner(db.Model):
    """Tournament winner model for tracking final standings."""
    __tablename__ = 'tournament_winners'

    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False)  # 1 = champion, 2 = runner-up, etc.
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    tournament = db.relationship('Tournament', back_populates='winners')
    user = db.relationship('User', back_populates='tournament_wins')

    # Unique constraint - one position per user per tournament
    __table_args__ = (
        db.UniqueConstraint('tournament_id', 'user_id', name='unique_tournament_user_winner'),
        db.UniqueConstraint('tournament_id', 'position', name='unique_tournament_position'),
    )

    def __repr__(self):
        return f'<TournamentWinner tournament={self.tournament_id} position={self.position} user={self.user_id}>'
