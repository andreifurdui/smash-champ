"""Statistics and leaderboard service."""
from sqlalchemy import or_, and_, func
from app.extensions import db
from app.models import User, Match, Tournament, Registration, TournamentWinner, MatchStatus, SetScore


def get_user_streak(user_id: int) -> dict:
    """
    Calculate current win/loss streak for user.

    Only includes CONFIRMED matches (walkovers excluded - only real games count).

    Returns:
        {
            'type': 'win' | 'loss' | None,
            'count': int,
            'matches': [Match]  # matches in streak
        }
    """
    # Get recent confirmed matches (exclude walkovers)
    matches = Match.query.filter(
        Match.status == MatchStatus.CONFIRMED.value,
        or_(Match.player1_id == user_id, Match.player2_id == user_id)
    ).options(
        db.joinedload(Match.player1),
        db.joinedload(Match.player2)
    ).order_by(Match.played_at.desc()).limit(20).all()

    if not matches:
        return {'type': None, 'count': 0, 'matches': []}

    # Determine streak type from most recent match
    first_match = matches[0]
    is_win = first_match.winner_id == user_id
    streak_type = 'win' if is_win else 'loss'

    # Count consecutive matches of same result
    streak_matches = []
    for match in matches:
        match_is_win = match.winner_id == user_id
        if match_is_win == is_win:
            streak_matches.append(match)
        else:
            break

    return {
        'type': streak_type,
        'count': len(streak_matches),
        'matches': streak_matches
    }


def get_global_leaderboard(limit: int = 50) -> list[dict]:
    """
    All-time leaderboard sorted by wins, then win rate.

    Returns:
        List of dicts with: user, wins, losses, total, win_rate, rank
    """
    from app.services.match import get_user_stats

    users = User.query.all()
    leaderboard = []

    for user in users:
        stats = get_user_stats(user.id)
        if stats['total'] > 0:  # Only users with matches
            leaderboard.append({
                'user': user,
                'rank': 0,  # Assigned after sorting
                **stats
            })

    # Sort by wins DESC, then win_rate DESC
    leaderboard.sort(key=lambda x: (x['wins'], x['win_rate']), reverse=True)

    # Assign ranks
    for i, entry in enumerate(leaderboard[:limit], 1):
        entry['rank'] = i

    return leaderboard[:limit]


def get_tournament_winners() -> list[TournamentWinner]:
    """
    Hall of fame - all tournament winners.

    Returns:
        TournamentWinner records with user and tournament eager loaded
    """
    return TournamentWinner.query.options(
        db.joinedload(TournamentWinner.user),
        db.joinedload(TournamentWinner.tournament)
    ).filter(TournamentWinner.position <= 3).order_by(
        TournamentWinner.tournament_id.desc(),
        TournamentWinner.position.asc()
    ).all()


def get_user_tournament_history(user_id: int) -> list[dict]:
    """
    User's tournament participation history.

    Returns:
        List of dicts with: tournament, registration, match_wins, match_losses
    """
    registrations = Registration.query.filter_by(user_id=user_id).options(
        db.joinedload(Registration.tournament)
    ).order_by(Registration.tournament_id.desc()).all()

    history = []
    for reg in registrations:
        # Count wins in this tournament
        wins = Match.query.filter(
            Match.tournament_id == reg.tournament_id,
            Match.winner_id == user_id,
            Match.status == MatchStatus.CONFIRMED.value
        ).count()

        # Count losses in this tournament
        losses = Match.query.filter(
            or_(Match.player1_id == user_id, Match.player2_id == user_id),
            Match.tournament_id == reg.tournament_id,
            Match.status == MatchStatus.CONFIRMED.value,
            Match.winner_id.isnot(None),
            Match.winner_id != user_id
        ).count()

        history.append({
            'tournament': reg.tournament,
            'registration': reg,
            'match_wins': wins,
            'match_losses': losses
        })

    return history


def get_head_to_head(user1_id: int, user2_id: int) -> dict:
    """
    H2H statistics between two players.

    Returns:
        Dict with: user1, user2, user1_wins, user2_wins, matches, etc.
    """
    user1 = User.query.get_or_404(user1_id)
    user2 = User.query.get_or_404(user2_id)

    # Get all matches between these two players
    matches = Match.query.filter(
        Match.status == MatchStatus.CONFIRMED.value,
        or_(
            and_(Match.player1_id == user1_id, Match.player2_id == user2_id),
            and_(Match.player1_id == user2_id, Match.player2_id == user1_id)
        )
    ).options(
        db.joinedload(Match.player1),
        db.joinedload(Match.player2)
    ).order_by(Match.played_at.desc()).all()

    user1_wins = sum(1 for m in matches if m.winner_id == user1_id)
    user2_wins = sum(1 for m in matches if m.winner_id == user2_id)

    return {
        'user1': user1,
        'user2': user2,
        'user1_wins': user1_wins,
        'user2_wins': user2_wins,
        'total_matches': len(matches),
        'matches': matches
    }


def get_match_history(tournament_id: int = None, user_id: int = None,
                      limit: int = 50, offset: int = 0) -> tuple[list[Match], int]:
    """
    Filterable match history with pagination.

    Returns:
        (matches, total_count)
    """
    query = Match.query.filter(Match.status == MatchStatus.CONFIRMED.value)

    # Apply filters
    if tournament_id:
        query = query.filter_by(tournament_id=tournament_id)
    if user_id:
        query = query.filter(
            or_(Match.player1_id == user_id, Match.player2_id == user_id)
        )

    # Get total count for pagination
    total = query.count()

    # Get paginated results
    matches = query.options(
        db.joinedload(Match.player1),
        db.joinedload(Match.player2),
        db.joinedload(Match.tournament)
    ).order_by(Match.played_at.desc()).limit(limit).offset(offset).all()

    return matches, total
