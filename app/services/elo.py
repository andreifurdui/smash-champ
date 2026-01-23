"""ELO rating calculation and management service."""

import math
from app.extensions import db
from app.models import User, Match, EloHistory, MatchStatus

# K-factor: Higher = more rating volatility
K_FACTOR_NORMAL = 32
K_FACTOR_WALKOVER = 16


def calculate_expected_score(player_elo: int, opponent_elo: int) -> float:
    """
    Calculate expected score for a player.

    Returns a value between 0 and 1 representing the probability of winning.
    """
    return 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))


def calculate_margin_multiplier(match: Match) -> float:
    """
    Calculate margin of victory multiplier based on set and point difference.

    Returns a multiplier (1.0 to ~1.5) that scales ELO changes.
    - 2-1 close match: ~1.0x
    - 2-0 close match: ~1.2x
    - 2-0 dominant match: ~1.4x
    """
    set_scores = match.set_scores.all()
    if not set_scores:
        return 1.0

    winner_sets = 0
    loser_sets = 0
    winner_points = 0
    loser_points = 0

    for s in set_scores:
        if match.winner_id == match.player1_id:
            winner_points += s.player1_score
            loser_points += s.player2_score
            if s.player1_score > s.player2_score:
                winner_sets += 1
            else:
                loser_sets += 1
        else:
            winner_points += s.player2_score
            loser_points += s.player1_score
            if s.player2_score > s.player1_score:
                winner_sets += 1
            else:
                loser_sets += 1

    # Set difference component: 2-0 = +0.2, 2-1 = +0.0
    set_diff = winner_sets - loser_sets
    set_bonus = (set_diff - 1) * 0.2

    # Point difference component: logarithmic scale, capped
    # A +15 point diff adds ~0.2, +30 adds ~0.27
    point_diff = max(0, winner_points - loser_points)
    point_bonus = min(0.3, math.log(point_diff + 1) * 0.08)

    return 1.0 + set_bonus + point_bonus


def calculate_elo_change(winner_elo: int, loser_elo: int, margin_multiplier: float = 1.0, is_walkover: bool = False) -> tuple[int, int]:
    """
    Calculate ELO rating changes for winner and loser.

    Args:
        winner_elo: Winner's current ELO
        loser_elo: Loser's current ELO
        margin_multiplier: Multiplier based on victory margin (1.0 to ~1.5)
        is_walkover: Whether match was a walkover (reduces K-factor)

    Returns tuple of (winner_change, loser_change).
    """
    k_factor = K_FACTOR_WALKOVER if is_walkover else K_FACTOR_NORMAL
    k_factor *= margin_multiplier

    # Winner gets actual score of 1, loser gets 0
    expected_winner = calculate_expected_score(winner_elo, loser_elo)
    expected_loser = 1 - expected_winner

    winner_change = round(k_factor * (1 - expected_winner))
    loser_change = round(k_factor * (0 - expected_loser))

    return winner_change, loser_change


def update_elo_ratings(match: Match) -> bool:
    """
    Update ELO ratings for both players after a match.

    Creates EloHistory records and updates User.elo_rating.
    Returns True if successful, False if match has no winner.
    """
    if not match.winner_id:
        return False

    # Get winner and loser
    if match.winner_id == match.player1_id:
        winner = match.player1
        loser = match.player2
    else:
        winner = match.player2
        loser = match.player1

    # Check if already processed (avoid double processing)
    existing = EloHistory.query.filter_by(match_id=match.id).first()
    if existing:
        return False

    # Calculate ELO changes with margin of victory
    is_walkover = match.status == 'walkover'
    margin_mult = 1.0 if is_walkover else calculate_margin_multiplier(match)
    winner_change, loser_change = calculate_elo_change(
        winner.elo_rating, loser.elo_rating, margin_mult, is_walkover
    )

    # Create history records
    winner_history = EloHistory(
        user_id=winner.id,
        match_id=match.id,
        elo_before=winner.elo_rating,
        elo_after=winner.elo_rating + winner_change,
        elo_change=winner_change
    )

    loser_history = EloHistory(
        user_id=loser.id,
        match_id=match.id,
        elo_before=loser.elo_rating,
        elo_after=loser.elo_rating + loser_change,
        elo_change=loser_change
    )

    # Update user ratings
    winner.elo_rating += winner_change
    loser.elo_rating += loser_change

    # Prevent going below 100
    if loser.elo_rating < 100:
        loser.elo_rating = 100
        loser_history.elo_after = 100

    db.session.add(winner_history)
    db.session.add(loser_history)

    return True


def get_elo_leaderboard(limit: int = 50) -> list[dict]:
    """
    Get ELO leaderboard sorted by rating.

    Returns list of dicts with user, elo_rating, and rank.
    """
    users = User.query.order_by(User.elo_rating.desc()).limit(limit).all()

    return [
        {
            'user': user,
            'elo_rating': user.elo_rating,
            'rank': idx + 1
        }
        for idx, user in enumerate(users)
    ]


def get_user_elo_history(user_id: int, limit: int = 20) -> list[EloHistory]:
    """
    Get ELO history for a specific user, most recent first.
    """
    return EloHistory.query.filter_by(user_id=user_id)\
        .order_by(EloHistory.created_at.desc())\
        .limit(limit).all()


def recalculate_all_elo() -> dict:
    """
    Reset all ELO ratings and recalculate from match history.

    Returns dict with statistics:
    - users_reset: number of users reset to 1200
    - matches_processed: number of matches processed
    - final_ratings: dict of username -> elo_rating
    """
    # 1. Clear existing EloHistory records
    EloHistory.query.delete()

    # 2. Reset all users to 1200
    users_reset = User.query.update({User.elo_rating: 1200})
    db.session.commit()

    # 3. Get completed matches in chronological order
    matches = Match.query.filter(
        Match.status.in_([MatchStatus.CONFIRMED.value, MatchStatus.WALKOVER.value]),
        Match.winner_id.isnot(None)
    ).order_by(Match.played_at.asc()).all()

    # 4. Process each match
    processed = 0
    for match in matches:
        if update_elo_ratings(match):
            processed += 1
        db.session.commit()

    # 5. Get final ratings
    final_ratings = {
        u.username: u.elo_rating
        for u in User.query.order_by(User.elo_rating.desc()).all()
    }

    return {
        'users_reset': users_reset,
        'matches_processed': processed,
        'final_ratings': final_ratings
    }
