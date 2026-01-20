"""
Match service layer.
Handles match queries, statistics, and user-specific match operations.
"""
from typing import Optional, List
from sqlalchemy import or_, and_
from app.extensions import db
from app.models import Match, User, MatchStatus, MatchPhase


def get_user_next_match(user_id: int) -> Optional[Match]:
    """
    Get user's next scheduled match (earliest by scheduled_at or created_at).

    Args:
        user_id: User ID

    Returns:
        Match object or None if no upcoming matches
    """
    return Match.query.filter(
        or_(Match.player1_id == user_id, Match.player2_id == user_id),
        Match.status == MatchStatus.SCHEDULED.value
    ).options(
        db.joinedload(Match.player1),
        db.joinedload(Match.player2),
        db.joinedload(Match.tournament)
    ).order_by(
        Match.scheduled_at.asc().nullslast(),  # Scheduled matches first
        Match.created_at.asc()                  # Then by creation
    ).first()


def get_user_recent_matches(user_id: int, limit: int = 5) -> List[Match]:
    """
    Get user's most recent confirmed matches.

    Args:
        user_id: User ID
        limit: Number of matches to return (default 5)

    Returns:
        List of Match objects with results
    """
    return Match.query.filter(
        or_(Match.player1_id == user_id, Match.player2_id == user_id),
        Match.status == MatchStatus.CONFIRMED.value,
        Match.winner_id.isnot(None)
    ).options(
        db.joinedload(Match.player1),
        db.joinedload(Match.player2),
        db.joinedload(Match.tournament)
    ).order_by(Match.played_at.desc()).limit(limit).all()


def get_user_pending_confirmations(user_id: int) -> List[Match]:
    """
    Get matches awaiting confirmation from user.

    Args:
        user_id: User ID

    Returns:
        List of matches where user is opponent and confirmation needed
    """
    return Match.query.filter(
        Match.status == MatchStatus.PENDING_CONFIRMATION.value,
        or_(
            # User is player2 and player1 submitted
            and_(Match.player2_id == user_id, Match.submitted_by_id == Match.player1_id),
            # User is player1 and player2 submitted
            and_(Match.player1_id == user_id, Match.submitted_by_id == Match.player2_id)
        )
    ).options(
        db.joinedload(Match.player1),
        db.joinedload(Match.player2),
        db.joinedload(Match.tournament)
    ).order_by(Match.submitted_at.asc()).all()


def get_global_recent_matches(limit: int = 10) -> List[Match]:
    """
    Get most recent confirmed matches across all users.

    Args:
        limit: Number of matches to return (default 10)

    Returns:
        List of Match objects with results
    """
    return Match.query.filter(
        Match.status == MatchStatus.CONFIRMED.value,
        Match.winner_id.isnot(None)
    ).options(
        db.joinedload(Match.player1),
        db.joinedload(Match.player2),
        db.joinedload(Match.tournament)
    ).order_by(Match.played_at.desc()).limit(limit).all()


def get_user_stats(user_id: int) -> dict:
    """
    Calculate user's overall match statistics.

    Args:
        user_id: User ID

    Returns:
        Dictionary with wins, losses, total, win_rate
    """
    # Count wins
    wins = Match.query.filter(
        Match.winner_id == user_id,
        Match.status == MatchStatus.CONFIRMED.value
    ).count()

    # Count losses (played and confirmed but didn't win)
    losses = Match.query.filter(
        or_(Match.player1_id == user_id, Match.player2_id == user_id),
        Match.status == MatchStatus.CONFIRMED.value,
        Match.winner_id.isnot(None),
        Match.winner_id != user_id
    ).count()

    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0

    return {
        'wins': wins,
        'losses': losses,
        'total': total,
        'win_rate': round(win_rate, 1)
    }
