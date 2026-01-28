"""
Dashboard service layer.
Aggregates data from multiple services for dashboard display.
"""
from datetime import datetime, timedelta
from typing import Optional
from app.services import match, tournament
from app.services.elo import get_elo_leaderboard, get_user_elo_history
from app.models import User, MatchStatus, EloHistory


def get_dashboard_data(user_id: int) -> dict:
    """
    Get all dashboard data for user in single function.

    Args:
        user_id: User ID

    Returns:
        Dictionary with all dashboard components:
        {
            'upcoming_matches': [Match],
            'recent_matches': [Match],
            'pending_confirmations': [Match],
            'active_tournaments': [Tournament],
            'stats': {'wins': int, 'losses': int, 'total': int, 'win_rate': float},
            'global_activity': [Match],
            'elo_rating': int,
            'pending_free_matches': [Match]
        }
    """
    user = User.query.get(user_id)

    # Get pending free matches (matches awaiting confirmation from this user)
    pending_free = match.get_user_free_matches(
        user_id, status=MatchStatus.PENDING_CONFIRMATION.value, limit=5
    )
    # Filter to only show those where user needs to confirm (not ones they submitted)
    pending_free = [m for m in pending_free if m.submitted_by_id != user_id]

    # Get recent matches and global activity
    recent_matches = match.get_user_recent_matches(user_id, limit=5)
    global_activity = match.get_global_recent_matches(limit=10)

    # ELO changes for user's recent matches (both players)
    match_ids = [m.id for m in recent_matches]
    elo_records = EloHistory.query.filter(
        EloHistory.match_id.in_(match_ids)
    ).all() if match_ids else []
    elo_by_match = {}
    for e in elo_records:
        if e.match_id not in elo_by_match:
            elo_by_match[e.match_id] = {}
        elo_by_match[e.match_id][e.user_id] = e.elo_change

    # ELO changes for global activity (both players)
    global_match_ids = [m.id for m in global_activity]
    global_elo_records = EloHistory.query.filter(
        EloHistory.match_id.in_(global_match_ids)
    ).all() if global_match_ids else []
    global_elo_by_match = {}
    for e in global_elo_records:
        if e.match_id not in global_elo_by_match:
            global_elo_by_match[e.match_id] = {}
        global_elo_by_match[e.match_id][e.user_id] = e.elo_change

    # ELO history for chart (reversed to oldest first)
    elo_history_raw = get_user_elo_history(user_id, limit=20)
    elo_history = [
        {'rating': h.elo_after, 'date': h.created_at.strftime('%m/%d')}
        for h in reversed(elo_history_raw)
    ] if elo_history_raw else []

    # Calculate weekly ELO change (Sunday-starting week)
    today = datetime.utcnow()
    days_since_sunday = (today.weekday() + 1) % 7  # Monday=0, so Sunday=6 -> 0
    week_start = (today - timedelta(days=days_since_sunday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    weekly_elo_records = EloHistory.query.filter(
        EloHistory.user_id == user_id,
        EloHistory.created_at >= week_start
    ).all()
    weekly_elo_change = sum(e.elo_change for e in weekly_elo_records)

    return {
        'upcoming_matches': match.get_user_upcoming_matches(user_id, limit=3),
        'recent_matches': recent_matches,
        'pending_confirmations': match.get_user_pending_confirmations(user_id),
        'active_tournaments': tournament.get_user_tournaments(user_id),
        'stats': match.get_user_stats(user_id),
        'global_activity': global_activity,
        'elo_rating': user.elo_rating if user else 1200,
        'pending_free_matches': pending_free,
        'elo_by_match': elo_by_match,
        'global_elo_by_match': global_elo_by_match,
        'elo_leaderboard': get_elo_leaderboard(limit=5),
        'elo_history': elo_history,
        'weekly_elo_change': weekly_elo_change
    }
