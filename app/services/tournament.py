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
