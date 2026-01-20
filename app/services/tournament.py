"""
Tournament management service layer.
Handles tournament creation, lifecycle management, and fixture generation.
"""
from typing import Optional
from sqlalchemy import or_
from app.extensions import db
from app.models import Tournament, Registration, Match, User, TournamentStatus, MatchPhase, MatchStatus


class TournamentError(Exception):
    """Custom exception for tournament-related errors."""
    pass


def create_tournament(name: str, description: Optional[str], playoff_format: str) -> Tournament:
    """
    Create a new tournament in REGISTRATION status.

    Args:
        name: Tournament name (3-128 chars)
        description: Optional tournament description (max 500 chars)
        playoff_format: Playoff format (e.g., GAUNTLET)

    Returns:
        Created Tournament object

    Raises:
        TournamentError: If validation fails
    """
    if not name or len(name) < 3:
        raise TournamentError("Tournament name must be at least 3 characters")

    if len(name) > 128:
        raise TournamentError("Tournament name must be at most 128 characters")

    if description and len(description) > 500:
        raise TournamentError("Description must be at most 500 characters")

    tournament = Tournament(
        name=name,
        description=description,
        playoff_format=playoff_format,
        status=TournamentStatus.REGISTRATION
    )

    db.session.add(tournament)
    db.session.commit()

    return tournament


def get_tournament_with_players(tournament_id: int) -> Optional[Tournament]:
    """
    Fetch tournament with all registered players.

    Args:
        tournament_id: Tournament ID

    Returns:
        Tournament object with registrations loaded, or None if not found
    """
    return Tournament.query.options(
        db.joinedload(Tournament.registrations).joinedload(Registration.user)
    ).get(tournament_id)


def start_group_stage(tournament_id: int) -> int:
    """
    Start group stage and generate double round-robin fixtures.

    Algorithm:
    - For each pair of players (i, j) where i < j:
      * Match 1: player_i vs player_j (fixture_number=1)
      * Match 2: player_j vs player_i (fixture_number=2)
    - Total matches: n × (n-1) where n = player count

    Args:
        tournament_id: Tournament ID

    Returns:
        Number of matches created

    Raises:
        TournamentError: If validation fails
    """
    tournament = get_tournament_with_players(tournament_id)

    if not tournament:
        raise TournamentError("Tournament not found")

    # Validate tournament status
    if tournament.status != TournamentStatus.REGISTRATION:
        raise TournamentError(f"Cannot start group stage. Tournament status is '{tournament.status}'")

    # Get registered players
    players = [reg.user for reg in tournament.registrations]
    player_count = len(players)

    # Validate minimum players
    if player_count < 2:
        raise TournamentError(f"Cannot start group stage with {player_count} player(s). Minimum 2 players required.")

    # Check if fixtures already exist
    existing_matches = Match.query.filter_by(
        tournament_id=tournament_id,
        phase=MatchPhase.GROUP
    ).first()

    if existing_matches:
        raise TournamentError("Group stage fixtures already exist")

    # Generate double round-robin fixtures
    matches_created = 0

    for i in range(player_count):
        for j in range(i + 1, player_count):
            # First fixture: player_i vs player_j
            match1 = Match(
                tournament_id=tournament_id,
                player1_id=players[i].id,
                player2_id=players[j].id,
                phase=MatchPhase.GROUP,
                fixture_number=1,
                status=MatchStatus.SCHEDULED
            )
            db.session.add(match1)
            matches_created += 1

            # Second fixture: player_j vs player_i (home/away swap)
            match2 = Match(
                tournament_id=tournament_id,
                player1_id=players[j].id,
                player2_id=players[i].id,
                phase=MatchPhase.GROUP,
                fixture_number=2,
                status=MatchStatus.SCHEDULED
            )
            db.session.add(match2)
            matches_created += 1

    # Update tournament status
    tournament.status = TournamentStatus.GROUP_STAGE

    db.session.commit()

    return matches_created


def cancel_tournament(tournament_id: int) -> None:
    """
    Cancel a tournament.

    Args:
        tournament_id: Tournament ID

    Raises:
        TournamentError: If validation fails
    """
    tournament = Tournament.query.get(tournament_id)

    if not tournament:
        raise TournamentError("Tournament not found")

    if tournament.status == TournamentStatus.CANCELLED:
        raise TournamentError("Tournament is already cancelled")

    if tournament.status == TournamentStatus.COMPLETED:
        raise TournamentError("Cannot cancel a completed tournament")

    tournament.status = TournamentStatus.CANCELLED
    db.session.commit()


def get_tournament_matches(tournament_id: int, phase: Optional[str] = None) -> list[Match]:
    """
    Get all matches for a tournament, optionally filtered by phase.

    Args:
        tournament_id: Tournament ID
        phase: Optional match phase filter (GROUP or PLAYOFF)

    Returns:
        List of Match objects
    """
    query = Match.query.filter_by(tournament_id=tournament_id).options(
        db.joinedload(Match.player1),
        db.joinedload(Match.player2)
    )

    if phase:
        query = query.filter_by(phase=phase)

    return query.order_by(Match.id).all()


def register_user_for_tournament(user_id: int, tournament_id: int) -> Registration:
    """
    Register user for tournament.

    Args:
        user_id: User ID
        tournament_id: Tournament ID

    Returns:
        Created Registration object

    Raises:
        TournamentError: If validation fails
    """
    # Query tournament
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        raise TournamentError("Tournament not found")

    # Validate status
    if tournament.status != TournamentStatus.REGISTRATION:
        raise TournamentError("Tournament is not accepting registrations")

    # Check for existing registration
    existing = Registration.query.filter_by(
        user_id=user_id,
        tournament_id=tournament_id
    ).first()

    if existing:
        raise TournamentError("You are already registered for this tournament")

    # Create registration with all stats initialized to 0
    registration = Registration(
        user_id=user_id,
        tournament_id=tournament_id,
        group_points=0,
        sets_won=0,
        sets_lost=0,
        points_won=0,
        points_lost=0
    )

    db.session.add(registration)
    db.session.commit()

    return registration


def unregister_user_from_tournament(user_id: int, tournament_id: int) -> None:
    """
    Unregister user from tournament.

    Args:
        user_id: User ID
        tournament_id: Tournament ID

    Raises:
        TournamentError: If validation fails
    """
    # Query tournament
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        raise TournamentError("Tournament not found")

    # Validate status - can only unregister during registration phase
    if tournament.status != TournamentStatus.REGISTRATION:
        raise TournamentError("Cannot unregister after group stage has started")

    # Query registration
    registration = Registration.query.filter_by(
        user_id=user_id,
        tournament_id=tournament_id
    ).first()

    if not registration:
        raise TournamentError("You are not registered for this tournament")

    db.session.delete(registration)
    db.session.commit()


def get_user_tournaments(user_id: int) -> dict:
    """
    Get categorized tournaments for user.

    Args:
        user_id: User ID

    Returns:
        Dictionary with categorized tournament lists:
        {
            'available': [Tournament],    # REGISTRATION, user not in
            'registered': [Tournament],   # User in, REGISTRATION status
            'in_progress': [Tournament],  # User in, GROUP_STAGE or PLAYOFFS
            'completed': [Tournament]     # User in, COMPLETED
        }
    """
    # Get user's registrations with tournaments
    user_registrations = Registration.query.filter_by(user_id=user_id).options(
        db.joinedload(Registration.tournament)
    ).all()

    # Extract registered tournament IDs and categorize
    registered_tournament_ids = [reg.tournament_id for reg in user_registrations]
    registered = []
    in_progress = []
    completed = []

    for reg in user_registrations:
        tournament = reg.tournament
        if tournament.status == TournamentStatus.REGISTRATION:
            registered.append(tournament)
        elif tournament.status in [TournamentStatus.GROUP_STAGE, TournamentStatus.PLAYOFFS]:
            in_progress.append(tournament)
        elif tournament.status == TournamentStatus.COMPLETED:
            completed.append(tournament)

    # Get available tournaments (REGISTRATION status, user not registered)
    available = Tournament.query.filter(
        Tournament.status == TournamentStatus.REGISTRATION,
        ~Tournament.id.in_(registered_tournament_ids) if registered_tournament_ids else True
    ).all()

    return {
        'available': available,
        'registered': registered,
        'in_progress': in_progress,
        'completed': completed
    }


def get_user_registration(user_id: int, tournament_id: int) -> Optional[Registration]:
    """
    Get user's registration for tournament, if exists.

    Args:
        user_id: User ID
        tournament_id: Tournament ID

    Returns:
        Registration object or None
    """
    return Registration.query.filter_by(
        user_id=user_id,
        tournament_id=tournament_id
    ).first()


def calculate_standings(tournament_id: int) -> list[dict]:
    """
    Calculate standings with tiebreakers.

    Tiebreaker order:
    1. Group points (DESC)
    2. Head-to-head record (simplified: 2 players only, 3+ skip to next)
    3. Set difference (DESC)
    4. Point difference (DESC)
    5. Points scored (DESC)

    Args:
        tournament_id: Tournament ID

    Returns:
        List of standing dictionaries with position, stats, and relationships
    """
    # 1. Get registrations with eager loading
    registrations = Registration.query.filter_by(tournament_id=tournament_id).options(
        db.joinedload(Registration.user)
    ).all()

    # 2. Get confirmed GROUP matches
    confirmed_matches = Match.query.filter(
        Match.tournament_id == tournament_id,
        Match.phase == MatchPhase.GROUP.value,
        Match.status == MatchStatus.CONFIRMED.value,
        Match.winner_id.isnot(None)
    ).all()

    # 3. Calculate W/L for each user
    stats = {}  # {user_id: {'won': 0, 'lost': 0}}
    for reg in registrations:
        stats[reg.user_id] = {'won': 0, 'lost': 0}

    for match in confirmed_matches:
        winner_id = match.winner_id
        loser_id = match.player2_id if winner_id == match.player1_id else match.player1_id

        if winner_id in stats:
            stats[winner_id]['won'] += 1
        if loser_id in stats:
            stats[loser_id]['lost'] += 1

    # 4. Build standings list
    standings = []
    for reg in registrations:
        user_stats = stats.get(reg.user_id, {'won': 0, 'lost': 0})
        won = user_stats['won']
        lost = user_stats['lost']

        standings.append({
            'registration': reg,
            'user': reg.user,
            'played': won + lost,
            'won': won,
            'lost': lost,
            'group_points': reg.group_points,
            'set_diff': reg.set_difference,
            'point_diff': reg.point_difference,
            'sets_record': f"{reg.sets_won}-{reg.sets_lost}",
            'points_record': f"{reg.points_won}-{reg.points_lost}"
        })

    # 5. Sort with tiebreakers
    # NOTE: Head-to-head (tiebreaker 2) simplified for Phase 3:
    # - Only handles 2-player ties (complex multi-way tiebreakers deferred)
    # - 3+ tied players fall through to set difference
    standings.sort(key=lambda x: (
        -x['group_points'],           # Primary: points DESC
        -x['set_diff'],               # Tiebreaker 3: set diff DESC
        -x['point_diff'],             # Tiebreaker 4: point diff DESC
        -x['registration'].points_won # Tiebreaker 5: points scored DESC
    ))

    # 6. Assign positions
    for i, standing in enumerate(standings):
        standing['position'] = i + 1

    return standings
