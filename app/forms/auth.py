"""Authentication forms for user registration, login, and profile management."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import StringField, PasswordField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from app.models.user import User


class RegistrationForm(FlaskForm):
    """User registration form."""
    email = StringField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=20, message='Username must be 3-20 characters')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    tagline = TextAreaField('Tagline (Optional)', validators=[
        Optional(),
        Length(max=100, message='Tagline must be 100 characters or less')
    ])
    avatar = FileField('Avatar (Optional)', validators=[
        Optional(),
        FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'], 'Images only!'),
        FileSize(max_size=16777216, message='File size must not exceed 16MB')
    ])

    def validate_email(self, email):
        """Check if email already exists."""
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            raise ValidationError('This email is already registered. Please use a different email.')

    def validate_username(self, username):
        """Check if username already exists and contains only allowed characters."""
        # Check allowed characters
        if not username.data.replace('_', '').isalnum():
            raise ValidationError('Username can only contain letters, numbers, and underscores.')

        # Check uniqueness
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('This username is already taken. Please choose a different one.')


class LoginForm(FlaskForm):
    """User login form."""
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired()
    ])
    remember_me = BooleanField('Remember Me')


class ProfileEditForm(FlaskForm):
    """Profile editing form."""
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
    avatar = FileField('Avatar', validators=[
        Optional(),
        FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'], 'Images only!'),
        FileSize(max_size=16777216, message='File size must not exceed 16MB')
    ])

    def __init__(self, original_username, original_email, *args, **kwargs):
        """Store original values to allow keeping them."""
        super(ProfileEditForm, self).__init__(*args, **kwargs)
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
                raise ValidationError('This username is already taken. Please choose a different one.')

    def validate_email(self, email):
        """Check if email is taken (allow keeping current email)."""
        if email.data.lower() != self.original_email.lower():
            user = User.query.filter_by(email=email.data.lower()).first()
            if user:
                raise ValidationError('This email is already registered. Please use a different email.')


class PasswordChangeForm(FlaskForm):
    """Password change form requiring current password."""
    current_password = PasswordField('Current Password', validators=[
        DataRequired()
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ])
