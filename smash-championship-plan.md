# .smash - Technical Reference

> **Project**: .smash (styled lowercase with dot, like parent company .lumen)
> **URL**: smash.muncher.lumen.lan
> **Users**: ~20 internal users at .lumen

---

## Overview

**.smash** is a lightweight web application for managing table tennis tournaments at .lumen. Features include user registration with avatars/taglines, group stage round-robin with double fixtures, Gauntlet playoffs, score submission with opponent confirmation, and statistics tracking.

### Design Philosophy
- **Mortal Kombat aesthetic**: Dark theme, dramatic VS presentations, fiery accents
- **Mobile-first for interactions**: Score submission designed for phone use at the table
- **Simple over clever**: This serves ~20 users, no over-engineering

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Flask 3.x, SQLAlchemy 2.x, Flask-Login, Flask-WTF |
| Database | SQLite |
| Frontend | Jinja2, Tailwind CSS, Alpine.js |
| Server | Gunicorn + Nginx + systemd |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         NGINX                                    │
│              (smash.muncher.lumen.lan:80)                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       GUNICORN (127.0.0.1:8000)                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FLASK APP                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Routes    │  │   Models    │  │  Templates  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Forms     │  │  Services   │  │   Utils     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SQLite (instance/smash.db)                    │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure

```
app/
├── __init__.py          # create_app() factory with error handlers
├── config.py            # Config classes (Dev/Prod/Test)
├── extensions.py        # db, login_manager, migrate instances
├── models/              # User, Tournament, Registration, Match, SetScore
├── routes/              # Blueprints: auth, main, tournament, match, admin, stats
├── services/            # Business logic (tournament, match, standings, bracket, stats)
├── forms/               # Flask-WTF forms
├── templates/           # Jinja2 (base.html + auth/, main/, admin/, etc.)
├── static/              # CSS, JS, img/default_avatars/, avatars/
└── utils/               # decorators.py, helpers.py, defaults.py, avatars.py
```

---

## Data Models

### Entity Relationships

```
User ──┬── Registration ──── Tournament
       │        │
       │        └── group stats (points, sets_won/lost, position)
       │
       └── Match ──── SetScore
              │
              └── player1, player2, winner, submitted_by, confirmed_by
```

### Key Models

**User**: email, username, password_hash, avatar_path, tagline, is_admin

**Tournament**: name, status (registration/group_stage/playoffs/completed), playoff_format

**Registration**: user_id, tournament_id, group_points, sets_won/lost, points_won/lost, group_position

**Match**: tournament_id, player1_id, player2_id, phase (group/playoff), status, winner_id, submitted_by_id, confirmed_by_id

**SetScore**: match_id, set_number, player1_score, player2_score

---

## Tournament Format

### Group Stage
- **Round-robin with double fixtures**: Every player plays every other player twice
- **Points**: Win = 2, Loss = 1, Walkover Loss = 0
- **Tiebreakers** (in order): Head-to-head → Set difference → Point difference → Points scored

### Gauntlet Playoffs
All players qualify. Last place challenges second-to-last, winner challenges third-to-last, and so on until the champion is determined.

```
R1: #4 vs #3 → Winner
R2: Winner vs #2 → Winner
R3: Winner vs #1 → CHAMPION
```

---

## User Flows

### Score Submission Flow

```
SCHEDULED → (player submits) → PENDING_CONFIRMATION
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
         CONFIRMED              DISPUTED               AUTO-CONFIRM
      (opponent confirms)    (opponent disputes)      (24h timeout)
              │                       │                       │
              └───────────────────────┴───────────────────────┘
                                      │
                                      ▼
                               Stats Updated
                          (if playoff: winner advances)
```

### Score Validation Rules
- **Set win**: First to 11 points, must win by 2 (deuce continues: 12-10, 15-13, etc.)
- **Match win**: Best of 3 sets (first to win 2)

---

## Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Landing page |
| `/auth/register` | GET/POST | User registration |
| `/auth/login` | GET/POST | Login |
| `/auth/logout` | GET | Logout |
| `/auth/profile` | GET | View profile |
| `/auth/profile/edit` | GET/POST | Edit profile |
| `/dashboard` | GET | Main dashboard |
| `/tournament/` | GET | Tournament list |
| `/tournament/<id>` | GET | Tournament detail |
| `/tournament/<id>/register` | POST | Register for tournament |
| `/match/<id>/submit` | GET/POST | Submit score |
| `/match/<id>/confirm` | POST | Confirm score |
| `/match/<id>/dispute` | POST | Dispute score |
| `/stats/` | GET | Global leaderboard |
| `/stats/user/<username>` | GET | User statistics |
| `/stats/head-to-head` | GET | H2H comparison |
| `/stats/matches` | GET | Match history |
| `/admin/` | GET | Admin dashboard |
| `/admin/tournament/create` | GET/POST | Create tournament |
| `/admin/tournament/<id>` | GET | Manage tournament |

---

## UI Design

### Color Palette (Mortal Kombat Theme)

```css
--mk-fire: #F97316;        /* Orange - primary accent */
--mk-fire-dark: #EA580C;   /* Darker orange - hover */
--mk-dark: #0F0F0F;        /* Deepest black - main bg */
--mk-darker: #171717;      /* Card backgrounds */
--mk-darkest: #262626;     /* Elevated surfaces */
--color-win: #22C55E;      /* Green - victory */
--color-loss: #EF4444;     /* Red - defeat */
--color-pending: #EAB308;  /* Yellow - pending */
```

---

## Deployment

### Quick Commands

```bash
# Development
source venv/bin/activate && flask run --debug

# Production deployment
sudo ./deploy.sh

# Manual service control
sudo systemctl restart smash
sudo systemctl reload nginx
```

### Environment Variables
- `SECRET_KEY`: Required in production (auto-generated by deploy.sh)
- `DATABASE_URL`: SQLite path (default: instance/smash.db)

---

## Default Content

### Taglines (assigned randomly if user doesn't provide one)

```python
DEFAULT_TAGLINES = [
    "I came here to play ping pong and eat snacks... and I'm all out of snacks.",
    "My backhand is almost as strong as my coffee addiction.",
    "They call me 'The Server'... because I work in IT.",
    "Statistically, I have a 50% chance of winning. Emotionally, 0%.",
    "I put the 'ping' in 'crying'.",
    "My strategy? Hoping the ball goes where I want it to.",
    "Powered by anxiety and vending machine snacks.",
    "I'm not saying I'm the best, but my mom thinks I'm special.",
    # ... and more in app/utils/defaults.py
]
```

### Default Avatars
Drop images into `app/static/img/default_avatars/` - they're auto-discovered. Supported formats: PNG, JPG, JPEG, GIF, WEBP.

---

## Future Enhancements & TODOs

### High Priority

| Feature | Description |
|---------|-------------|
| **Auto-confirmation scheduler** | Automatically confirm scores after 24 hours if opponent hasn't responded. Requires APScheduler setup. |
| **Admin score override** | Allow admins to edit/resolve disputed scores. UI exists in admin, needs route implementation. |
| **Single elimination playoffs** | Alternative playoff format with seeded bracket. Models support it, needs bracket generation service. |

### Medium Priority

| Feature | Description |
|---------|-------------|
| **Email notifications** | Weekly digests, match reminders, score confirmation requests. Flask-Mail configured but not implemented. |
| **Win rate over time** | Chart showing user's performance trend. Stats service partially supports this. |
| **Interesting stats** | Longest match, biggest comeback, most deuce points, etc. |
| **Animations/transitions** | CSS animations for VS reveals, score submissions, bracket progression. |
| **Loading states** | Skeleton loaders for async operations. |

### Low Priority (Post-V1)

| Feature | Description |
|---------|-------------|
| **Real-time updates** | WebSocket support for live score updates. Nginx config already has WebSocket headers. |
| **Double elimination playoffs** | Losers bracket format. Complex bracket management. |
| **Multiple groups** | Support for larger tournaments with multiple round-robin groups. |
| **Season/league system** | Track standings across multiple tournaments. |
| **Achievement badges** | Unlock badges for milestones (first win, 10 wins, tournament champion, etc.). |
| **Match scheduling calendar** | Calendar view for upcoming matches with scheduling. |
| **Spectator mode** | Public viewing of live matches without login. |
| **Match commentary** | Allow players to add comments/reactions to matches. |
| **Rating/ELO system** | Skill-based matchmaking and rankings. Could add to Registration model. |
| **API for mobile app** | REST/JSON endpoints for potential mobile client. Routes already support JSON responses. |

### Known Limitations

| Item | Notes |
|------|-------|
| **Head-to-head tiebreaker** | Simplified implementation - doesn't handle complex multi-way ties |
| **Query optimization** | N+1 queries in some list views - acceptable for ~20 users |
| **Static files via Flask** | Nginx static serving disabled due to home directory permissions |

---

## Quick Reference

### Create Admin User

```bash
flask shell
>>> from app.models import User
>>> from app.extensions import db
>>> u = User(email='admin@lumen.com', username='admin', is_admin=True)
>>> u.set_password('your-password')
>>> db.session.add(u); db.session.commit()
```

### Database Commands

```bash
flask db init           # First time only
flask db migrate -m "message"
flask db upgrade
```

### Service Management

```bash
sudo systemctl status smash
sudo systemctl restart smash
sudo journalctl -u smash -f   # View logs
```
