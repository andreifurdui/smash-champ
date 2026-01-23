"""Challenge form for creating free matches."""

from flask_wtf import FlaskForm
from wtforms import SelectField
from wtforms.validators import DataRequired


class ChallengeForm(FlaskForm):
    """Form to challenge another player to a free match."""
    opponent_id = SelectField('Opponent', validators=[DataRequired()], coerce=int)
