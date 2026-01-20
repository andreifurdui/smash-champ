"""Avatar utilities for default avatar handling."""

import os
import random
from pathlib import Path


def get_default_avatars():
    """Get list of available default avatar filenames."""
    avatars_dir = Path(__file__).parent.parent / 'static' / 'img' / 'default_avatars'
    if not avatars_dir.exists():
        return []

    valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    avatars = []
    for f in avatars_dir.iterdir():
        if f.is_file() and f.suffix.lower() in valid_extensions:
            avatars.append(f.name)
    return sorted(avatars)


def get_random_default_avatar(seed=None):
    """Get a random default avatar path, seeded by user ID for consistency."""
    avatars = get_default_avatars()
    if not avatars:
        return '/static/img/default_avatar.svg'

    if seed is not None:
        random.seed(seed)
    avatar = random.choice(avatars)
    return f'/static/img/default_avatars/{avatar}'
