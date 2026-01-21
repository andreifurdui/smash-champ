"""Admin forms for user and tournament management."""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError
from app.models.user import User


class UserEditForm(FlaskForm):
    """Admin form for editing user profiles."""
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=20, message='Username must be 3-20 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    tagline = TextAreaField('Tagline', validators=[
        Optional(),
        Length(max=100, message='Tagline must be 100 characters or less')
    ])
    avatar_path = SelectField('Avatar', validators=[Optional()])

    def __init__(self, original_username, original_email, *args, **kwargs):
        """Store original values to allow keeping them."""
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        """Check if username is taken (allow keeping current username)."""
        if username.data != self.original_username:
            # Check allowed characters
            if not username.data.replace('_', '').isalnum():
                raise ValidationError('Username can only contain letters, numbers, and underscores.')

            # Check uniqueness
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('This username is already taken.')

    def validate_email(self, email):
        """Check if email is taken (allow keeping current email)."""
        if email.data.lower() != self.original_email.lower():
            user = User.query.filter_by(email=email.data.lower()).first()
            if user:
                raise ValidationError('This email is already registered.')


class TournamentEditForm(FlaskForm):
    """Admin form for editing tournament details."""
    name = StringField('Tournament Name', validators=[
        DataRequired(),
        Length(min=3, max=128, message='Tournament name must be 3-128 characters')
    ])
    description = TextAreaField('Description (Optional)', validators=[
        Optional(),
        Length(max=500, message='Description must be 500 characters or less')
    ])
