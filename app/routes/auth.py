"""Authentication routes for registration, login, logout, and profile management."""

import os
import uuid
from pathlib import Path
from PIL import Image
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.user import User
from app.forms.auth import RegistrationForm, LoginForm, ProfileEditForm, PasswordChangeForm
from app.utils.defaults import get_random_tagline, get_random_avatar

bp = Blueprint('auth', __name__, url_prefix='/auth')


def save_avatar(file, username):
    """
    Save uploaded avatar image.
    - Resize to 200x200
    - Optimize with quality=85
    - Save to /static/avatars/ with format: username_uuid8.ext
    - Return relative path for database storage
    """
    # Create avatars directory if it doesn't exist
    avatars_dir = Path('app/static/avatars')
    avatars_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{secure_filename(username)}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = avatars_dir / filename

    # Open and process image
    img = Image.open(file)

    # Convert RGBA to RGB if needed (for JPEG compatibility)
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background

    # Resize to 200x200
    img = img.resize((200, 200), Image.Resampling.LANCZOS)

    # Save with optimization
    img.save(filepath, quality=85, optimize=True)

    # Return path for database (relative to static)
    return f'/static/avatars/{filename}'


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Create new user
        user = User(
            email=form.email.data.lower(),
            username=form.username.data
        )
        user.set_password(form.password.data)

        # Handle tagline
        if form.tagline.data and form.tagline.data.strip():
            user.tagline = form.tagline.data.strip()
        else:
            user.tagline = get_random_tagline()

        # Handle avatar upload
        if form.avatar.data:
            avatar_path = save_avatar(form.avatar.data, user.username)
            user.avatar_path = avatar_path
        else:
            user.avatar_path = get_random_avatar()

        # Save to database
        db.session.add(user)
        db.session.commit()

        # Auto-login after registration
        login_user(user)

        flash(f'Welcome to .smash, {user.username}! Your account has been created.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/register.html', form=form)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        # Find user by email (case-insensitive)
        user = User.query.filter_by(email=form.email.data.lower()).first()

        # Validate credentials
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash(f'Welcome back, {user.username}!', 'success')

            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'error')

    return render_template('auth/login.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    """User logout."""
    username = current_user.username
    logout_user()
    flash(f'Goodbye, {username}! You have been logged out.', 'info')
    return redirect(url_for('main.landing'))


@bp.route('/profile')
@login_required
def profile():
    """View user profile."""
    return render_template('auth/profile.html', user=current_user)


@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    """Edit user profile."""
    form = ProfileEditForm(
        original_username=current_user.username,
        original_email=current_user.email
    )

    if form.validate_on_submit():
        # Update basic fields
        current_user.username = form.username.data
        current_user.email = form.email.data.lower()

        # Update tagline
        if form.tagline.data and form.tagline.data.strip():
            current_user.tagline = form.tagline.data.strip()

        # Handle avatar upload
        if form.avatar.data:
            # Delete old custom avatar if exists
            if current_user.avatar_path and current_user.avatar_path.startswith('/static/avatars/'):
                old_path = Path('app') / current_user.avatar_path.lstrip('/')
                if old_path.exists():
                    try:
                        old_path.unlink()
                    except Exception:
                        pass  # Ignore errors deleting old avatar

            # Save new avatar
            avatar_path = save_avatar(form.avatar.data, current_user.username)
            current_user.avatar_path = avatar_path

        # Save changes
        db.session.commit()

        flash('Your profile has been updated successfully!', 'success')
        return redirect(url_for('auth.profile'))

    elif request.method == 'GET':
        # Pre-populate form with current values
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.tagline.data = current_user.tagline

    return render_template('auth/profile_edit.html', form=form)


@bp.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password."""
    form = PasswordChangeForm()

    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'error')
        else:
            # Set new password
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Your password has been changed successfully!', 'success')
            return redirect(url_for('auth.profile'))

    return render_template('auth/change_password.html', form=form)
