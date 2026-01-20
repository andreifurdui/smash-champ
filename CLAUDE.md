# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**.smash** - Office Table tennis championship app for ~20 users at .lumen.

Features: user registration, group stage (round-robin with double fixtures), Gauntlet playoffs, score submission with opponent confirmation, statistics.

**Full Specs**: See `smash-championship-plan.md` for detailed requirements, data models, and UI mockups.

**Brand**: .smash (styled lowercase with dot)
**Theme**: Mortal Kombat inspired - dark UI, fiery accents, dramatic VS displays
**URL**: `smash.lumen.local`

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Flask 3.x, SQLAlchemy 2.x, Flask-Login, Flask-WTF |
| Database | SQLite |
| Frontend | Jinja2, Tailwind CSS, Alpine.js |
| Server | Gunicorn + Nginx |

## Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Database
flask db init                    # First time only
flask db migrate -m "message"    # Create migration
flask db upgrade                 # Apply migrations

# Development
flask run --debug

# Create admin user (in flask shell)
flask shell
>>> from app.models import User
>>> from app.extensions import db
>>> u = User(email='admin@lumen.com', username='admin', is_admin=True)
>>> u.set_password('password')
>>> db.session.add(u); db.session.commit()
```

## Architecture

```
app/
├── __init__.py          # create_app() factory
├── config.py            # Config classes (Dev/Prod/Test)
├── extensions.py        # db, login_manager, migrate instances
├── models/              # User, Tournament, Registration, Match, SetScore
├── routes/              # Blueprints: auth, main, tournament, match, admin, stats, api
├── services/            # Business logic (tournament.py, match.py, standings.py, bracket.py, stats.py)
├── forms/               # Flask-WTF forms
├── templates/           # Jinja2 (base.html + components/ for reusables)
├── static/              # CSS, JS, img/default_avatars/
└── utils/               # decorators.py (admin_required), helpers, defaults.py
```

Routes are thin - business logic lives in `services/`. Templates extend `base.html`.

## Key Decisions (Do Not Change)

- **Playoff format**: Gauntlet (last place challenges up, all players qualify from group stage)
- **Score confirmation**: Submitter enters score, opponent confirms or disputes, 24h auto-confirm
- **Match format**: Best of 3 sets, first to 11 points per set, win by 2
- **Taglines**: 100 char max, random cringe defaults assigned if user doesn't provide one
- **Default avatars**: Auto-discovered from `static/img/default_avatars/` folder

## Data Models

- **User**: email, username, password_hash, avatar_path, tagline, is_admin
- **Tournament**: name, status (registration/group_stage/playoffs/completed), phase, playoff_format
- **Registration**: user_id, tournament_id, group stats (points, sets_won/lost, position)
- **Match**: tournament_id, player1_id, player2_id, phase (group/playoff), status, winner_id, submitted_by_id, confirmed_by_id
- **SetScore**: match_id, set_number, player1_score, player2_score

## Validation Rules

**Table Tennis Scoring**:
- Set win: First to 11, must win by 2 (deuce continues until 2-point lead)
- Match win: Best of 3 sets (first to win 2)

**Group Stage Tiebreakers** (in order):
1. Head-to-head record
2. Set difference (won - lost)
3. Point difference
4. Points scored

## Implementation Phases

| Phase | Focus | Status |
|-------|-------|--------|
| 0 | Project setup, models, migrations | ✅ Complete |
| 1 | Auth (register, login, profile) | ✅ Complete |
| 2 | Admin tournament management | ✅ Complete |
| 3 | User tournament registration, standings | ✅ Complete |
| 4 | Dashboard with VS cards | ✅ Complete |
| 5 | Score submission + confirmation flow | ✅ Complete |
| 6 | Gauntlet playoff bracket generation | ✅ Complete |
| 7 | Statistics pages | ✅ Complete |
| 8 | Polish + deployment | 🔜 Next |

**Current Status**: Phase 7 complete. Comprehensive statistics system implemented with global leaderboard, user stats pages, head-to-head comparisons, match history browser, and hall of fame. All service functions tested and working. Navigation integrated in navbar, dashboard, and profile pages. Ready for Phase 8 (Polish + Deployment).

## Coding Guidelines

1. **No over-engineering** - This serves ~20 users. Simple > clever.
2. **Flat > nested** - Avoid deep inheritance or abstraction layers.
3. **Obvious > short** - Readability matters more than line count.
4. **Routes stay thin** - Complex logic goes in `services/`.
5. **No raw SQL** - Let SQLAlchemy handle it.

```python
# YES: Direct and readable
def get_user_matches(user_id: int, limit: int = 10) -> list[Match]:
    return Match.query.filter(
        (Match.player1_id == user_id) | (Match.player2_id == user_id)
    ).order_by(Match.played_at.desc()).limit(limit).all()

# NO: Over-abstracted
class MatchQueryBuilder:
    def __init__(self): ...
    def for_user(self, user_id): ...
    def build(self): ...
```

## Documentation Rules

**NEVER create status reports, completion documents, or summary files after implementing features.** Instead:
1. Update `smash-championship-plan.md` to check off completed items
2. Update this `CLAUDE.md` file to reflect current implementation status
3. Keep both files as the single source of truth

## When in Doubt

1. Check `smash-championship-plan.md` for detailed specs
2. Keep it simple - this is a fun office app, not enterprise software
3. Make it work first, optimize later
