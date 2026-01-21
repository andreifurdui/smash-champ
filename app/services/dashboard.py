"""
Dashboard service layer.
Aggregates data from multiple services for dashboard display.
"""
from typing import Optional
from app.services import match, tournament


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
            'global_activity': [Match]
        }
    """
    return {
        'upcoming_matches': match.get_user_upcoming_matches(user_id, limit=3),
        'recent_matches': match.get_user_recent_matches(user_id, limit=5),
        'pending_confirmations': match.get_user_pending_confirmations(user_id),
        'active_tournaments': tournament.get_user_tournaments(user_id),
        'stats': match.get_user_stats(user_id),
        'global_activity': match.get_global_recent_matches(limit=10)
    }
