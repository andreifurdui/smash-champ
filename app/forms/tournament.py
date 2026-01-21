"""Tournament management forms."""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Optional
from app.models import PlayoffFormat


class TournamentCreateForm(FlaskForm):
    """Tournament creation form."""
    name = StringField('Tournament Name', validators=[
        DataRequired(),
        Length(min=3, max=128, message='Tournament name must be 3-128 characters')
    ])
    description = TextAreaField('Description (Optional)', validators=[
        Optional(),
        Length(max=500, message='Description must be 500 characters or less')
    ])
    playoff_format = SelectField('Playoff Format',
        choices=[
            (PlayoffFormat.GAUNTLET.value, 'Gauntlet')
        ],
        default=PlayoffFormat.GAUNTLET.value,
        validators=[DataRequired()]
    )
    sets_to_win = SelectField('Match Format',
        choices=[
            (2, 'Best of 3 (first to 2 sets)'),
            (1, 'Best of 1 (single set)')
        ],
        default=2,
        coerce=int,
        validators=[DataRequired()]
    )
