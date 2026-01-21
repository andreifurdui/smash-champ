"""Match routes for score submission and confirmation."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.forms.match import ScoreSubmissionForm
from app.services.match import submit_match_score, confirm_match_score, dispute_match_score
from app.models import Match
from app.extensions import db

bp = Blueprint('match', __name__, url_prefix='/match')


@bp.route('/<int:match_id>/submit', methods=['GET', 'POST'])
@login_required
def submit(match_id):
    """Submit score for a match."""
    match = Match.query.get_or_404(match_id)

    # Validate user is participant
    if current_user.id not in (match.player1_id, match.player2_id):
        flash('You are not a participant in this match', 'error')
        return redirect(url_for('main.dashboard'))

    # Check if already submitted
    if match.status != 'scheduled':
        flash(f'Cannot submit score for match in {match.status} status', 'warning')
        return redirect(url_for('main.dashboard'))

    sets_to_win = match.tournament.sets_to_win
    form = ScoreSubmissionForm(sets_to_win=sets_to_win)

    if form.validate_on_submit():
        try:
            # Determine if current user is player1 or player2
            is_player1 = current_user.id == match.player1_id

            # Build sets data (swap scores if current user is player2)
            sets_data = []
            for i in range(1, 4):
                p1_field = getattr(form, f'set{i}_player1')
                p2_field = getattr(form, f'set{i}_player2')

                if p1_field.data is not None and p2_field.data is not None:
                    if is_player1:
                        sets_data.append({
                            'player1_score': p1_field.data,
                            'player2_score': p2_field.data
                        })
                    else:
                        # Swap if current user is player2
                        sets_data.append({
                            'player1_score': p2_field.data,
                            'player2_score': p1_field.data
                        })

            submit_match_score(match_id, current_user.id, sets_data)
            flash('Score submitted! Waiting for opponent confirmation.', 'success')
            return redirect(url_for('main.dashboard'))

        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')

    # Determine current player and opponent for display
    if current_user.id == match.player1_id:
        current_player = match.player1
        opponent = match.player2
    else:
        current_player = match.player2
        opponent = match.player1

    return render_template('match/submit.html',
                         match=match,
                         form=form,
                         current_player=current_player,
                         opponent=opponent,
                         sets_to_win=sets_to_win)


@bp.route('/<int:match_id>/confirm', methods=['POST'])
@login_required
def confirm(match_id):
    """Confirm opponent's submitted score."""
    try:
        confirm_match_score(match_id, current_user.id)
        flash('Match result confirmed! Statistics updated.', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('main.dashboard'))


@bp.route('/<int:match_id>/dispute', methods=['POST'])
@login_required
def dispute(match_id):
    """Dispute opponent's submitted score."""
    try:
        dispute_match_score(match_id, current_user.id)
        flash('Score disputed. Admin will review this match.', 'warning')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')

    return redirect(url_for('main.dashboard'))
