from datetime import datetime

from app.extensions import db


class Registration(db.Model):
    """Registration model linking users to tournaments with stats."""
    __tablename__ = 'registrations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)

    # Seeding and grouping
    seed = db.Column(db.Integer, nullable=True)
    group_number = db.Column(db.Integer, nullable=True)

    # Group stage statistics
    group_points = db.Column(db.Integer, default=0, nullable=False)  # 2 for win, 1 for loss, 0 for walkover loss
    group_position = db.Column(db.Integer, nullable=True)
    sets_won = db.Column(db.Integer, default=0, nullable=False)
    sets_lost = db.Column(db.Integer, default=0, nullable=False)
    points_won = db.Column(db.Integer, default=0, nullable=False)
    points_lost = db.Column(db.Integer, default=0, nullable=False)

    # Playoff tracking
    eliminated = db.Column(db.Boolean, default=False, nullable=False)
    final_position = db.Column(db.Integer, nullable=True)

    registered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='registrations')
    tournament = db.relationship('Tournament', back_populates='registrations')

    # Unique constraint - user can only register once per tournament
    __table_args__ = (
        db.UniqueConstraint('user_id', 'tournament_id', name='unique_user_tournament'),
    )

    @property
    def set_difference(self):
        """Calculate set difference (won - lost)."""
        return self.sets_won - self.sets_lost

    @property
    def point_difference(self):
        """Calculate point difference (won - lost)."""
        return self.points_won - self.points_lost

    def __repr__(self):
        return f'<Registration user={self.user_id} tournament={self.tournament_id}>'
