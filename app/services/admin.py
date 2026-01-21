"""Admin service functions for user, tournament, and registration management."""

import secrets
import string

from app.extensions import db
from app.models import User, Tournament, Registration, TournamentStatus


class AdminError(Exception):
    """Custom exception for admin operations."""
    pass


# ----- User Management -----

def get_all_users():
    """Get all users ordered by username."""
    return User.query.order_by(User.username).all()


def get_user_by_id(user_id):
    """Get a user by ID."""
    return User.query.get(user_id)


def update_user(user_id, username, email, tagline, avatar_path):
    """
    Update user fields.

    Args:
        user_id: ID of user to update
        username: New username
        email: New email
        tagline: New tagline (can be None)
        avatar_path: New avatar path (can be None)

    Returns:
        Updated user object

    Raises:
        AdminError: If user not found
    """
    user = User.query.get(user_id)
    if not user:
        raise AdminError('User not found.')

    user.username = username
    user.email = email.lower()
    user.tagline = tagline if tagline else None
    user.avatar_path = avatar_path if avatar_path else None

    db.session.commit()
    return user


def toggle_admin_status(user_id, current_user_id):
    """
    Toggle admin status for a user.

    Args:
        user_id: ID of user to toggle
        current_user_id: ID of admin performing the action

    Returns:
        Updated user object

    Raises:
        AdminError: If user not found or trying to demote self
    """
    if user_id == current_user_id:
        raise AdminError('Cannot change your own admin status.')

    user = User.query.get(user_id)
    if not user:
        raise AdminError('User not found.')

    user.is_admin = not user.is_admin
    db.session.commit()
    return user


def reset_user_password(user_id):
    """
    Generate and set a temporary password for a user.

    Args:
        user_id: ID of user to reset password

    Returns:
        Tuple of (user, temp_password)

    Raises:
        AdminError: If user not found
    """
    user = User.query.get(user_id)
    if not user:
        raise AdminError('User not found.')

    # Generate random password
    alphabet = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(alphabet) for _ in range(12))

    user.set_password(temp_password)
    db.session.commit()

    return user, temp_password


def delete_user(user_id, current_user_id):
    """
    Delete a user and their registrations.

    Args:
        user_id: ID of user to delete
        current_user_id: ID of admin performing the action

    Returns:
        Username of deleted user

    Raises:
        AdminError: If user not found or trying to delete self
    """
    if user_id == current_user_id:
        raise AdminError('Cannot delete your own account.')

    user = User.query.get(user_id)
    if not user:
        raise AdminError('User not found.')

    username = user.username

    # Delete user's registrations first
    Registration.query.filter_by(user_id=user_id).delete()

    # Delete user
    db.session.delete(user)
    db.session.commit()

    return username


# ----- Tournament Management -----

def update_tournament(tournament_id, name, description):
    """
    Update tournament details.

    Args:
        tournament_id: ID of tournament to update
        name: New tournament name
        description: New description (can be None)

    Returns:
        Updated tournament object

    Raises:
        AdminError: If tournament not found
    """
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        raise AdminError('Tournament not found.')

    tournament.name = name
    tournament.description = description if description else None

    db.session.commit()
    return tournament


# ----- Registration Management -----

def add_player_to_tournament(tournament_id, user_id):
    """
    Add a player to a tournament.

    Args:
        tournament_id: ID of tournament
        user_id: ID of user to add

    Returns:
        Created registration object

    Raises:
        AdminError: If tournament/user not found, not in registration phase,
                   or user already registered
    """
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        raise AdminError('Tournament not found.')

    if tournament.status != TournamentStatus.REGISTRATION.value:
        raise AdminError('Can only add players during registration phase.')

    user = User.query.get(user_id)
    if not user:
        raise AdminError('User not found.')

    # Check if already registered
    existing = Registration.query.filter_by(
        user_id=user_id,
        tournament_id=tournament_id
    ).first()
    if existing:
        raise AdminError(f'{user.username} is already registered.')

    registration = Registration(
        user_id=user_id,
        tournament_id=tournament_id
    )
    db.session.add(registration)
    db.session.commit()

    return registration


def remove_player_from_tournament(tournament_id, user_id):
    """
    Remove a player from a tournament.

    Args:
        tournament_id: ID of tournament
        user_id: ID of user to remove

    Returns:
        Username of removed player

    Raises:
        AdminError: If tournament not found, not in registration phase,
                   or user not registered
    """
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        raise AdminError('Tournament not found.')

    if tournament.status != TournamentStatus.REGISTRATION.value:
        raise AdminError('Can only remove players during registration phase.')

    registration = Registration.query.filter_by(
        user_id=user_id,
        tournament_id=tournament_id
    ).first()
    if not registration:
        raise AdminError('Player is not registered for this tournament.')

    username = registration.user.username
    db.session.delete(registration)
    db.session.commit()

    return username


def get_unregistered_users(tournament_id):
    """
    Get all users not registered for a tournament.

    Args:
        tournament_id: ID of tournament

    Returns:
        List of User objects not registered
    """
    registered_user_ids = db.session.query(Registration.user_id).filter_by(
        tournament_id=tournament_id
    ).subquery()

    return User.query.filter(
        ~User.id.in_(registered_user_ids)
    ).order_by(User.username).all()
