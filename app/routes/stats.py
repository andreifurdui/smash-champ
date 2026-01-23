"""Statistics routes."""
from flask import Blueprint, render_template, request, flash
from flask_login import login_required
from app.services import stats as stats_service
from app.services.elo import get_elo_leaderboard, get_user_elo_history
from app.models import User, Tournament

bp = Blueprint('stats', __name__, url_prefix='/stats')


@bp.route('/')
@login_required
def leaderboard():
    """Global leaderboard and hall of fame."""
    leaderboard = stats_service.get_global_leaderboard()
    elo_leaderboard = get_elo_leaderboard()
    winners = stats_service.get_tournament_winners()

    return render_template('stats/leaderboard.html',
                         leaderboard=leaderboard,
                         elo_leaderboard=elo_leaderboard,
                         winners=winners)


@bp.route('/user/<int:user_id>')
@login_required
def user_stats(user_id):
    """Individual user statistics page."""
    from app.services.match import get_user_stats, get_user_recent_matches
    from app.models import EloHistory

    user = User.query.get_or_404(user_id)
    stats = get_user_stats(user_id)
    tournament_history = stats_service.get_user_tournament_history(user_id)
    recent_matches = get_user_recent_matches(user_id, limit=10)
    elo_history = get_user_elo_history(user_id, limit=5)

    # ELO changes for recent matches
    match_ids = [m.id for m in recent_matches]
    elo_for_matches = EloHistory.query.filter(
        EloHistory.user_id == user_id,
        EloHistory.match_id.in_(match_ids)
    ).all() if match_ids else []
    elo_by_match = {e.match_id: e.elo_change for e in elo_for_matches}

    return render_template('stats/user.html',
                         user=user,
                         stats=stats,
                         tournament_history=tournament_history,
                         recent_matches=recent_matches,
                         elo_history=elo_history,
                         elo_by_match=elo_by_match)


@bp.route('/head-to-head')
@login_required
def head_to_head():
    """H2H comparison tool."""
    user1_id = request.args.get('user1', type=int)
    user2_id = request.args.get('user2', type=int)

    all_users = User.query.order_by(User.username).all()

    h2h_data = None
    if user1_id and user2_id:
        if user1_id == user2_id:
            flash('Please select two different players', 'warning')
        else:
            h2h_data = stats_service.get_head_to_head(user1_id, user2_id)

    return render_template('stats/head_to_head.html',
                         all_users=all_users,
                         h2h_data=h2h_data,
                         user1_id=user1_id,
                         user2_id=user2_id)


@bp.route('/matches')
@login_required
def matches():
    """Match history browser."""
    tournament_id = request.args.get('tournament', type=int)
    user_id = request.args.get('user', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 25

    offset = (page - 1) * per_page
    matches, total = stats_service.get_match_history(
        tournament_id=tournament_id,
        user_id=user_id,
        limit=per_page,
        offset=offset
    )

    # For filter dropdowns
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    users = User.query.order_by(User.username).all()

    return render_template('stats/matches.html',
                         matches=matches,
                         total=total,
                         page=page,
                         per_page=per_page,
                         tournaments=tournaments,
                         users=users,
                         current_tournament=tournament_id,
                         current_user_filter=user_id)
