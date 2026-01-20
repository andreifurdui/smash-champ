"""Default taglines for users who don't provide their own."""

import random
from app.utils.avatars import get_default_avatars

DEFAULT_TAGLINES = [
    "Fear the paddle.",
    "I came, I saw, I served.",
    "Ping pong wizard in training.",
    "Smashing expectations since day one.",
    "Warning: May cause sudden defeat.",
    "Born to spin, forced to work.",
    "Have paddle, will travel.",
    "Underestimate me. That'll be fun.",
    "I don't always play ping pong, but when I do, I win.",
    "Paddle diplomacy is my specialty.",
    "In ping pong we trust.",
    "Making opponents cry since registration.",
    "Float like a butterfly, smash like thunder.",
    "Professional ball whacker.",
    "Trained by watching YouTube videos.",
    "Here for the free snacks and glory.",
    "My backhand is my personality.",
    "Plot twist: I'm actually good.",
    "Ready to crush dreams and serve aces.",
    "Legends don't retire, they play ping pong.",
]


def get_random_tagline():
    """Return a random tagline from the default list."""
    return random.choice(DEFAULT_TAGLINES)


def get_random_avatar():
    """Return a random avatar path from available default avatars."""
    avatars = get_default_avatars()
    if avatars:
        return random.choice(avatars)
    # Fallback to a simple default if no avatars found
    return '/static/img/default_avatar.svg'
