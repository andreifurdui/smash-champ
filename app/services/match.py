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


def get_user_upcoming_matches(user_id: int, limit: int = 3) -> List[Match]:
    """
    Get user's next N scheduled matches (ordered by scheduled_at or creation).

    Args:
        user_id: User ID
        limit: Number of matches to return (default 3)

    Returns:
        List of Match objects
    """
    return Match.query.filter(
        or_(Match.player1_id == user_id, Match.player2_id == user_id),
        Match.status == MatchStatus.SCHEDULED.value
    ).options(
        db.joinedload(Match.player1),
        db.joinedload(Match.player2),
        db.joinedload(Match.tournament)
    ).order_by(
        Match.scheduled_at.asc().nullslast(),
        Match.id.asc()  # Creation order = round order
    ).limit(limit).all()


def get_user_recent_matches(user_id: int, limit: int = 5) -> List[Match]:
    """
    Get user's most recent confirmed or walkover matches.

    Args:
        user_id: User ID
        limit: Number of matches to return (default 5)

    Returns:
        List of Match objects with results
    """
    return Match.query.filter(
        or_(Match.player1_id == user_id, Match.player2_id == user_id),
        Match.status.in_([MatchStatus.CONFIRMED.value, MatchStatus.WALKOVER.value]),
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
    Get most recent confirmed or walkover matches across all users.

    Args:
        limit: Number of matches to return (default 10)

    Returns:
        List of Match objects with results
    """
    return Match.query.filter(
        Match.status.in_([MatchStatus.CONFIRMED.value, MatchStatus.WALKOVER.value]),
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
    # Count wins (confirmed and walkover)
    wins = Match.query.filter(
        Match.winner_id == user_id,
        Match.status.in_([MatchStatus.CONFIRMED.value, MatchStatus.WALKOVER.value])
    ).count()

    # Count losses (played and confirmed/walkover but didn't win)
    losses = Match.query.filter(
        or_(Match.player1_id == user_id, Match.player2_id == user_id),
        Match.status.in_([MatchStatus.CONFIRMED.value, MatchStatus.WALKOVER.value]),
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


def submit_match_score(match_id: int, user_id: int, sets_data: list[dict]) -> Match:
    """
    Submit match score.

    Args:
        match_id: Match ID
        user_id: User submitting (must be participant)
        sets_data: List of dicts with player1_score, player2_score

    Returns:
        Updated Match object

    Raises:
        ValueError: If validation fails
    """
    from app.models import SetScore
    from datetime import datetime

    match = Match.query.get_or_404(match_id)

    # Validate user is participant
    if user_id not in (match.player1_id, match.player2_id):
        raise ValueError('You are not a participant in this match')

    # Validate match status
    if match.status != MatchStatus.SCHEDULED.value:
        raise ValueError(f'Cannot submit score for match in {match.status} status')

    # Get tournament's sets_to_win setting (default 2 for free matches)
    sets_to_win = match.tournament.sets_to_win if match.tournament else 2

    # Validate number of sets based on format
    if sets_to_win == 1:
        # Best-of-1: exactly 1 set
        if not sets_data or len(sets_data) != 1:
            raise ValueError('Best-of-1 match must have exactly 1 set')
    else:
        # Best-of-3: 2 or 3 sets
        if not sets_data or len(sets_data) < 2 or len(sets_data) > 3:
            raise ValueError('Best-of-3 match must have 2 or 3 sets')

    # Create SetScore records and determine winner
    player1_sets_won = 0
    player2_sets_won = 0

    for i, set_data in enumerate(sets_data):
        set_score = SetScore(
            match_id=match.id,
            set_number=i + 1,
            player1_score=set_data['player1_score'],
            player2_score=set_data['player2_score']
        )

        # Validate set score
        if not set_score.is_valid_score:
            raise ValueError(f'Set {i+1} has invalid score: {set_data["player1_score"]}-{set_data["player2_score"]}')

        # Count sets won
        if set_data['player1_score'] > set_data['player2_score']:
            player1_sets_won += 1
        else:
            player2_sets_won += 1

        db.session.add(set_score)

    # Determine winner based on sets_to_win
    if player1_sets_won >= sets_to_win:
        match.winner_id = match.player1_id
    elif player2_sets_won >= sets_to_win:
        match.winner_id = match.player2_id
    else:
        raise ValueError(f'No player won {sets_to_win} set(s)')

    # Update match status
    match.status = MatchStatus.PENDING_CONFIRMATION.value
    match.submitted_by_id = user_id
    match.submitted_at = datetime.utcnow()

    db.session.commit()
    return match


def confirm_match_score(match_id: int, user_id: int) -> Match:
    """
    Confirm match score (opponent confirms submitted score).

    Args:
        match_id: Match ID
        user_id: User confirming (must be opponent, not submitter)

    Returns:
        Updated Match object

    Raises:
        ValueError: If validation fails
    """
    from datetime import datetime

    match = Match.query.get_or_404(match_id)

    # Validate user is participant
    if user_id not in (match.player1_id, match.player2_id):
        raise ValueError('You are not a participant in this match')

    # Validate user is NOT submitter
    if user_id == match.submitted_by_id:
        raise ValueError('You cannot confirm your own submission')

    # Validate match status
    if match.status != MatchStatus.PENDING_CONFIRMATION.value:
        raise ValueError(f'Cannot confirm match in {match.status} status')

    # Update match status
    match.status = MatchStatus.CONFIRMED.value
    match.confirmed_by_id = user_id
    match.confirmed_at = datetime.utcnow()
    match.played_at = datetime.utcnow()

    # Update statistics (skip for free matches)
    if match.tournament_id is not None:
        _update_match_statistics(match)

    # Update ELO ratings
    from app.services.elo import update_elo_ratings
    update_elo_ratings(match)

    db.session.commit()

    # If this is a playoff match, advance winner
    if match.phase == MatchPhase.PLAYOFF.value:
        from app.services.tournament import advance_playoff_winner
        advance_playoff_winner(match.id)

    return match


def dispute_match_score(match_id: int, user_id: int) -> Match:
    """
    Dispute match score (opponent disputes submitted score).

    Args:
        match_id: Match ID
        user_id: User disputing (must be opponent, not submitter)

    Returns:
        Updated Match object

    Raises:
        ValueError: If validation fails
    """
    match = Match.query.get_or_404(match_id)

    # Validate user is participant
    if user_id not in (match.player1_id, match.player2_id):
        raise ValueError('You are not a participant in this match')

    # Validate user is NOT submitter
    if user_id == match.submitted_by_id:
        raise ValueError('You cannot dispute your own submission')

    # Validate match status
    if match.status != MatchStatus.PENDING_CONFIRMATION.value:
        raise ValueError(f'Cannot dispute match in {match.status} status')

    # Update match status (admin will resolve)
    match.status = MatchStatus.DISPUTED.value

    db.session.commit()
    return match


def _update_match_statistics(match: Match) -> None:
    """
    Update Registration statistics after match confirmation.

    Args:
        match: Confirmed Match object

    Raises:
        ValueError: If registrations not found
    """
    from app.models import Registration, SetScore

    # Get registrations for both players
    reg1 = Registration.query.filter_by(
        user_id=match.player1_id,
        tournament_id=match.tournament_id
    ).first()

    reg2 = Registration.query.filter_by(
        user_id=match.player2_id,
        tournament_id=match.tournament_id
    ).first()

    if not reg1 or not reg2:
        raise ValueError('Registration records not found for match participants')

    # Get set scores
    set_scores = SetScore.query.filter_by(match_id=match.id).all()

    # Calculate stats for each player
    p1_sets_won = 0
    p1_sets_lost = 0
    p1_points_won = 0
    p1_points_lost = 0

    for set_score in set_scores:
        p1_points_won += set_score.player1_score
        p1_points_lost += set_score.player2_score

        if set_score.player1_score > set_score.player2_score:
            p1_sets_won += 1
        else:
            p1_sets_lost += 1

    p2_sets_won = p1_sets_lost
    p2_sets_lost = p1_sets_won
    p2_points_won = p1_points_lost
    p2_points_lost = p1_points_won

    # Update Registration records
    reg1.sets_won += p1_sets_won
    reg1.sets_lost += p1_sets_lost
    reg1.points_won += p1_points_won
    reg1.points_lost += p1_points_lost

    reg2.sets_won += p2_sets_won
    reg2.sets_lost += p2_sets_lost
    reg2.points_won += p2_points_won
    reg2.points_lost += p2_points_lost

    # Update group points (2 for win, 1 for loss)
    if match.winner_id == match.player1_id:
        reg1.group_points += 2
        reg2.group_points += 1
    else:
        reg1.group_points += 1
        reg2.group_points += 2


def forfeit_match(match_id: int, forfeiting_user_id: int, admin_override: bool = False) -> Match:
    """
    Forfeit a match. The forfeiting player loses, opponent wins by walkover.

    Args:
        match_id: Match ID
        forfeiting_user_id: User ID of player forfeiting
        admin_override: If True, skip participant validation (admin action)

    Returns:
        Updated Match object

    Raises:
        ValueError: If validation fails
    """
    from datetime import datetime

    match = Match.query.get_or_404(match_id)

    # Validate match status
    if match.status != MatchStatus.SCHEDULED.value:
        raise ValueError(f'Cannot forfeit match in {match.status} status')

    # Validate forfeiting user is participant (unless admin override)
    if not admin_override:
        if forfeiting_user_id not in (match.player1_id, match.player2_id):
            raise ValueError('You are not a participant in this match')

    # Ensure forfeiting user is actually a participant even with admin override
    if forfeiting_user_id not in (match.player1_id, match.player2_id):
        raise ValueError('Forfeiting user must be a match participant')

    # Determine winner (opponent of forfeiting player)
    if forfeiting_user_id == match.player1_id:
        match.winner_id = match.player2_id
    else:
        match.winner_id = match.player1_id

    # Update match status to walkover
    match.status = MatchStatus.WALKOVER.value
    match.played_at = datetime.utcnow()

    # Update statistics (winner +2, loser +0, no sets/points) - skip for free matches
    if match.tournament_id is not None:
        _update_walkover_statistics(match, forfeiting_user_id)

    # Update ELO ratings
    from app.services.elo import update_elo_ratings
    update_elo_ratings(match)

    db.session.commit()

    # If this is a playoff match, advance winner
    if match.phase == MatchPhase.PLAYOFF.value:
        from app.services.tournament import advance_playoff_winner
        advance_playoff_winner(match.id)

    return match


def _update_walkover_statistics(match: Match, forfeiting_user_id: int) -> None:
    """
    Update Registration statistics after walkover.
    Winner gets +2 points, loser gets +0 points.
    No sets or points are counted (no game played).

    Args:
        match: Match object with winner_id set
        forfeiting_user_id: User ID of the player who forfeited
    """
    from app.models import Registration

    # Get registrations for both players
    winner_reg = Registration.query.filter_by(
        user_id=match.winner_id,
        tournament_id=match.tournament_id
    ).first()

    loser_reg = Registration.query.filter_by(
        user_id=forfeiting_user_id,
        tournament_id=match.tournament_id
    ).first()

    if not winner_reg or not loser_reg:
        raise ValueError('Registration records not found for match participants')

    # Winner gets +2 points, loser gets +0 points (harsher than loss where loser gets +1)
    winner_reg.group_points += 2
    # loser gets 0 points (no addition needed)


def reset_disputed_match(match_id: int, admin_override: bool = False) -> Match:
    """
    Reset a disputed match so players can resubmit scores.

    Args:
        match_id: Match ID
        admin_override: If True, allows admin to reset (default False)

    Returns:
        Reset Match object

    Raises:
        ValueError: If match is not in disputed status
    """
    from app.models import SetScore

    match = Match.query.get_or_404(match_id)

    if match.status != MatchStatus.DISPUTED.value:
        raise ValueError('Can only reset disputed matches')

    # Delete existing set scores
    SetScore.query.filter_by(match_id=match_id).delete()

    # Reset match fields
    match.status = MatchStatus.SCHEDULED.value
    match.winner_id = None
    match.submitted_by_id = None
    match.submitted_at = None
    match.confirmed_by_id = None
    match.confirmed_at = None
    match.played_at = None

    db.session.commit()
    return match


def admin_set_match_score(match_id: int, sets_data: list[dict], winner_id: int) -> Match:
    """
    Admin sets the final score for a disputed match.

    Args:
        match_id: Match ID
        sets_data: List of dicts with player1_score, player2_score
        winner_id: User ID of the winner

    Returns:
        Updated Match object

    Raises:
        ValueError: If validation fails
    """
    from app.models import SetScore
    from datetime import datetime

    match = Match.query.get_or_404(match_id)

    if match.status != MatchStatus.DISPUTED.value:
        raise ValueError('Can only set score for disputed matches')

    if winner_id not in (match.player1_id, match.player2_id):
        raise ValueError('Winner must be a match participant')

    # Delete existing set scores
    SetScore.query.filter_by(match_id=match_id).delete()

    # Create new set scores
    for i, set_data in enumerate(sets_data):
        set_score = SetScore(
            match_id=match_id,
            set_number=i + 1,
            player1_score=set_data['player1_score'],
            player2_score=set_data['player2_score']
        )
        db.session.add(set_score)

    # Finalize match
    match.winner_id = winner_id
    match.status = MatchStatus.CONFIRMED.value
    match.confirmed_at = datetime.utcnow()
    match.played_at = datetime.utcnow()

    # Update statistics (reuse existing helper) - skip for free matches
    if match.tournament_id is not None:
        _update_match_statistics(match)

    # Update ELO ratings
    from app.services.elo import update_elo_ratings
    update_elo_ratings(match)

    db.session.commit()

    # Handle playoff advancement if needed
    if match.phase == MatchPhase.PLAYOFF.value:
        from app.services.tournament import advance_playoff_winner
        advance_playoff_winner(match.id)

    return match


def create_free_match(challenger_id: int, opponent_id: int) -> Match:
    """
    Create a free match (challenge) between two users.

    Args:
        challenger_id: User ID of the challenger
        opponent_id: User ID of the opponent

    Returns:
        Created Match object

    Raises:
        ValueError: If validation fails
    """
    if challenger_id == opponent_id:
        raise ValueError('You cannot challenge yourself')

    # Verify both users exist
    challenger = User.query.get(challenger_id)
    opponent = User.query.get(opponent_id)

    if not challenger or not opponent:
        raise ValueError('User not found')

    # Create free match
    match = Match(
        tournament_id=None,
        player1_id=challenger_id,
        player2_id=opponent_id,
        phase=MatchPhase.FREE.value,
        status=MatchStatus.SCHEDULED.value
    )

    db.session.add(match)
    db.session.commit()

    return match


def get_user_free_matches(user_id: int, status: Optional[str] = None, limit: int = 20) -> List[Match]:
    """
    Get free matches for a user.

    Args:
        user_id: User ID
        status: Optional status filter (e.g., 'scheduled', 'pending_confirmation')
        limit: Maximum number of matches to return

    Returns:
        List of Match objects
    """
    query = Match.query.filter(
        Match.tournament_id.is_(None),
        or_(Match.player1_id == user_id, Match.player2_id == user_id)
    )

    if status:
        query = query.filter(Match.status == status)

    return query.options(
        db.joinedload(Match.player1),
        db.joinedload(Match.player2)
    ).order_by(Match.created_at.desc()).limit(limit).all()
