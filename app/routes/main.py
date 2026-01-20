"""Main routes for landing page and dashboard."""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_required
from app.services.dashboard import get_dashboard_data
from app.services.tournament import calculate_standings

bp = Blueprint('main', __name__)


@bp.route('/')
def landing():
    """Landing page - redirect to dashboard if authenticated."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('main/landing.html')


@bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with tournaments, matches, and stats."""
    data = get_dashboard_data(current_user.id)
    return render_template('main/dashboard.html',
                         calculate_standings=calculate_standings,
                         **data)
