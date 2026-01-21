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


def _generate_round_robin_schedule(players: list) -> list[tuple]:
    """
    Generate round-robin schedule using circle method.

    Each player plays once per round before anyone plays their second match.
    For n players: (n-1) rounds for single round-robin.

    Args:
        players: List of player objects (must have .id attribute)

    Returns:
        List of (player1_id, player2_id) tuples ordered by round.
    """
    n = len(players)
    player_ids = [p.id for p in players]

    # Add bye if odd number of players
    if n % 2 == 1:
        player_ids.append(None)  # bye
        n += 1

    schedule = []

    # n-1 rounds for single round-robin
    for round_num in range(n - 1):
        round_matches = []
        for i in range(n // 2):
            p1 = player_ids[i]
            p2 = player_ids[n - 1 - i]
            # Skip byes
            if p1 is not None and p2 is not None:
                round_matches.append((p1, p2))
        schedule.extend(round_matches)

        # Rotate: fix first player, rotate rest clockwise
        player_ids = [player_ids[0]] + [player_ids[-1]] + player_ids[1:-1]

    return schedule


def create_tournament(name: str, description: Optional[str], playoff_format: str, sets_to_win: int = 2) -> Tournament:
    """
    Create a new tournament in REGISTRATION status.

    Args:
        name: Tournament name (3-128 chars)
        description: Optional tournament description (max 500 chars)
        playoff_format: Playoff format (e.g., GAUNTLET)
        sets_to_win: Sets needed to win a match (1 for best-of-1, 2 for best-of-3)

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

    if sets_to_win not in (1, 2):
        raise TournamentError("Sets to win must be 1 or 2")

    tournament = Tournament(
        name=name,
        description=description,
        playoff_format=playoff_format,
        sets_to_win=sets_to_win,
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
    return Tournament.query.get(tournament_id)


def start_group_stage(tournament_id: int) -> int:
    """
    Start group stage and generate double round-robin fixtures.

    Algorithm: Circle method for fair round-robin scheduling.
    - Each player plays once per round before anyone plays a second match
    - First fixtures (n-1 rounds), then return fixtures (n-1 rounds)
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

    # Generate round-robin schedule (proper round ordering)
    first_fixture_pairs = _generate_round_robin_schedule(players)
    matches_created = 0

    # Create matches for first fixtures (fixture_number=1)
    for p1_id, p2_id in first_fixture_pairs:
        match = Match(
            tournament_id=tournament_id,
            player1_id=p1_id,
            player2_id=p2_id,
            phase=MatchPhase.GROUP,
            fixture_number=1,
            status=MatchStatus.SCHEDULED
        )
        db.session.add(match)
        matches_created += 1

    # Create return fixtures (fixture_number=2) in same round order
    for p1_id, p2_id in first_fixture_pairs:
        match = Match(
            tournament_id=tournament_id,
            player1_id=p2_id,  # Swapped
            player2_id=p1_id,
            phase=MatchPhase.GROUP,
            fixture_number=2,
            status=MatchStatus.SCHEDULED
        )
        db.session.add(match)
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


def start_playoffs(tournament_id: int) -> Tournament:
    """
    Start playoff phase - generate Gauntlet bracket from group standings.

    Args:
        tournament_id: Tournament ID

    Returns:
        Updated Tournament object

    Raises:
        TournamentError: If validation fails
    """
    from datetime import datetime
    from app.models import TournamentWinner

    tournament = Tournament.query.get_or_404(tournament_id)

    # Validate tournament status
    if tournament.status != TournamentStatus.GROUP_STAGE:
        raise TournamentError(f'Cannot start playoffs from {tournament.status.value} status')

    # Validate all group matches are confirmed
    pending_matches = Match.query.filter_by(
        tournament_id=tournament_id,
        phase=MatchPhase.GROUP.value
    ).filter(
        Match.status.in_([MatchStatus.SCHEDULED.value, MatchStatus.PENDING_CONFIRMATION.value])
    ).count()

    if pending_matches > 0:
        raise TournamentError(f'Cannot start playoffs: {pending_matches} group matches still pending')

    # Calculate final standings
    standings = calculate_standings(tournament_id)

    if len(standings) < 2:
        raise TournamentError('Need at least 2 players for playoffs')

    # Update Registration records with seeds and positions
    for standing in standings:
        reg = Registration.query.filter_by(
            tournament_id=tournament_id,
            user_id=standing['user'].id
        ).first()
        reg.seed = standing['position']
        reg.group_position = standing['position']

    # Generate Gauntlet bracket
    # Gauntlet: Last place (#n) vs second-to-last (#n-1), winner challenges up
    # Total matches: n - 1

    # Reverse standings (start from bottom)
    seeded_players = [s['user'].id for s in standings]
    seeded_players.reverse()  # Now: [#4, #3, #2, #1] for 4 players

    # Create first match: #4 vs #3 (last vs second-to-last)
    first_match = Match(
        tournament_id=tournament_id,
        player1_id=seeded_players[0],  # Last place
        player2_id=seeded_players[1],  # Second-to-last
        phase=MatchPhase.PLAYOFF,
        status=MatchStatus.SCHEDULED,
        bracket_round=1,
        bracket_position=1
    )
    db.session.add(first_match)

    # Update tournament status
    tournament.status = TournamentStatus.PLAYOFFS

    db.session.commit()
    return tournament


def advance_playoff_winner(match_id: int) -> None:
    """
    Handle playoff winner advancement - create next match if not final.

    Called automatically after match confirmation for PLAYOFF matches.

    Args:
        match_id: ID of confirmed playoff match

    Raises:
        TournamentError: If match not playoff or not confirmed
    """
    from datetime import datetime

    match = Match.query.get_or_404(match_id)

    # Validate this is a confirmed playoff match
    if match.phase != MatchPhase.PLAYOFF:
        return  # Not a playoff match, nothing to do

    if match.status != MatchStatus.CONFIRMED:
        raise TournamentError('Match must be confirmed to advance winner')

    if not match.winner_id:
        raise TournamentError('Match must have a winner')

    # Get all registrations (ordered by seed)
    registrations = Registration.query.filter_by(
        tournament_id=match.tournament_id
    ).order_by(Registration.seed.asc()).all()

    seeded_player_ids = [r.user_id for r in registrations]
    total_players = len(seeded_player_ids)

    # Determine next opponent
    # Gauntlet logic: Winner challenges next higher seed
    current_round = match.bracket_round
    next_round = current_round + 1

    # Check if this was the final match
    if next_round > total_players - 1:
        # This was the championship match - tournament complete
        complete_tournament(match.tournament_id)
        return

    # Get next opponent (next seed in line)
    # seeded_player_ids is [#1, #2, #3, #4] (highest to lowest seed)
    # Reverse for gauntlet: [#4, #3, #2, #1]
    gauntlet_order = list(reversed(seeded_player_ids))
    next_opponent_id = gauntlet_order[next_round]  # next_round is 0-indexed position

    # Create next playoff match
    next_match = Match(
        tournament_id=match.tournament_id,
        player1_id=match.winner_id,  # Winner advances
        player2_id=next_opponent_id,  # Next challenger
        phase=MatchPhase.PLAYOFF,
        status=MatchStatus.SCHEDULED,
        bracket_round=next_round,
        bracket_position=1
    )
    db.session.add(next_match)
    db.session.commit()


def complete_tournament(tournament_id: int) -> Tournament:
    """
    Complete tournament - record final positions, update TournamentWinner.

    Args:
        tournament_id: Tournament ID

    Returns:
        Updated Tournament object

    Raises:
        TournamentError: If validation fails
    """
    from datetime import datetime
    from app.models import TournamentWinner

    tournament = Tournament.query.get_or_404(tournament_id)

    # Validate tournament status
    if tournament.status != TournamentStatus.PLAYOFFS:
        raise TournamentError(f'Cannot complete tournament from {tournament.status.value} status')

    # Get final playoff match (championship)
    final_match = Match.query.filter_by(
        tournament_id=tournament_id,
        phase=MatchPhase.PLAYOFF.value
    ).order_by(Match.bracket_round.desc()).first()

    if not final_match or not final_match.winner_id:
        raise TournamentError('Championship match must be confirmed to complete tournament')

    # Get all playoff matches (for position calculation)
    playoff_matches = Match.query.filter_by(
        tournament_id=tournament_id,
        phase=MatchPhase.PLAYOFF.value,
        status=MatchStatus.CONFIRMED.value
    ).order_by(Match.bracket_round.desc()).all()

    # Determine final positions (Gauntlet logic)
    # 1st place: Winner of final match (champion)
    # 2nd place: Loser of final match
    # 3rd+ place: Order by elimination round (later = better)

    champion_id = final_match.winner_id
    runner_up_id = final_match.player1_id if final_match.player2_id == champion_id else final_match.player2_id

    # Build position map
    position_map = {
        champion_id: 1,
        runner_up_id: 2
    }

    # Assign remaining positions based on elimination round (reverse bracket_round)
    # Higher bracket_round = eliminated later = better position
    eliminated_players = []
    for match in playoff_matches:
        loser_id = match.player1_id if match.winner_id == match.player2_id else match.player2_id
        if loser_id not in position_map:
            eliminated_players.append((loser_id, match.bracket_round))

    # Sort by bracket_round descending (eliminated later = better)
    eliminated_players.sort(key=lambda x: x[1], reverse=True)

    current_position = 3
    for player_id, _ in eliminated_players:
        position_map[player_id] = current_position
        current_position += 1

    # Update Registration records with final positions
    for user_id, position in position_map.items():
        reg = Registration.query.filter_by(
            tournament_id=tournament_id,
            user_id=user_id
        ).first()
        if reg:
            reg.final_position = position

    # Create TournamentWinner records
    for user_id, position in position_map.items():
        winner_record = TournamentWinner(
            tournament_id=tournament_id,
            user_id=user_id,
            position=position,
            awarded_at=datetime.utcnow()
        )
        db.session.add(winner_record)

    # Update tournament status
    tournament.status = TournamentStatus.COMPLETED

    db.session.commit()
    return tournament
