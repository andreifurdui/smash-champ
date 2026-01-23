from datetime import datetime

from app.extensions import db


class EloHistory(db.Model):
    """ELO rating history for tracking changes per match."""
    __tablename__ = 'elo_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    elo_before = db.Column(db.Integer, nullable=False)
    elo_after = db.Column(db.Integer, nullable=False)
    elo_change = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship('User', backref=db.backref('elo_history', lazy='dynamic'))
    match = db.relationship('Match', backref=db.backref('elo_changes', lazy='dynamic'))

    # Unique constraint - one ELO change per user per match
    __table_args__ = (
        db.UniqueConstraint('user_id', 'match_id', name='unique_user_match_elo'),
    )

    def __repr__(self):
        return f'<EloHistory user={self.user_id} match={self.match_id} {self.elo_before}->{self.elo_after}>'
