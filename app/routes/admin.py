"""Admin routes for tournament and user management."""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user

from app.extensions import db
from app.models import Tournament, TournamentStatus, MatchPhase, Match, User
from app.forms.tournament import TournamentCreateForm
from app.forms.admin import UserEditForm, TournamentEditForm
from app.services.match import forfeit_match, reset_disputed_match, admin_set_match_score
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
from app.services.admin import (
    get_all_users,
    get_user_by_id,
    update_user,
    toggle_admin_status,
    reset_user_password,
    delete_user,
    update_tournament,
    add_player_to_tournament,
    remove_player_from_tournament,
    get_unregistered_users,
    AdminError
)
from app.utils.decorators import admin_required
from app.utils.avatars import get_default_avatars

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

    # Get unregistered users for add player dropdown (only during registration)
    unregistered_users = []
    if tournament.status == TournamentStatus.REGISTRATION.value:
        unregistered_users = get_unregistered_users(tournament_id)

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
        unregistered_users=unregistered_users,
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


@bp.route('/match/<int:match_id>/reset', methods=['POST'])
@admin_required
def match_reset(match_id):
    """
    Admin action: Reset a disputed match so players can resubmit scores.

    Clears all set scores and resets match to scheduled status.
    """
    match = Match.query.get_or_404(match_id)

    try:
        reset_disputed_match(match_id, admin_override=True)
        flash('Match reset. Players can resubmit scores.', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('admin.tournament_detail', tournament_id=match.tournament_id))


@bp.route('/match/<int:match_id>/set-score', methods=['POST'])
@admin_required
def match_set_score(match_id):
    """
    Admin action: Set the final score for a disputed match.

    Accepts set scores and winner from form data.
    """
    match = Match.query.get_or_404(match_id)

    try:
        # Parse set scores from form
        sets_data = []

        # Set 1 (required)
        set1_p1 = request.form.get('set1_p1', type=int)
        set1_p2 = request.form.get('set1_p2', type=int)
        if set1_p1 is not None and set1_p2 is not None:
            sets_data.append({'player1_score': set1_p1, 'player2_score': set1_p2})

        # Set 2 (required)
        set2_p1 = request.form.get('set2_p1', type=int)
        set2_p2 = request.form.get('set2_p2', type=int)
        if set2_p1 is not None and set2_p2 is not None:
            sets_data.append({'player1_score': set2_p1, 'player2_score': set2_p2})

        # Set 3 (optional)
        set3_p1 = request.form.get('set3_p1', type=int)
        set3_p2 = request.form.get('set3_p2', type=int)
        if set3_p1 is not None and set3_p2 is not None:
            sets_data.append({'player1_score': set3_p1, 'player2_score': set3_p2})

        # Get winner
        winner_id = request.form.get('winner_id', type=int)
        if not winner_id:
            raise ValueError('Winner must be selected')

        # Validate sets based on tournament format
        sets_to_win = match.tournament.sets_to_win
        if sets_to_win == 1:
            if len(sets_data) != 1:
                raise ValueError('Best-of-1 match must have exactly 1 set')
        else:
            if len(sets_data) < 2:
                raise ValueError('At least 2 sets are required for best-of-3')

        admin_set_match_score(match_id, sets_data, winner_id)
        flash('Match score set and confirmed.', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('admin.tournament_detail', tournament_id=match.tournament_id))


# ----- User Management Routes -----

@bp.route('/users')
@admin_required
def users():
    """
    List all users for admin management.

    Shows user list with avatars, usernames, emails, admin badges,
    and action buttons for editing/deleting.
    """
    all_users = get_all_users()
    return render_template('admin/users.html', users=all_users)


@bp.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def user_edit(user_id):
    """
    Edit a user's profile.

    GET: Show user edit form
    POST: Process form submission and update user
    """
    user = get_user_by_id(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))

    # Get available avatars for dropdown
    default_avatars = get_default_avatars()
    avatar_choices = [('', 'Default (random)')]
    for avatar in default_avatars:
        avatar_choices.append((f'/static/img/default_avatars/{avatar}', avatar))

    form = UserEditForm(
        original_username=user.username,
        original_email=user.email,
        obj=user
    )
    form.avatar_path.choices = avatar_choices

    # Set initial tagline value (uses raw _tagline to avoid default)
    if request.method == 'GET':
        form.tagline.data = user._tagline

    if form.validate_on_submit():
        try:
            update_user(
                user_id=user_id,
                username=form.username.data,
                email=form.email.data,
                tagline=form.tagline.data,
                avatar_path=form.avatar_path.data
            )
            flash(f'User "{form.username.data}" updated successfully.', 'success')
            return redirect(url_for('admin.users'))
        except AdminError as e:
            flash(str(e), 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')

    return render_template('admin/user_edit.html', form=form, user=user)


@bp.route('/user/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def user_toggle_admin(user_id):
    """
    Toggle admin status for a user.

    Promotes regular user to admin or demotes admin to regular user.
    Prevents self-demotion.
    """
    try:
        user = toggle_admin_status(user_id, current_user.id)
        status = 'promoted to admin' if user.is_admin else 'demoted to regular user'
        flash(f'{user.username} has been {status}.', 'success')
    except AdminError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('admin.users'))


@bp.route('/user/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def user_reset_password(user_id):
    """
    Reset a user's password to a random temporary password.

    Generates a 12-character alphanumeric password and shows it
    in a flash message for the admin to share with the user.
    """
    try:
        user, temp_password = reset_user_password(user_id)
        flash(f'Password for {user.username} has been reset to: {temp_password}', 'success')
    except AdminError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('admin.users'))


@bp.route('/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def user_delete(user_id):
    """
    Delete a user and all their registrations.

    Prevents self-deletion. Cascades to remove registrations
    but preserves match history (matches remain but player info
    may be incomplete).
    """
    try:
        username = delete_user(user_id, current_user.id)
        flash(f'User "{username}" has been deleted.', 'success')
    except AdminError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('admin.users'))


# ----- Tournament Editing -----

@bp.route('/tournament/<int:tournament_id>/edit', methods=['GET', 'POST'])
@admin_required
def tournament_edit(tournament_id):
    """
    Edit tournament details (name, description).

    GET: Show tournament edit form
    POST: Process form submission and update tournament
    """
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        flash('Tournament not found.', 'error')
        return redirect(url_for('admin.dashboard'))

    form = TournamentEditForm(obj=tournament)

    if form.validate_on_submit():
        try:
            update_tournament(
                tournament_id=tournament_id,
                name=form.name.data,
                description=form.description.data
            )
            flash(f'Tournament "{form.name.data}" updated successfully.', 'success')
            return redirect(url_for('admin.tournament_detail', tournament_id=tournament_id))
        except AdminError as e:
            flash(str(e), 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')

    return render_template('admin/tournament_edit.html', form=form, tournament=tournament)


# ----- Registration Management -----

@bp.route('/tournament/<int:tournament_id>/add-player/<int:user_id>', methods=['POST'])
@admin_required
def tournament_add_player(tournament_id, user_id):
    """
    Add a player to a tournament.

    Only available during registration phase.
    Creates a new registration for the specified user.
    """
    try:
        registration = add_player_to_tournament(tournament_id, user_id)
        flash(f'{registration.user.username} has been added to the tournament.', 'success')
    except AdminError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('admin.tournament_detail', tournament_id=tournament_id))


@bp.route('/tournament/<int:tournament_id>/remove-player/<int:user_id>', methods=['POST'])
@admin_required
def tournament_remove_player(tournament_id, user_id):
    """
    Remove a player from a tournament.

    Only available during registration phase.
    Deletes the registration for the specified user.
    """
    try:
        username = remove_player_from_tournament(tournament_id, user_id)
        flash(f'{username} has been removed from the tournament.', 'success')
    except AdminError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('admin.tournament_detail', tournament_id=tournament_id))
