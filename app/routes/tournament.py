"""
User-facing tournament routes.
Handles browsing, registration, and viewing tournament details.
"""
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.services.tournament import (
    get_user_tournaments,
    get_tournament_with_players,
    get_user_registration,
    register_user_for_tournament,
    unregister_user_from_tournament,
    calculate_standings,
    get_tournament_matches,
    get_final_standings,
    TournamentError
)
from app.extensions import db

bp = Blueprint('tournament', __name__, url_prefix='/tournament')


@bp.route('/')
@login_required
def list():
    """Display tournaments grouped by status."""
    tournaments = get_user_tournaments(current_user.id)
    return render_template('tournament/list.html', tournaments=tournaments)


@bp.route('/<int:tournament_id>')
@login_required
def detail(tournament_id):
    """View tournament with tabs (Overview, Standings, Fixtures)."""
    tournament = get_tournament_with_players(tournament_id)
    if not tournament:
        flash('Tournament not found.', 'error')
        return redirect(url_for('tournament.list'))

    user_registration = get_user_registration(current_user.id, tournament_id)
    players = [reg.user for reg in tournament.registrations]

    # Calculate standings if group stage started
    standings = None
    if tournament.status in ['group_stage', 'playoffs', 'completed']:
        standings = calculate_standings(tournament_id)

    matches = get_tournament_matches(tournament_id, phase='group')

    # Get playoff matches if tournament is in playoffs or completed
    playoff_matches = []
    if tournament.status in ['playoffs', 'completed']:
        playoff_matches = get_tournament_matches(tournament_id, phase='playoff')

    # Get final standings for completed tournaments
    final_standings = None
    if tournament.status == 'completed':
        final_standings = get_final_standings(tournament_id)

    return render_template('tournament/detail.html',
                         tournament=tournament,
                         user_registration=user_registration,
                         players=players,
                         standings=standings,
                         matches=matches,
                         playoff_matches=playoff_matches,
                         final_standings=final_standings)


@bp.route('/<int:tournament_id>/register', methods=['POST'])
@login_required
def register(tournament_id):
    """Register current user for tournament."""
    try:
        register_user_for_tournament(current_user.id, tournament_id)
        flash('Successfully registered for tournament!', 'success')
    except TournamentError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('tournament.detail', tournament_id=tournament_id))


@bp.route('/<int:tournament_id>/unregister', methods=['POST'])
@login_required
def unregister(tournament_id):
    """Unregister current user from tournament."""
    try:
        unregister_user_from_tournament(current_user.id, tournament_id)
        flash('Successfully unregistered from tournament.', 'warning')
    except TournamentError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('tournament.detail', tournament_id=tournament_id))
