"""Admin routes for tournament management."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user

from app.extensions import db
from app.models import Tournament, TournamentStatus, MatchPhase, Match
from app.forms.tournament import TournamentCreateForm
from app.services.match import forfeit_match
from app.services.tournament import (
    create_tournament,
    get_tournament_with_players,
    start_group_stage,
    start_playoffs,
    complete_tournament as complete_tournament_service,
    cancel_tournament,
    get_tournament_matches,
    TournamentError
)
from app.utils.decorators import admin_required

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/')
@admin_required
def dashboard():
    """
    Admin dashboard showing all tournaments.

    Lists all tournaments with status badges, player counts,
    and action buttons for tournament management.
    """
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    return render_template('admin/dashboard.html', tournaments=tournaments)


@bp.route('/tournament/create', methods=['GET', 'POST'])
@admin_required
def tournament_create():
    """
    Create a new tournament.

    GET: Show tournament creation form
    POST: Process form submission and create tournament
    """
    form = TournamentCreateForm()

    if form.validate_on_submit():
        try:
            tournament = create_tournament(
                name=form.name.data,
                description=form.description.data if form.description.data else None,
                playoff_format=form.playoff_format.data,
                sets_to_win=form.sets_to_win.data
            )
            flash(f'Tournament "{tournament.name}" created successfully!', 'success')
            return redirect(url_for('admin.tournament_detail', tournament_id=tournament.id))
        except TournamentError as e:
            flash(str(e), 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')

    return render_template('admin/tournament_create.html', form=form)


@bp.route('/tournament/<int:tournament_id>')
@admin_required
def tournament_detail(tournament_id):
    """
    View tournament details with registered players and fixtures.

    Shows:
    - Tournament information (name, status, format)
    - Registered players list
    - Action buttons (start group stage, cancel)
    - Group stage fixtures (if generated)
    """
    tournament = get_tournament_with_players(tournament_id)

    if not tournament:
        flash('Tournament not found.', 'error')
        return redirect(url_for('admin.dashboard'))

    # Get registered players
    players = [reg.user for reg in tournament.registrations]

    # Get group stage matches if they exist
    group_matches = []
    if tournament.status in [TournamentStatus.GROUP_STAGE.value,
                            TournamentStatus.PLAYOFFS.value,
                            TournamentStatus.COMPLETED.value]:
        group_matches = get_tournament_matches(tournament_id, phase=MatchPhase.GROUP.value)

    return render_template(
        'admin/tournament_detail.html',
        tournament=tournament,
        players=players,
        group_matches=group_matches
    )


@bp.route('/tournament/<int:tournament_id>/start-group-stage', methods=['POST'])
@admin_required
def tournament_start_group_stage(tournament_id):
    """
    Start group stage and generate double round-robin fixtures.

    Validates:
    - Tournament exists
    - Minimum 2 players registered
    - Tournament in REGISTRATION status
    - No existing fixtures

    On success: Creates n×(n-1) matches where n = player count
    """
    try:
        matches_created = start_group_stage(tournament_id)
        flash(f'Group stage started! Generated {matches_created} matches.', 'success')
    except TournamentError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('admin.tournament_detail', tournament_id=tournament_id))


@bp.route('/tournament/<int:tournament_id>/cancel', methods=['POST'])
@admin_required
def tournament_cancel(tournament_id):
    """
    Cancel a tournament.

    Validates:
    - Tournament exists
    - Not already cancelled
    - Not completed
    """
    try:
        cancel_tournament(tournament_id)
        flash('Tournament cancelled successfully.', 'warning')
    except TournamentError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('admin.tournament_detail', tournament_id=tournament_id))


@bp.route('/tournament/<int:tournament_id>/start-playoffs', methods=['POST'])
@admin_required
def tournament_start_playoffs(tournament_id):
    """
    Start playoff phase.

    Validates:
    - Tournament exists
    - Tournament in GROUP_STAGE status
    - All group matches are confirmed
    - At least 2 players

    On success: Creates first Gauntlet playoff match
    """
    try:
        tournament = start_playoffs(tournament_id)
        flash(f'Playoffs started for {tournament.name}! Gauntlet bracket generated.', 'success')
    except TournamentError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('admin.tournament_detail', tournament_id=tournament_id))


@bp.route('/tournament/<int:tournament_id>/complete', methods=['POST'])
@admin_required
def tournament_complete(tournament_id):
    """
    Complete tournament (manual trigger if needed).

    Validates:
    - Tournament exists
    - Tournament in PLAYOFFS status
    - Championship match is confirmed

    On success: Records final positions and creates TournamentWinner records
    """
    try:
        tournament = complete_tournament_service(tournament_id)
        flash(f'Tournament {tournament.name} completed! Final standings recorded.', 'success')
    except TournamentError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('admin.tournament_detail', tournament_id=tournament_id))


@bp.route('/match/<int:match_id>/forfeit/<int:forfeiting_user_id>', methods=['POST'])
@admin_required
def match_forfeit(match_id, forfeiting_user_id):
    """
    Admin action: Forfeit a match on behalf of a player.

    The forfeiting player loses by walkover, opponent wins.
    """
    match = Match.query.get_or_404(match_id)

    try:
        forfeit_match(match_id, forfeiting_user_id, admin_override=True)
        flash('Match forfeited. Winner awarded by walkover.', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('admin.tournament_detail', tournament_id=match.tournament_id))
