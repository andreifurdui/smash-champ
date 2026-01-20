# CLAUDE.md - Project Guide for Claude Code

> **Project**: .smash - Office Table Tennis Championship App
> **Full Plan**: See `smash-championship-plan.md` for complete details

---

## Quick Overview

A Flask web app for managing table tennis tournaments at work (~20 users). Features user registration, group stage (round-robin), Gauntlet playoffs, score submission with confirmation, and statistics.

**Brand**: .smash (styled lowercase with dot, like parent company .lumen)
**Design Theme**: Mortal Kombat inspired - dark UI, fiery accents, dramatic VS displays.
**URL**: `smash.lumen.local` (internal server)

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Flask 3.x, SQLAlchemy 2.x, Flask-Login |
| Database | SQLite |
| Frontend | Jinja2, Tailwind CSS, Alpine.js |
| Server | Gunicorn + Nginx |

---

## Project Structure

```
smash/
├── app/
│   ├── __init__.py          # App factory
│   ├── config.py            # Config classes
│   ├── extensions.py        # Flask extensions
│   ├── models/              # SQLAlchemy models
│   ├── routes/              # Blueprints (auth, main, tournament, match, admin, stats, api)
│   ├── services/            # Business logic
│   ├── forms/               # Flask-WTF forms
│   ├── templates/           # Jinja2 templates
│   ├── static/              # CSS, JS, images
│   └── utils/               # Helpers, decorators
├── migrations/              # Flask-Migrate
├── instance/                # SQLite DB (smash.db)
├── requirements.txt
└── run.py
```

---

## Key Decisions (Do Not Change)

- **Playoff format**: Gauntlet (last place challenges up, all players qualify)
- **Score confirmation**: Submitter + opponent confirmation, 24h auto-confirm
- **Taglines**: 100 char max, random cringe defaults if empty
- **Avatars**: Auto-discovered from `static/img/default_avatars/`

---

## Coding Guidelines

### Favor Simplicity

1. **No over-engineering**. This app serves ~20 users. Simple > clever.

2. **Flat is better than nested**. Avoid deep inheritance or abstraction layers.

3. **One file, one purpose**. Keep modules focused and small.

4. **Obvious code > short code**. Readability matters more than line count.

5. **Minimal dependencies**. Only add packages when truly needed.

### Python Style

```python
# YES: Simple, readable
def get_user_matches(user_id: int, limit: int = 10) -> list[Match]:
    return Match.query.filter(
        (Match.player1_id == user_id) | (Match.player2_id == user_id)
    ).order_by(Match.played_at.desc()).limit(limit).all()

# NO: Over-abstracted
class MatchQueryBuilder:
    def __init__(self): ...
    def for_user(self, user_id): ...
    def with_limit(self, limit): ...
    def build(self): ...
```

### Flask Patterns

- Use **application factory** (`create_app()`)
- Use **blueprints** for route organization
- Keep routes thin - business logic goes in `services/`
- Use **Flask-WTF** for all forms (CSRF protection)

### Database

- Let SQLAlchemy handle relationships
- Use `db.session` context properly
- Index frequently queried columns
- No raw SQL unless absolutely necessary

### Templates

- Extend `base.html` for all pages
- Use `components/` for reusable partials
- Keep logic minimal - compute in views, display in templates

### JavaScript

- Alpine.js for interactivity - no heavy frameworks
- Vanilla JS for simple DOM manipulation
- No build step required for JS

---

## Implementation Phases

| Phase | Focus | Key Files |
|-------|-------|-----------|
| 0 | Setup | `__init__.py`, `config.py`, `models/` |
| 1 | Auth | `routes/auth.py`, `forms/auth.py`, `templates/auth/` |
| 2 | Admin Tournaments | `routes/admin.py`, `services/tournament.py` |
| 3 | User Tournament Flow | `routes/tournament.py`, `templates/tournament/` |
| 4 | Dashboard | `routes/main.py`, `templates/main/dashboard.html` |
| 5 | Score Submission | `routes/match.py`, `services/match.py` |
| 6 | Gauntlet Playoffs | `services/bracket.py`, `templates/components/bracket.html` |
| 7 | Statistics | `routes/stats.py`, `services/stats.py` |
| 8 | Polish & Deploy | `gunicorn.conf.py`, nginx config |

---

## Quick Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Database
flask db init
flask db migrate -m "message"
flask db upgrade

# Run dev server
flask run --debug

# Create admin (in flask shell)
flask shell
>>> u = User(email='admin@lumen.com', username='admin', is_admin=True)
>>> u.set_password('password')
>>> db.session.add(u); db.session.commit()
```

---

## Models Summary

- **User**: email, username, password_hash, avatar_path, tagline, is_admin
- **Tournament**: name, status, phase, playoff_format (gauntlet)
- **Registration**: user + tournament link, stats (points, sets, position)
- **Match**: player1, player2, status, winner, phase (group/playoff)
- **SetScore**: match_id, set_number, player1_score, player2_score

---

## Validation Rules

### Table Tennis Scoring
- Set win: First to 11, must win by 2
- Deuce: 10-10 → must win by 2 (e.g., 12-10, 15-13)
- Match win: Best of 3 sets (first to 2)

### Tiebreakers (Group Stage)
1. Head-to-head
2. Set difference
3. Point difference
4. Points scored

---

## When in Doubt

1. Check `smash-championship-plan.md` for detailed specs
2. Keep it simple
3. Make it work first, optimize later
4. Ask if requirements are unclear

---

*Remember: This is a fun office app, not enterprise software. Ship it!* 🏓
