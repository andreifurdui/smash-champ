# .smash - Table Tennis Championship Web App - Technical Planning Document

> **Project**: .smash (styled lowercase with dot, like parent company .lumen)
> **Version:** 1.0
> **Last Updated:** January 20, 2026
> **Implementation Status:** Phase 0 ✅ | Phase 1 ✅ | Phase 2 ✅ | Phase 3 Ready to Start

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Technical Stack](#2-technical-stack)
3. [Architecture Overview](#3-architecture-overview)
4. [Data Models & Database Schema](#4-data-models--database-schema)
5. [Tournament Format Design](#5-tournament-format-design)
6. [API Routes & Endpoints](#6-api-routes--endpoints)
7. [User Interface Design](#7-user-interface-design)
8. [Authentication & Authorization](#8-authentication--authorization)
9. [Score Submission & Confirmation System](#9-score-submission--confirmation-system)
10. [Email Notification System](#10-email-notification-system)
11. [Deployment Configuration](#11-deployment-configuration)
12. [Implementation Phases](#12-implementation-phases)
13. [File Structure](#13-file-structure)
14. [Open Questions & Decisions](#14-open-questions--decisions)

---

## 1. Executive Summary

### Project Overview
**.smash** is a lightweight, internal web application for managing table tennis tournaments at .lumen. Features include user registration, tournament management, match scheduling, score submission with confirmation, and statistics tracking.

### Key Features
- User registration with avatars and taglines (Mortal Kombat style)
- Group stage with round-robin (double fixtures)
- Playoff phase with configurable format (Gauntlet or Traditional Bracket)
- Score submission with two-player confirmation flow
- Admin panel for tournament management
- Statistics and history tracking
- Mobile-responsive design optimized for score submissions
- Weekly email digest (future enhancement)

### Design Philosophy
- **Mortal Kombat aesthetic**: Dark theme, dramatic VS presentations, fiery accents
- **Minimal but beautiful**: Clean layouts, purposeful animations
- **Mobile-first for interactions**: Score submission designed for phone use at the table

---

## 2. Technical Stack

### Backend
| Component | Technology | Rationale |
|-----------|------------|-----------|
| Framework | **Flask 3.x** | Simple, lightweight, perfect for ~20 users |
| Database | **SQLite** | Zero config, sufficient for low concurrency |
| ORM | **SQLAlchemy 2.x** | Pythonic, great Flask integration |
| Auth | **Flask-Login** | Simple session management |
| Forms | **Flask-WTF** | CSRF protection, validation |
| Migrations | **Flask-Migrate** (Alembic) | Schema versioning |
| Email | **Flask-Mail** | SMTP integration (future) |

### Frontend
| Component | Technology | Rationale |
|-----------|------------|-----------|
| Templates | **Jinja2** | Native Flask, server-side rendering |
| CSS | **Tailwind CSS 3.x** | Utility-first, rapid styling |
| Icons | **Heroicons** or **Lucide** | Clean, consistent iconography |
| JS Framework | **Alpine.js** | Lightweight reactivity (~15kb) |
| Animations | **CSS + minimal JS** | Smooth transitions, dramatic reveals |

### Development & Deployment
| Component | Technology |
|-----------|------------|
| Package Manager | **pip + venv** |
| Web Server | **Gunicorn** |
| Reverse Proxy | **Nginx** |
| Process Manager | **systemd** |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         NGINX                                    │
│                   (smash.lumen.local)                            │
│                    Reverse Proxy + Static Files                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       GUNICORN                                   │
│                  (WSGI Application Server)                       │
│                    Workers: 2-4                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FLASK APP                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Routes    │  │   Models    │  │  Templates  │             │
│  │  (Views)    │  │ (SQLAlchemy)│  │  (Jinja2)   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Forms     │  │  Services   │  │   Utils     │             │
│  │ (Flask-WTF) │  │  (Business) │  │  (Helpers)  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       SQLite DB                                  │
│                    (smash.db file)                               │
└─────────────────────────────────────────────────────────────────┘
```

### Request Flow
1. User requests `smash.lumen.local/dashboard`
2. Nginx receives request, proxies to Gunicorn
3. Gunicorn worker handles request via Flask app
4. Flask route renders template with data from SQLite
5. HTML response returned through the chain

---

## 4. Data Models & Database Schema

### Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│    User      │       │   Tournament     │       │    Match     │
├──────────────┤       ├──────────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)          │       │ id (PK)      │
│ email (UQ)   │       │ name             │       │ tournament_id│───┐
│ username (UQ)│       │ description      │       │ player1_id   │───┼──┐
│ password_hash│       │ status           │       │ player2_id   │───┼──┤
│ avatar_path  │       │ phase            │       │ phase        │   │  │
│ tagline      │       │ playoff_format   │       │ group_number │   │  │
│ is_admin     │       │ created_at       │       │ bracket_round│   │  │
│ created_at   │       │ started_at       │       │ bracket_pos  │   │  │
│ updated_at   │       │ completed_at     │       │ scheduled_at │   │  │
└──────┬───────┘       └────────┬─────────┘       │ played_at    │   │  │
       │                        │                 │ status       │   │  │
       │                        │                 │ submitted_by │───┼──┤
       │  ┌─────────────────────┘                 │ confirmed_by │───┼──┤
       │  │                                       │ created_at   │   │  │
       │  │  ┌────────────────────────────────────┴──────────────┘   │  │
       │  │  │                                                       │  │
       │  ▼  ▼                                                       │  │
       │ ┌──────────────────┐                                        │  │
       │ │  Registration    │                                        │  │
       │ ├──────────────────┤                                        │  │
       │ │ id (PK)          │                                        │  │
       └►│ user_id (FK)     │                                        │  │
         │ tournament_id(FK)│◄───────────────────────────────────────┘  │
         │ seed             │                                           │
         │ group_number     │                                           │
         │ group_points     │                                           │
         │ group_position   │                                           │
         │ sets_won         │                                           │
         │ sets_lost        │                                           │
         │ points_won       │                                           │
         │ points_lost      │                                           │
         │ eliminated       │                                           │
         │ final_position   │                                           │
         │ registered_at    │                                           │
         └──────────────────┘                                           │
                                                                        │
┌──────────────────┐                                                    │
│    SetScore      │                                                    │
├──────────────────┤                                                    │
│ id (PK)          │                                                    │
│ match_id (FK)    │────────────────────────────────────────────────────┤
│ set_number       │                                                    │
│ player1_score    │                                                    │
│ player2_score    │                                                    │
└──────────────────┘                                                    │
                                                                        │
┌──────────────────┐                                                    │
│ TournamentWinner │                                                    │
├──────────────────┤                                                    │
│ id (PK)          │                                                    │
│ tournament_id(FK)│                                                    │
│ user_id (FK)     │◄───────────────────────────────────────────────────┘
│ position (1,2,3) │
│ awarded_at       │
└──────────────────┘
```

### Model Definitions

```python
# models.py

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar_path = db.Column(db.String(256))  # None = assign random default on access
    tagline = db.Column(db.String(100))  # None = assign random cringe tagline on access
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    registrations = db.relationship('Registration', back_populates='user')
    matches_as_player1 = db.relationship('Match', foreign_keys='Match.player1_id')
    matches_as_player2 = db.relationship('Match', foreign_keys='Match.player2_id')
    
    @property
    def display_tagline(self) -> str:
        """Returns user's tagline or a random cringe default."""
        if self.tagline:
            return self.tagline
        # Import here to avoid circular imports
        from app.utils.defaults import get_random_default_tagline
        return get_random_default_tagline(seed=self.id)  # Consistent per user
    
    @property
    def display_avatar(self) -> str:
        """Returns user's avatar path or a random default."""
        if self.avatar_path:
            return f'/static/avatars/{self.avatar_path}'
        from app.utils.avatars import get_random_default_avatar, get_default_avatar_path
        return get_default_avatar_path(get_random_default_avatar())


class Tournament(db.Model):
    __tablename__ = 'tournaments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='registration')
    # Status: registration, group_stage, playoffs, completed, cancelled
    phase = db.Column(db.String(20), default='registration')
    # Phase: registration, group, playoff_round_N, final, completed
    playoff_format = db.Column(db.String(20), default='gauntlet')
    # Format: gauntlet (default), single_elimination (future option)
    # Note: All players advance to playoffs in Gauntlet format
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    registrations = db.relationship('Registration', back_populates='tournament')
    matches = db.relationship('Match', back_populates='tournament')
    winners = db.relationship('TournamentWinner', back_populates='tournament')


class Registration(db.Model):
    __tablename__ = 'registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    seed = db.Column(db.Integer)  # Assigned after group stage
    group_number = db.Column(db.Integer, default=1)  # For multiple groups
    group_points = db.Column(db.Integer, default=0)  # 2 for win, 1 for loss, 0 for walkover loss
    group_position = db.Column(db.Integer)  # Calculated after group stage
    sets_won = db.Column(db.Integer, default=0)
    sets_lost = db.Column(db.Integer, default=0)
    points_won = db.Column(db.Integer, default=0)  # Total points scored
    points_lost = db.Column(db.Integer, default=0)  # Total points conceded
    eliminated = db.Column(db.Boolean, default=False)
    final_position = db.Column(db.Integer)  # Final tournament standing
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='registrations')
    tournament = db.relationship('Tournament', back_populates='registrations')
    
    # Unique constraint: one registration per user per tournament
    __table_args__ = (
        db.UniqueConstraint('user_id', 'tournament_id', name='unique_user_tournament'),
    )


class Match(db.Model):
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    player1_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    phase = db.Column(db.String(20), nullable=False)  # group, playoff
    group_number = db.Column(db.Integer)  # For group stage
    fixture_number = db.Column(db.Integer)  # 1 = first meeting, 2 = return fixture
    bracket_round = db.Column(db.Integer)  # For playoffs: 1, 2, 3... (gauntlet steps)
    bracket_position = db.Column(db.Integer)  # Position in bracket
    scheduled_at = db.Column(db.DateTime)
    played_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='scheduled')
    # Status: scheduled, pending_confirmation, confirmed, disputed, cancelled, walkover
    winner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    submitted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    submitted_at = db.Column(db.DateTime)
    confirmed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    confirmed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tournament = db.relationship('Tournament', back_populates='matches')
    player1 = db.relationship('User', foreign_keys=[player1_id])
    player2 = db.relationship('User', foreign_keys=[player2_id])
    winner = db.relationship('User', foreign_keys=[winner_id])
    submitted_by = db.relationship('User', foreign_keys=[submitted_by_id])
    confirmed_by = db.relationship('User', foreign_keys=[confirmed_by_id])
    sets = db.relationship('SetScore', back_populates='match', order_by='SetScore.set_number')


class SetScore(db.Model):
    __tablename__ = 'set_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    set_number = db.Column(db.Integer, nullable=False)  # 1, 2, 3
    player1_score = db.Column(db.Integer, nullable=False)
    player2_score = db.Column(db.Integer, nullable=False)
    
    # Relationships
    match = db.relationship('Match', back_populates='sets')
    
    __table_args__ = (
        db.UniqueConstraint('match_id', 'set_number', name='unique_match_set'),
    )


class TournamentWinner(db.Model):
    __tablename__ = 'tournament_winners'
    
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False)  # 1 = champion, 2 = runner-up, 3 = third
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tournament = db.relationship('Tournament', back_populates='winners')
    user = db.relationship('User')
```

### Database Indexes

```python
# Additional indexes for query optimization
# Add in migrations

# Fast user lookup
Index('idx_user_email', User.email)
Index('idx_user_username', User.username)

# Tournament queries
Index('idx_tournament_status', Tournament.status)

# Match queries (most frequent)
Index('idx_match_tournament_phase', Match.tournament_id, Match.phase)
Index('idx_match_player1', Match.player1_id)
Index('idx_match_player2', Match.player2_id)
Index('idx_match_status', Match.status)

# Registration queries
Index('idx_registration_tournament', Registration.tournament_id)
Index('idx_registration_user', Registration.user_id)
```

---

## 5. Tournament Format Design

### Overview

Each tournament consists of two phases:
1. **Group Stage**: Round-robin with double fixtures (home and away)
2. **Playoff Stage**: Configurable format

### Group Stage

#### Round-Robin Double Fixtures
- Every player plays every other player **twice**
- Total matches per player: `2 * (n - 1)` where n = number of players
- Total matches in tournament group stage: `n * (n - 1)`

#### Points System
| Result | Points |
|--------|--------|
| Win | 2 |
| Loss | 1 |
| Walkover Loss | 0 |

> **Note**: Originally planned as 3-1-0, implemented as 2-1-0 for simpler scoring with no draws in table tennis.

#### Tiebreaker Rules (in order)
1. **Head-to-head record** between tied players
2. **Set difference** (sets won - sets lost)
3. **Point difference** (points won - points lost)
4. **Points scored** (total points won)
5. **Random draw** (if still tied)

#### Example Group Table
```
┌──────┬──────────────┬────┬───┬───┬────────┬────────┬─────┐
│ Pos  │ Player       │ P  │ W │ L │ Sets   │ Points │ Pts │
├──────┼──────────────┼────┼───┼───┼────────┼────────┼─────┤
│ 1    │ DragonSlayer │ 6  │ 5 │ 1 │ 10-3   │ 112-78 │ 11  │
│ 2    │ PaddleMaster │ 6  │ 4 │ 2 │ 9-5    │ 105-82 │ 10  │
│ 3    │ SpinKing     │ 6  │ 3 │ 3 │ 7-7    │ 95-91  │ 9   │
│ 4    │ TableTitan   │ 6  │ 0 │ 6 │ 2-12   │ 64-125 │ 6   │
└──────┴──────────────┴────┴───┴───┴────────┴────────┴─────┘

Note: Pts = (Wins × 2) + (Losses × 1)
```

### Playoff Stage

#### Option A: Gauntlet Format (Recommended) ⭐

**Description**: The last-place player challenges the second-to-last. Winner challenges third-to-last, and so on until the champion is determined.

**Visualization**:
```
Group Stage Final Standings:
1. DragonSlayer (Champion's advantage - plays last)
2. PaddleMaster
3. SpinKing
4. TableTitan (Starts the gauntlet)

Gauntlet Progression:
                                                    ┌─────────────────┐
                                                    │  CHAMPIONSHIP   │
                                                    │    FINAL        │
                                    ┌───────────────┤                 │
                                    │               │ DragonSlayer vs │
                                    │               │    Winner R2    │
                        ┌───────────┴───────────┐   └─────────────────┘
                        │      ROUND 2          │
            ┌───────────┤                       │
            │           │ PaddleMaster vs       │
            │           │    Winner R1          │
┌───────────┴───────────┴───────────────────────┘
│         ROUND 1
│
│  TableTitan vs SpinKing
│  (4th vs 3rd)
│
└─────────────────────────────────────────────────

Match Flow:
R1: #4 TableTitan vs #3 SpinKing → Winner advances
R2: Winner of R1 vs #2 PaddleMaster → Winner advances  
R3: Winner of R2 vs #1 DragonSlayer → CHAMPION
```

**Pros**:
- Everyone has a theoretical path to victory
- Higher seeds rewarded with fewer matches and fresher legs
- Dramatic comeback potential creates excitement
- Simpler bracket structure

**Cons**:
- Top seed might only play 1 match
- Lower seeds have a harder path (more matches, fatigue)

**Match Count**: `n - 1` matches total (where n = players)

---

#### Option B: Traditional Seeded Single Elimination

**Description**: Top N players qualify, seeded into a bracket (1 vs 8, 2 vs 7, etc.)

**Visualization** (8-player example):
```
                    ┌─────────────────┐
                    │     FINAL       │
            ┌───────┤                 ├───────┐
            │       └─────────────────┘       │
     ┌──────┴──────┐               ┌──────────┴────┐
     │  SEMI 1     │               │    SEMI 2     │
   ┌─┤             ├─┐           ┌─┤               ├─┐
   │ └─────────────┘ │           │ └───────────────┘ │
┌──┴──┐          ┌───┴─┐     ┌───┴──┐          ┌────┴─┐
│QF 1 │          │QF 2 │     │ QF 3 │          │ QF 4 │
├─────┤          ├─────┤     ├──────┤          ├──────┤
│#1   │          │#4   │     │#3    │          │#2    │
│ vs  │          │ vs  │     │ vs   │          │ vs   │
│#8   │          │#5   │     │#6    │          │#7    │
└─────┘          └─────┘     └──────┘          └──────┘
```

**Pros**:
- Traditional, well-understood format
- Equal number of matches for all participants at each round
- Clear bracket progression

**Cons**:
- Bottom players eliminated immediately
- Requires power-of-2 players (or byes)
- Less dramatic for lower-ranked players

**Match Count**: 
- Quarter-finals: 4 matches
- Semi-finals: 2 matches
- Final: 1 match
- Third-place match: 1 match (optional)
- Total: 7-8 matches

---

#### Option C: Double Elimination

**Description**: Losers get a second chance through a losers bracket.

**Pros**:
- Most forgiving - everyone gets at least 2 matches
- More total matches (more fun)

**Cons**:
- Complex bracket management
- Significantly longer tournament duration
- Can feel confusing to track

**Recommendation**: Skip for V1, consider for future enhancement.

---

### Playoff Format Comparison Matrix

| Criteria | Gauntlet | Single Elimination |
|----------|----------|-------------------|
| Excitement for lower seeds | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Fairness for top seeds | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Number of matches | Minimal (n-1) | Moderate |
| Implementation complexity | Simple | Moderate |
| Bracket visualization | Simple linear | Tree structure |
| Comeback potential | High | Low |
| Best for small groups (≤8) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Best for large groups (>8) | ⭐⭐⭐ | ⭐⭐⭐⭐ |

### Recommended Configuration Options

```python
class PlayoffFormat(Enum):
    GAUNTLET = "gauntlet"  # Default
    SINGLE_ELIMINATION = "single_elimination"
    
# Tournament creation form should offer:
# - Playoff format selection
# - Number of qualifiers (0 = all qualify)
# - Third-place match option (for single elimination)
```

---

## 6. API Routes & Endpoints

### Route Structure

```
/                           # Landing page / redirect
/auth/
    /login                  # GET, POST
    /register               # GET, POST
    /logout                 # GET
    /forgot-password        # GET, POST (future)

/dashboard                  # Main user dashboard (GET)

/profile/
    /                       # View own profile (GET)
    /edit                   # Edit profile (GET, POST)
    /<username>             # View other user's profile (GET)

/tournament/
    /                       # List all tournaments (GET)
    /create                 # Admin: create tournament (GET, POST)
    /<id>/                  # Tournament detail (GET)
    /<id>/register          # Register for tournament (POST)
    /<id>/unregister        # Unregister from tournament (POST)
    /<id>/standings         # View standings (GET)
    /<id>/bracket           # View playoff bracket (GET)
    /<id>/matches           # List all matches (GET)

/match/
    /<id>/                  # Match detail (GET)
    /<id>/submit            # Submit score (GET, POST)
    /<id>/confirm           # Confirm score (POST)
    /<id>/dispute           # Dispute score (POST)

/admin/
    /                       # Admin dashboard (GET)
    /tournament/<id>/
        /start-group        # Start group stage (POST)
        /start-playoffs     # Start playoff stage (POST)
        /complete           # Complete tournament (POST)
        /cancel             # Cancel tournament (POST)
    /match/<id>/
        /edit               # Edit match score (GET, POST)
        /resolve-dispute    # Resolve disputed score (POST)
        /set-walkover       # Set walkover result (POST)
    /user/
        /                   # List users (GET)
        /<id>/toggle-admin  # Toggle admin status (POST)

/stats/
    /                       # Overall statistics (GET)
    /user/<username>        # User statistics (GET)
    /head-to-head           # H2H comparison (GET)
    /leaderboard            # All-time leaderboard (GET)

/api/  # JSON endpoints for AJAX
    /matches/upcoming       # User's upcoming matches (GET)
    /matches/recent         # Recent match results (GET)
    /match/<id>/sets        # Get match set scores (GET)
    /notifications          # User notifications (GET)
```

### Route Details

#### Authentication Routes

```python
# /auth/register - POST
Request:
{
    "email": "john@company.com",
    "username": "DragonSlayer",
    "password": "securepassword",
    "confirm_password": "securepassword",
    "tagline": "Fear the paddle!",  # Optional
    "avatar": <file>  # Optional
}

Response: Redirect to /dashboard or error

# /auth/login - POST
Request:
{
    "email": "john@company.com",
    "password": "securepassword",
    "remember_me": true
}

Response: Redirect to /dashboard or error
```

#### Dashboard Route

```python
# /dashboard - GET
# Returns: Main page with tournament view, user's matches, recent results

Context:
{
    "user": User,
    "active_tournament": Tournament | None,
    "user_registration": Registration | None,
    "user_upcoming_matches": [Match],  # User's upcoming
    "user_recent_matches": [Match],    # User's last 5
    "all_recent_matches": [Match],     # Everyone's recent
    "all_upcoming_matches": [Match],   # Everyone's upcoming
    "pending_confirmations": [Match],  # Matches awaiting user confirmation
    "standings": [Registration],       # If group stage
    "bracket": BracketData,           # If playoffs
}
```

#### Match Submission Routes

```python
# /match/<id>/submit - POST
Request:
{
    "sets": [
        {"player1_score": 11, "player2_score": 7},
        {"player1_score": 9, "player2_score": 11},
        {"player1_score": 11, "player2_score": 5}
    ]
}

Validation:
- User must be player1 or player2
- Match must be in 'scheduled' status
- Scores must follow table tennis rules
- Winner determined by best of 3 (first to 2 sets)

Response: Redirect with flash message

# /match/<id>/confirm - POST
# Confirms a pending score submission

Validation:
- User must be the OTHER player (not submitter)
- Match must be in 'pending_confirmation' status

Response: Redirect with flash message

# /match/<id>/dispute - POST
Request:
{
    "reason": "Score was incorrect"  # Optional
}

Validation:
- User must be the OTHER player (not submitter)
- Match must be in 'pending_confirmation' status

Response: Redirect, admin notified
```

---

## 7. User Interface Design

### Design System

#### Color Palette (Mortal Kombat Inspired)
```css
:root {
    /* Primary - Fire/Combat */
    --color-fire-500: #F97316;      /* Orange - primary accent */
    --color-fire-600: #EA580C;      /* Darker orange - hover */
    --color-fire-400: #FB923C;      /* Lighter orange */
    
    /* Background - Dark Arena */
    --color-dark-900: #0F0F0F;      /* Deepest black - main bg */
    --color-dark-800: #171717;      /* Card backgrounds */
    --color-dark-700: #262626;      /* Elevated surfaces */
    --color-dark-600: #404040;      /* Borders */
    
    /* Text */
    --color-text-primary: #FAFAFA;  /* White text */
    --color-text-secondary: #A3A3A3; /* Gray text */
    --color-text-muted: #737373;    /* Muted text */
    
    /* Status Colors */
    --color-win: #22C55E;           /* Green - victory */
    --color-loss: #EF4444;          /* Red - defeat */
    --color-pending: #EAB308;       /* Yellow - pending */
    
    /* Special */
    --color-gold: #FFD700;          /* Champion gold */
    --color-silver: #C0C0C0;        /* Runner-up silver */
    --color-bronze: #CD7F32;        /* Third place bronze */
}
```

#### Typography
```css
/* Headings - Bold, impactful */
font-family: 'Inter', 'SF Pro Display', system-ui, sans-serif;

/* VS Screen / Special text */
font-family: 'Bebas Neue', 'Impact', sans-serif;  /* Optional dramatic font */
```

#### Component Styling
```
Cards: 
- Rounded corners (rounded-lg / 8px)
- Subtle border (1px dark-600)
- Dark background (dark-800)
- Hover: slight glow effect

Buttons:
- Primary: Fire gradient, white text
- Secondary: Dark with border
- Hover: Scale up slightly (1.02)

Tables:
- Alternating row colors (dark-800 / dark-700)
- Sticky headers
- Responsive horizontal scroll on mobile
```

### Page Layouts

#### Landing Page (Unauthenticated)
```
┌────────────────────────────────────────────────────────┐
│                    HEADER                               │
│  🏓 .smash                          [Login] [Register] │
├────────────────────────────────────────────────────────┤
│                                                        │
│       ███████╗███╗   ███╗ █████╗ ███████╗██╗  ██╗     │
│       ██╔════╝████╗ ████║██╔══██╗██╔════╝██║  ██║     │
│       ███████╗██╔████╔██║███████║███████╗███████║     │
│       ╚════██║██║╚██╔╝██║██╔══██║╚════██║██╔══██║     │
│       ███████║██║ ╚═╝ ██║██║  ██║███████║██║  ██║     │
│       ╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝     │
│                                                        │
│           🏓 .lumen Table Tennis Championship 🏓        │
│                                                        │
│              [ Register Now ]  [ View Standings ]       │
│                                                        │
├────────────────────────────────────────────────────────┤
│  CURRENT TOURNAMENT: Summer Slam 2025                  │
│  Status: Group Stage | 12 Players | 24 Matches Left    │
└────────────────────────────────────────────────────────┘
```

#### Dashboard (Main Page - Authenticated)
```
┌────────────────────────────────────────────────────────────────────────┐
│ HEADER: 🏓 .smash   [Dashboard] [Tournaments] [Stats]   👤 DragonSlayer│
├────────────────────────────────────────────────────────┬───────────────┤
│                                                        │               │
│  SUMMER SLAM 2025 - GROUP STAGE                        │  YOUR NEXT    │
│  ═══════════════════════════════════════════          │  MATCH        │
│                                                        │ ┌───────────┐ │
│  ┌─────────────────────────────────────────────────┐  │ │           │ │
│  │ STANDINGS                                        │  │ │  YOU      │ │
│  ├──────┬──────────────┬────┬───┬───┬───┬─────────┤  │ │    VS     │ │
│  │ #    │ Player       │ P  │ W │ L │ SD│ PTS     │  │ │ SpinKing  │ │
│  ├──────┼──────────────┼────┼───┼───┼───┼─────────┤  │ │           │ │
│  │ 1 🔥 │ DragonSlayer │ 4  │ 4 │ 0 │+7 │ 8       │  │ │ Tomorrow  │ │
│  │ 2    │ PaddleMaster │ 4  │ 3 │ 1 │+5 │ 7       │  │ └───────────┘ │
│  │ 3    │ SpinKing     │ 4  │ 2 │ 2 │+1 │ 6       │  │ [Submit Score]│
│  │ 4    │ TableTitan   │ 4  │ 1 │ 3 │-4 │ 5       │  │               │
│  │ 5    │ NetNinja     │ 4  │ 0 │ 4 │-9 │ 4       │  │ ───────────── │
│  └──────┴──────────────┴────┴───┴───┴───┴─────────┘  │               │
│                                                        │ YOUR RECENT   │
│  OR (if playoffs):                                     │ MATCHES       │
│                                                        │ ┌───────────┐ │
│  ┌─────────────────────────────────────────────────┐  │ │✓ You 2-0  │ │
│  │           PLAYOFF BRACKET (GAUNTLET)             │  │ │ TableTitan│ │
│  │                                                  │  │ ├───────────┤ │
│  │  R1: TableTitan vs NetNinja     → [Winner]      │  │ │✓ You 2-1  │ │
│  │  R2: [Winner R1] vs SpinKing    → [Winner]      │  │ │ NetNinja  │ │
│  │  R3: [Winner R2] vs PaddleMaster→ [Winner]      │  │ └───────────┘ │
│  │  FINAL: [Winner R3] vs DragonSlayer → CHAMPION   │  │               │
│  └─────────────────────────────────────────────────┘  │ ───────────── │
│                                                        │               │
├────────────────────────────────────────────────────────┤ ALL MATCHES   │
│  RECENT RESULTS                      UPCOMING          │ ┌───────────┐ │
│  ┌─────────────────────────────┐    ┌──────────────┐  │ │PM vs SK   │ │
│  │ DragonSlayer 2-0 TableTitan │    │ SpinKing vs  │  │ │ Today 3pm │ │
│  │ "Flawless victory!"         │    │ DragonSlayer │  │ ├───────────┤ │
│  ├─────────────────────────────┤    │ Tomorrow     │  │ │TT vs NN   │ │
│  │ PaddleMaster 2-1 NetNinja   │    ├──────────────┤  │ │ Wed 2pm   │ │
│  │ "Close one!"                │    │ PaddleMaster │  │ └───────────┘ │
│  └─────────────────────────────┘    │ vs TableTitan│  │               │
│                                     │ Wednesday    │  │               │
│                                     └──────────────┘  │               │
└────────────────────────────────────────────────────────┴───────────────┘
```

#### Score Submission Page
```
┌────────────────────────────────────────────────────────┐
│                    MATCH RESULT                        │
│                                                        │
│       ┌─────────┐           ┌─────────┐               │
│       │  🐉     │    VS     │   👑    │               │
│       │  YOU    │    ⚔️     │ SpinKing│               │
│       └─────────┘           └─────────┘               │
│      "Fear the    │         │  "Spin to               │
│       paddle!"    │         │   win!"                 │
│                                                        │
│  ══════════════════════════════════════════════════   │
│                                                        │
│  SET 1:    [ 11 ]  -  [  7 ]     ✓ Valid             │
│  SET 2:    [  9 ]  -  [ 11 ]     ✓ Valid             │
│  SET 3:    [ 11 ]  -  [  5 ]     ✓ Valid             │
│                                                        │
│  ──────────────────────────────────────────────────   │
│                                                        │
│  RESULT:  YOU WIN  2-1  🏆                            │
│                                                        │
│  ══════════════════════════════════════════════════   │
│                                                        │
│         [ SUBMIT RESULT ]    [ CANCEL ]                │
│                                                        │
│  ⚠️ Your opponent will need to confirm this score.    │
└────────────────────────────────────────────────────────┘
```

#### Mobile Score Submission (Optimized)
```
┌──────────────────────────┐
│ ← SUBMIT SCORE           │
├──────────────────────────┤
│                          │
│    YOU vs SpinKing       │
│                          │
│  ┌─────────────────────┐ │
│  │  SET 1              │ │
│  │  [11] - [7]     ✓   │ │
│  ├─────────────────────┤ │
│  │  SET 2              │ │
│  │  [9]  - [11]    ✓   │ │
│  ├─────────────────────┤ │
│  │  SET 3              │ │
│  │  [11] - [5]     ✓   │ │
│  └─────────────────────┘ │
│                          │
│  Result: YOU WIN 2-1     │
│                          │
│  ┌────────────────────┐  │
│  │   SUBMIT RESULT    │  │
│  └────────────────────┘  │
│                          │
└──────────────────────────┘
```

### Component Library

#### Matchup Card (VS Style)
```html
<!-- Mortal Kombat style VS card -->
<div class="matchup-card">
    <div class="player player-1">
        <img src="avatar1.png" class="avatar">
        <span class="name">DragonSlayer</span>
        <span class="tagline">"Fear the paddle!"</span>
    </div>
    <div class="vs-badge">
        <span class="vs-text">VS</span>
        <span class="match-time">Today 3:00 PM</span>
    </div>
    <div class="player player-2">
        <img src="avatar2.png" class="avatar">
        <span class="name">SpinKing</span>
        <span class="tagline">"Spin to win!"</span>
    </div>
</div>
```

#### Result Card
```html
<div class="result-card win"> <!-- or 'loss' -->
    <div class="players">
        <span class="player winner">DragonSlayer</span>
        <span class="score">2 - 1</span>
        <span class="player">SpinKing</span>
    </div>
    <div class="sets">11-7, 9-11, 11-5</div>
    <div class="timestamp">2 hours ago</div>
</div>
```

#### Standings Row (with fire effect for top position)
```html
<tr class="standing-row position-1">
    <td class="position">
        <span class="fire-icon">🔥</span> 1
    </td>
    <td class="player">
        <img src="avatar.png" class="mini-avatar">
        DragonSlayer
    </td>
    <td class="stats">4</td>
    <td class="stats">4</td>
    <td class="stats">0</td>
    <td class="set-diff positive">+7</td>
    <td class="points">8</td>
</tr>
```

---

## 8. Authentication & Authorization

### User Roles

| Role | Permissions |
|------|-------------|
| **Guest** | View landing page, login, register |
| **User** | View dashboard, profile, tournaments, submit own match scores, confirm scores |
| **Admin** | All user permissions + create tournaments, edit any match, resolve disputes, manage users |

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    REGISTRATION FLOW                         │
│                                                             │
│  1. User visits /auth/register                              │
│  2. Fills form: email, username, password, tagline, avatar  │
│  3. Server validates:                                       │
│     - Email format and uniqueness                           │
│     - Username uniqueness (3-20 chars, alphanumeric + _)    │
│     - Password strength (min 8 chars)                       │
│  4. Password hashed with werkzeug.security                  │
│  5. Avatar uploaded to /static/avatars/ or default assigned │
│  6. User created, logged in, redirected to /dashboard       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      LOGIN FLOW                              │
│                                                             │
│  1. User visits /auth/login                                 │
│  2. Enters email and password                               │
│  3. Server validates credentials                            │
│  4. On success: create session, redirect to /dashboard      │
│  5. On failure: show error, stay on login page              │
│  6. Optional "remember me" extends session duration         │
└─────────────────────────────────────────────────────────────┘
```

### Password Security

```python
from werkzeug.security import generate_password_hash, check_password_hash

# On registration
password_hash = generate_password_hash(password, method='pbkdf2:sha256')

# On login
if check_password_hash(user.password_hash, password):
    login_user(user)
```

### Route Protection

```python
from flask_login import login_required, current_user
from functools import wraps

# Basic auth required
@app.route('/dashboard')
@login_required
def dashboard():
    ...

# Admin required decorator
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/')
@admin_required
def admin_dashboard():
    ...
```

### Avatar Handling

```python
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB

def save_avatar(file, username):
    if file and allowed_file(file.filename):
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{username}_{uuid.uuid4().hex[:8]}.{ext}"
        
        # Save and resize
        filepath = os.path.join(app.config['AVATAR_FOLDER'], filename)
        image = Image.open(file)
        image.thumbnail((200, 200))  # Max 200x200
        image.save(filepath, optimize=True, quality=85)
        
        return filename
    return 'default_avatar.png'

# Default avatars (pre-generated)
DEFAULT_AVATARS = [
    'paddle_red.png',
    'paddle_blue.png', 
    'paddle_green.png',
    'ball_flame.png',
    'ball_ice.png',
    # ... more options
]
```

---

## 9. Score Submission & Confirmation System

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SCORE SUBMISSION FLOW                             │
│                                                                     │
│   ┌─────────────┐                                                   │
│   │  SCHEDULED  │  Match is created, waiting to be played           │
│   └──────┬──────┘                                                   │
│          │                                                          │
│          │ Player submits score                                     │
│          ▼                                                          │
│   ┌──────────────────┐                                              │
│   │     PENDING      │  Score submitted, awaiting opponent          │
│   │  CONFIRMATION    │  confirmation                                │
│   └────────┬─────────┘                                              │
│            │                                                        │
│     ┌──────┴──────┬─────────────────┐                              │
│     │             │                 │                              │
│     ▼             ▼                 ▼                              │
│ ┌─────────┐  ┌──────────┐    ┌────────────┐                        │
│ │CONFIRMED│  │ DISPUTED │    │AUTO-CONFIRM│ (24h timeout)          │
│ └────┬────┘  └────┬─────┘    └─────┬──────┘                        │
│      │            │                │                                │
│      │            │                │                                │
│      │       ┌────▼────┐           │                                │
│      │       │  ADMIN  │           │                                │
│      │       │ REVIEW  │           │                                │
│      │       └────┬────┘           │                                │
│      │            │                │                                │
│      │      ┌─────┴─────┐          │                                │
│      │      ▼           ▼          │                                │
│      │ ┌─────────┐ ┌─────────┐     │                                │
│      │ │CONFIRMED│ │CORRECTED│     │                                │
│      │ └────┬────┘ └────┬────┘     │                                │
│      │      │           │          │                                │
│      └──────┴───────────┴──────────┘                                │
│                    │                                                │
│                    ▼                                                │
│            ┌──────────────┐                                         │
│            │   FINALIZED  │  Stats updated, tournament progresses   │
│            └──────────────┘                                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Match Status States

```python
class MatchStatus(Enum):
    SCHEDULED = "scheduled"           # Match created, not yet played
    PENDING_CONFIRMATION = "pending"  # Score submitted, awaiting confirmation
    CONFIRMED = "confirmed"           # Both players agree on score
    DISPUTED = "disputed"             # Opponent disputes the score
    CANCELLED = "cancelled"           # Match cancelled by admin
    WALKOVER = "walkover"             # One player forfeits/no-show
```

### Score Validation Rules

```python
def validate_set_score(player1_score: int, player2_score: int) -> bool:
    """
    Validates a single set score according to table tennis rules.
    
    Rules:
    - Normal win: First to 11 points with 2+ point lead
    - Deuce: If 10-10, must win by 2 (e.g., 12-10, 15-13)
    """
    # Both scores must be non-negative
    if player1_score < 0 or player2_score < 0:
        return False
    
    # Determine winner and loser scores
    winner_score = max(player1_score, player2_score)
    loser_score = min(player1_score, player2_score)
    
    # Winner must have at least 11 points
    if winner_score < 11:
        return False
    
    # Must win by at least 2 points
    if winner_score - loser_score < 2:
        return False
    
    # If winner has exactly 11, loser must have 9 or less
    if winner_score == 11 and loser_score > 9:
        return False
    
    # In deuce situations, check reasonable limits
    # (e.g., 15-13 is valid, but 50-48 is suspicious)
    if winner_score > 20 and loser_score > 18:
        # Flag for review but don't reject
        pass
    
    return True


def validate_match_result(sets: List[dict]) -> Tuple[bool, str, int]:
    """
    Validates complete match result.
    
    Returns: (is_valid, error_message, winner_id)
    
    Rules:
    - Best of 3 sets (first to 2 wins)
    - Each set must be valid
    - Match ends when someone reaches 2 set wins
    """
    if not sets or len(sets) < 2 or len(sets) > 3:
        return False, "Match must have 2 or 3 sets", None
    
    player1_sets_won = 0
    player2_sets_won = 0
    
    for i, s in enumerate(sets):
        p1 = s.get('player1_score', 0)
        p2 = s.get('player2_score', 0)
        
        if not validate_set_score(p1, p2):
            return False, f"Set {i+1} has invalid score: {p1}-{p2}", None
        
        if p1 > p2:
            player1_sets_won += 1
        else:
            player2_sets_won += 1
        
        # Check if match should have ended earlier
        if player1_sets_won == 2 or player2_sets_won == 2:
            if i < len(sets) - 1:
                return False, "Match continued after a player won 2 sets", None
    
    # Determine winner
    if player1_sets_won < 2 and player2_sets_won < 2:
        return False, "No player has won 2 sets yet", None
    
    winner = 1 if player1_sets_won == 2 else 2
    return True, "Valid", winner
```

### Auto-Confirmation System

```python
# Scheduled task (can use APScheduler or cron)
def auto_confirm_pending_matches():
    """
    Auto-confirms matches that have been pending for 24+ hours.
    Run this hourly via scheduler.
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    
    pending_matches = Match.query.filter(
        Match.status == MatchStatus.PENDING_CONFIRMATION,
        Match.submitted_at < cutoff_time
    ).all()
    
    for match in pending_matches:
        match.status = MatchStatus.CONFIRMED
        match.confirmed_at = datetime.utcnow()
        # Note: confirmed_by_id remains None (auto-confirmed)
        
        # Update statistics
        update_match_statistics(match)
        
        # Log the auto-confirmation
        app.logger.info(f"Auto-confirmed match {match.id} after 24h timeout")
    
    db.session.commit()
```

### Notification Triggers

```python
# Events that trigger notifications
NOTIFICATION_EVENTS = {
    'match_scheduled': "Your match vs {opponent} is scheduled for {time}",
    'score_submitted': "{opponent} submitted a score for your match. Please confirm.",
    'score_confirmed': "Match result confirmed: {result}",
    'score_disputed': "Your submitted score was disputed. Admin will review.",
    'dispute_resolved': "Admin has resolved the disputed match: {result}",
    'tournament_starting': "Tournament {name} is starting! Your first match is vs {opponent}",
    'playoffs_starting': "Playoffs are beginning! You qualified in position #{position}",
}
```

---

## 10. Email Notification System

> **Note**: This is a future enhancement. The architecture is designed to accommodate it.

### Email Types

| Type | Trigger | Content |
|------|---------|---------|
| Welcome | Registration | Welcome message, quick start guide |
| Match Reminder | 24h before scheduled match | Opponent info, time, location |
| Score Confirmation Request | Score submitted | Link to confirm/dispute |
| Weekly Digest | Sunday evening | Last week's results, upcoming matches, standings |
| Tournament Announcement | New tournament created | Registration link, details |
| Playoff Qualification | Group stage ends | Final position, playoff schedule |
| Champion Announcement | Tournament ends | Winner, final standings |

### Weekly Digest Template Structure

```
Subject: 🏓 .smash Weekly Digest - Week of {date}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR PERFORMANCE THIS WEEK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Matches Played: 3
Record: 2W - 1L
Current Position: #2

YOUR RESULTS:
✓ You 2-0 TableTitan
✓ You 2-1 NetNinja  
✗ PaddleMaster 2-0 You

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR UPCOMING MATCHES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Monday: vs SpinKing
Wednesday: vs DragonSlayer

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOURNAMENT STANDINGS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#1 DragonSlayer - 10 pts 🔥
#2 You - 9 pts
#3 PaddleMaster - 7 pts
#4 SpinKing - 6 pts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

View full standings: {link}
```

### Implementation Architecture

```python
# Future: app/services/email.py

from flask_mail import Mail, Message
from app import create_app

mail = Mail()

def send_email(to: str, subject: str, template: str, **kwargs):
    """Send email using Flask-Mail."""
    msg = Message(
        subject=subject,
        recipients=[to],
        html=render_template(f'email/{template}.html', **kwargs),
        body=render_template(f'email/{template}.txt', **kwargs)
    )
    mail.send(msg)


def send_weekly_digest(user: User):
    """Compile and send weekly digest for a user."""
    # Get user's matches from last week
    # Get user's upcoming matches
    # Get current standings
    # Render and send
    pass


# Scheduler setup (using APScheduler)
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('cron', day_of_week='sun', hour=18)
def send_all_weekly_digests():
    """Send weekly digests to all users every Sunday at 6 PM."""
    users = User.query.filter(User.email.isnot(None)).all()
    for user in users:
        send_weekly_digest(user)
```

---

## 11. Deployment Configuration

### Server Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 1 core | 2 cores |
| RAM | 512 MB | 1 GB |
| Storage | 1 GB | 5 GB |
| Python | 3.10+ | 3.11+ |

### Nginx Configuration

```nginx
# /etc/nginx/sites-available/smash

upstream smash_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name smash.lumen.local;
    
    # Redirect HTTP to HTTPS (if using SSL)
    # return 301 https://$server_name$request_uri;
    
    # Static files
    location /static/ {
        alias /var/www/smash/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Avatar uploads
    location /static/avatars/ {
        alias /var/www/smash/app/static/avatars/;
        expires 7d;
    }
    
    # Application
    location / {
        proxy_pass http://smash_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if added later)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log /var/log/nginx/smash_access.log;
    error_log /var/log/nginx/smash_error.log;
}
```

### Gunicorn Configuration

```python
# gunicorn.conf.py

bind = "127.0.0.1:8000"
workers = 2  # For ~20 users, 2 workers is plenty
worker_class = "sync"
timeout = 30
keepalive = 2

# Logging
accesslog = "/var/log/smash/gunicorn_access.log"
errorlog = "/var/log/smash/gunicorn_error.log"
loglevel = "info"

# Process naming
proc_name = "smash"

# Security
limit_request_line = 4094
limit_request_fields = 100
```

### Systemd Service

```ini
# /etc/systemd/system/smash.service

[Unit]
Description=.smash Table Tennis Championship App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/smash
Environment="PATH=/var/www/smash/venv/bin"
ExecStart=/var/www/smash/venv/bin/gunicorn -c gunicorn.conf.py "app:create_app()"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Environment Configuration

```bash
# /var/www/smash/.env

# Flask
FLASK_APP=app
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-generate-with-python-secrets

# Database
DATABASE_URL=sqlite:///instance/smash.db

# Email (future)
MAIL_SERVER=smtp.lumen.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=smash@lumen.com
MAIL_PASSWORD=email-password

# App settings
AVATAR_UPLOAD_FOLDER=/var/www/smash/app/static/avatars
MAX_AVATAR_SIZE=2097152
```

### Deployment Script

```bash
#!/bin/bash
# deploy.sh

set -e

APP_DIR="/var/www/smash"
VENV_DIR="$APP_DIR/venv"

echo "🏓 Deploying .smash..."

# Pull latest code
cd $APP_DIR
git pull origin main

# Activate venv and install dependencies
source $VENV_DIR/bin/activate
pip install -r requirements.txt

# Run migrations
flask db upgrade

# Collect static files (if using build step for Tailwind)
# npm run build

# Restart services
sudo systemctl restart smash
sudo systemctl reload nginx

echo "✅ Deployment complete!"
```

---

## 12. Implementation Phases

### Phase 0: Project Setup ✅ COMPLETED
**Duration**: ~30 minutes
**Goal**: Initialize project structure and basic configuration
**Status**: ✅ **COMPLETED** - January 20, 2026

```
Tasks:
☑ Create project directory structure
☑ Initialize Python virtual environment
☑ Create requirements.txt with dependencies
☑ Set up Flask application factory pattern
☑ Configure SQLAlchemy and Flask-Migrate
☑ Create .env.example and config.py
☑ Initialize database models (User, Tournament, Match, etc.)
☑ Run initial migration
☑ Create basic run.py for development
```

**Deliverables**:
- ✅ Working Flask app that starts on port 5000
- ✅ Database tables created (6 tables: users, tournaments, registrations, matches, set_scores, tournament_winners)
- ✅ Basic project structure in place
- ✅ All models with enums, relationships, and validation properties
- ✅ Utility files created (defaults.py with 20 taglines, avatars.py with auto-discovery)
- ✅ Virtual environment with all dependencies installed

**Implementation Notes**:
- Tournament model uses string-based enums (`TournamentStatus`, `PlayoffFormat`) for better database compatibility
- Match model includes comprehensive status tracking (`MatchStatus`, `MatchPhase`) with enums
- Registration model includes `group_points` defaulting to 0 (scoring: 2 for win, 1 for loss in group stage)
- SetScore model includes `is_valid_score` property for table tennis rule validation
- User model has `display_tagline` and `display_avatar` properties that return random defaults if not set
- All relationships properly configured with `back_populates` for bidirectional access
- Unique constraints added: (user_id, tournament_id) for registrations, (match_id, set_number) for set_scores
- Default avatars directory created with .gitkeep file and auto-discovery system ready
- Models include helper methods: `get_opponent()`, `is_pending_confirmation()`, `set_difference`, etc.

**Database Schema Verification**:
```
Tables created:
- alembic_version (migration tracking)
- tournaments (with status, phase, playoff_format)
- users (with email/username indexes)
- matches (with all player/submitter/winner relationships)
- registrations (with group stage stats)
- tournament_winners (with position tracking)
- set_scores (with match reference)
```

---

### Phase 1: Authentication System ✅ COMPLETED
**Duration**: ~45 minutes (actual)
**Goal**: Complete user registration, login, and profile management
**Status**: ✅ **COMPLETED** - January 20, 2026

```
Tasks:
☑ Implement User model with password hashing
☑ Create Flask-Login configuration
☑ Build registration form and route
  ☑ Email validation
  ☑ Username validation (3-20 chars, alphanumeric + underscore)
  ☑ Password strength check (min 8 chars)
  ☑ Avatar upload handling (resize to 200x200, optimize)
☑ Build login form and route (with remember me)
☑ Build logout route
☑ Create profile view page
☑ Create profile edit page
☑ Implement route protection decorators (@login_required, @admin_required)
☑ Create base template with navigation (MK theme)
☑ Style auth pages with Tailwind (dark theme)
☑ Implement password change route
☑ Add random default taglines and avatars
```

**Deliverables**:
- ✅ Users can register with avatar and tagline
- ✅ Users can login/logout with "remember me"
- ✅ Users can view and edit their profile
- ✅ Protected routes work correctly
- ✅ Avatar upload with automatic resize and optimization
- ✅ Random default taglines assigned if none provided
- ✅ Random default avatars assigned if none uploaded
- ✅ Password change functionality with current password verification
- ✅ Mortal Kombat dark theme with fire orange accents
- ✅ Mobile responsive design
- ✅ Color-coded flash messages

**Files Created** (14 files):
- `app/forms/auth.py` - All authentication forms with validation
- `app/routes/auth.py` - Registration, login, logout, profile routes
- `app/routes/main.py` - Landing page and dashboard routes
- `app/utils/decorators.py` - Admin required decorator
- `app/templates/base.html` - Master layout with MK theme
- `app/templates/auth/register.html` - Registration form
- `app/templates/auth/login.html` - Login form
- `app/templates/auth/profile.html` - Profile view
- `app/templates/auth/profile_edit.html` - Profile edit form
- `app/templates/auth/change_password.html` - Password change form
- `app/templates/main/landing.html` - Landing page
- `app/templates/main/dashboard.html` - Dashboard placeholder
- `app/static/css/app.css` - Custom MK styling
- `app/static/avatars/` - Directory for user uploads

**Files Modified** (2 files):
- `app/__init__.py` - Registered auth and main blueprints
- `app/utils/defaults.py` - Added get_random_tagline() and get_random_avatar() functions

**Routes Implemented**:
- `/` - Landing page (redirects to dashboard if authenticated)
- `/auth/register` - User registration with email, username, password, optional tagline/avatar
- `/auth/login` - Login with email, password, remember me checkbox
- `/auth/logout` - Logout with flash message
- `/auth/profile` - View user profile (protected)
- `/auth/profile/edit` - Edit profile (protected)
- `/auth/profile/change-password` - Change password (protected)
- `/dashboard` - User dashboard placeholder (protected)

---

### Phase 2: Tournament Management - Admin (Claude Code Session 3) ✅ **COMPLETE**
**Duration**: ~45 minutes
**Goal**: Admin can create and manage tournaments

```
Tasks:
✅ Create admin dashboard page
✅ Build tournament creation form
  ✅ Name, description
  ✅ Playoff format selection
  ✅ Qualifier count (optional)
✅ Tournament list view (admin)
✅ Tournament detail view (admin)
✅ Start group stage functionality
  ✅ Generate all round-robin fixtures
  ✅ Set tournament status
✅ Cancel tournament functionality
✅ Style admin pages
```

**Deliverables**:
- ✅ Admin can create tournaments
- ✅ Admin can start group stage
- ✅ Fixtures are auto-generated

**Completion Date**: January 20, 2026

**Files Created**:
- `app/services/tournament.py` - Core business logic
- `app/forms/tournament.py` - Tournament forms
- `app/routes/admin.py` - Admin blueprint
- `app/templates/admin/dashboard.html` - Tournament list
- `app/templates/admin/tournament_create.html` - Create form
- `app/templates/admin/tournament_detail.html` - Tournament details

**Files Modified**:
- `app/templates/base.html` - Admin nav link
- `app/__init__.py` - Blueprint registration

---

### Phase 3: User Tournament Flow (Claude Code Session 4)
**Duration**: ~45 minutes
**Goal**: Users can register for tournaments and view fixtures

```
Tasks:
□ Public tournament list page
□ Tournament detail page (user view)
  □ Registration button
  □ Unregister button
  □ Player list
□ Registration logic
  □ Check tournament status
  □ Prevent duplicate registration
□ Group stage standings table
  □ Calculate points, set diff, etc.
  □ Apply tiebreakers
  □ Highlight user's row
□ Fixtures list view
  □ Filter by status
  □ Show scores for completed
```

**Deliverables**:
- Users can register for tournaments
- Standings table displays correctly
- Fixtures list shows all matches

---

### Phase 4: Dashboard & Main View (Claude Code Session 5)
**Duration**: ~1 hour
**Goal**: Complete main dashboard with all components

```
Tasks:
□ Dashboard layout (main + sidebar)
□ Main area:
  □ Active tournament standings OR bracket
  □ Recent results (all users)
  □ Upcoming matches (all users)
□ Sidebar:
  □ User's next match (VS card style)
  □ User's recent matches (last 5)
  □ Pending confirmation alerts
□ Mortal Kombat styling
  □ VS cards
  □ Fire effects for #1
  □ Win/loss color coding
□ Mobile responsive layout
```

**Deliverables**:
- Dashboard shows all relevant info
- MK-style visual design
- Works on mobile

---

### Phase 5: Score Submission System (Claude Code Session 6)
**Duration**: ~1 hour
**Goal**: Complete score submission and confirmation flow

```
Tasks:
□ Score submission page
  □ Set-by-set input
  □ Real-time validation
  □ Match preview (VS style)
□ Score validation logic
  □ Table tennis rules
  □ Best of 3 logic
□ Submit score route
  □ Update match status
  □ Record submitter
□ Confirmation system
  □ Confirm route
  □ Dispute route
  □ Pending confirmation alerts
□ Auto-confirmation scheduler
  □ 24-hour timeout
□ Admin score override
□ Update statistics on confirmation
□ Mobile-optimized submission
```

**Deliverables**:
- Players can submit scores
- Opponents can confirm/dispute
- Stats update on confirmation
- Mobile submission works smoothly

---

### Phase 6: Playoff System (Claude Code Session 7)
**Duration**: ~1 hour
**Goal**: Implement playoff bracket generation and progression

```
Tasks:
□ Group stage completion logic
  □ Final standings calculation
  □ Tiebreaker application
□ Gauntlet bracket generation
  □ Create matches based on standings
  □ Link matches (winner advances)
□ Single elimination bracket generation (alternative)
  □ Seeding logic
  □ Bracket structure
□ Bracket visualization
  □ Gauntlet: linear progression view
  □ Single elim: tree view
□ Playoff match handling
  □ Automatic next match creation
  □ Winner advancement
□ Tournament completion
  □ Declare winner
  □ Record final positions
□ Admin playoff controls
```

**Deliverables**:
- Playoffs generate correctly
- Bracket displays properly
- Winners advance automatically
- Tournament completes properly

---

### Phase 7: Statistics & History (Claude Code Session 8)
**Duration**: ~45 minutes
**Goal**: Comprehensive statistics and history pages

```
Tasks:
□ User statistics page
  □ Overall record
  □ Tournament history
  □ Win rate over time
  □ Head-to-head records
□ Global statistics page
  □ All-time leaderboard
  □ Tournament winners hall of fame
  □ Interesting stats (longest match, etc.)
□ Head-to-head comparison page
  □ Select two players
  □ Show history and stats
□ Match history page
  □ Filterable by tournament/player
  □ Pagination
```

**Deliverables**:
- Rich statistics for users
- Global leaderboards
- Head-to-head comparisons

---

### Phase 8: Polish & Deployment (Claude Code Session 9)
**Duration**: ~1 hour
**Goal**: Final polish, testing, and deployment

```
Tasks:
□ UI polish
  □ Animations and transitions
  □ Loading states
  □ Error handling
  □ Flash messages
□ Security review
  □ CSRF protection
  □ SQL injection prevention
  □ XSS prevention
□ Performance check
  □ Query optimization
  □ Static file caching
□ Deployment setup
  □ Nginx configuration
  □ Gunicorn setup
  □ Systemd service
□ Documentation
  □ README
  □ Admin guide
□ Final testing on server
```

**Deliverables**:
- Production-ready application
- Deployed and running on server
- Documentation complete

---

### Future Enhancements (Post-V1)

```
□ Email notification system
  □ Weekly digests
  □ Match reminders
□ Real-time updates (WebSockets)
□ Double elimination playoffs
□ Multiple groups support
□ Season/league system
□ Achievement badges
□ Match scheduling calendar
□ Spectator mode
□ Match commentary/reactions
```

---

## 13. File Structure

```
smash/
├── app/
│   ├── __init__.py              # Application factory
│   ├── config.py                # Configuration classes
│   ├── extensions.py            # Flask extensions init
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py              # User model
│   │   ├── tournament.py        # Tournament model
│   │   ├── match.py             # Match, SetScore models
│   │   └── registration.py      # Registration model
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py              # Login, register, logout
│   │   ├── main.py              # Dashboard, landing
│   │   ├── tournament.py        # Tournament views
│   │   ├── match.py             # Match submission
│   │   ├── profile.py           # User profile
│   │   ├── admin.py             # Admin routes
│   │   ├── stats.py             # Statistics
│   │   └── api.py               # JSON endpoints
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── tournament.py        # Tournament business logic
│   │   ├── match.py             # Match/scoring logic
│   │   ├── standings.py         # Standings calculation
│   │   ├── bracket.py           # Playoff generation
│   │   └── stats.py             # Statistics calculation
│   │
│   ├── forms/
│   │   ├── __init__.py
│   │   ├── auth.py              # Login, register forms
│   │   ├── tournament.py        # Tournament forms
│   │   ├── match.py             # Score submission form
│   │   └── profile.py           # Profile edit form
│   │
│   ├── templates/
│   │   ├── base.html            # Base layout
│   │   ├── components/
│   │   │   ├── navbar.html
│   │   │   ├── sidebar.html
│   │   │   ├── vs_card.html     # MK-style VS display
│   │   │   ├── match_card.html
│   │   │   ├── standings_table.html
│   │   │   └── bracket.html
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── register.html
│   │   ├── main/
│   │   │   ├── landing.html
│   │   │   └── dashboard.html
│   │   ├── tournament/
│   │   │   ├── list.html
│   │   │   ├── detail.html
│   │   │   └── bracket.html
│   │   ├── match/
│   │   │   ├── detail.html
│   │   │   └── submit.html
│   │   ├── profile/
│   │   │   ├── view.html
│   │   │   └── edit.html
│   │   ├── admin/
│   │   │   ├── dashboard.html
│   │   │   ├── tournament_edit.html
│   │   │   └── match_edit.html
│   │   ├── stats/
│   │   │   ├── overview.html
│   │   │   ├── user.html
│   │   │   └── h2h.html
│   │   └── email/               # Future: email templates
│   │       ├── weekly_digest.html
│   │       └── weekly_digest.txt
│   │
│   ├── static/
│   │   ├── css/
│   │   │   ├── tailwind.css     # Tailwind source
│   │   │   └── app.css          # Custom styles
│   │   ├── js/
│   │   │   ├── app.js           # Main JS
│   │   │   └── alpine.min.js    # Alpine.js
│   │   ├── img/
│   │   │   ├── logo.svg
│   │   │   ├── favicon.ico
│   │   │   └── default_avatars/ # DROP NEW AVATARS HERE - AUTO-DISCOVERED!
│   │   │       ├── README.txt   # Instructions for adding avatars
│   │   │       └── placeholder.png  # Initial placeholder
│   │   └── avatars/             # User-uploaded avatars
│   │
│   └── utils/
│       ├── __init__.py
│       ├── helpers.py           # Misc helpers
│       ├── decorators.py        # Custom decorators
│       ├── avatars.py           # Avatar discovery & management
│       └── defaults.py          # Default taglines & other defaults
│
├── migrations/                  # Flask-Migrate
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_tournament.py
│   └── test_match.py
│
├── instance/
│   └── smash.db                 # SQLite database
│
├── .env                         # Environment variables
├── .env.example
├── .gitignore
├── requirements.txt
├── gunicorn.conf.py
├── run.py                       # Development server
├── tailwind.config.js           # Tailwind config
├── package.json                 # For Tailwind build
└── README.md
```

---

## 14. Open Questions & Decisions

### Resolved Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Framework | Flask | Simplicity, sufficient for 20 users |
| Database | SQLite | Low concurrency needs, easy setup |
| Playoff format | **Gauntlet** | More exciting, everyone has a chance, dramatic comebacks |
| Playoff qualifiers | **All players** | Everyone advances from group stage to Gauntlet |
| Score confirmation | Two-player with auto-confirm | Balance of accuracy and convenience |
| Email required | Yes | Unique ID, future notifications |
| Tagline max length | **100 characters** | Enough for creativity, not excessive |
| Default taglines | **Random cringe/wholesome** | Encourage users to add their own |
| Default avatars | **Folder with auto-discovery** | Easy to add more by dropping files in directory |

### Default Taglines (Cringe-Wholesome Collection)

These intentionally awkward taglines are assigned randomly to users who don't provide their own, encouraging them to customize:

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
    "Professional overthinker. Amateur ping pong player.",
    "Here for the free exercise and existential dread.",
    "My spirit animal is a deflated balloon.",
    "I practiced for 10 minutes. I'm basically a pro now.",
    "Warning: May apologize excessively during matches.",
    "I brought snacks to share. Please be my friend.",
    "My paddle has trust issues and so do I.",
    "Insert inspirational quote here.",
    "I'm just here so I don't get fined.",
    "Plot twist: I've never actually played before.",
    "My cat believes in me and that's enough.",
    "Preparing my excuse for losing since 2024.",
]
```

### Avatar Auto-Discovery System

Default avatars are stored in `app/static/img/default_avatars/` and automatically discovered:

```python
# app/utils/avatars.py

import os
import random
from flask import current_app

ALLOWED_AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def get_default_avatars() -> list[str]:
    """
    Discovers all default avatars in the default_avatars directory.
    Simply drop new images into the folder and they'll be available.
    
    Returns list of filenames (e.g., ['paddle_red.png', 'ball_flame.png'])
    """
    avatar_dir = os.path.join(
        current_app.static_folder, 
        'img', 
        'default_avatars'
    )
    
    if not os.path.exists(avatar_dir):
        return ['placeholder.png']  # Fallback
    
    avatars = [
        f for f in os.listdir(avatar_dir)
        if f.lower().rsplit('.', 1)[-1] in ALLOWED_AVATAR_EXTENSIONS
        and not f.startswith('.')  # Ignore hidden files
    ]
    
    return avatars if avatars else ['placeholder.png']


def get_random_default_avatar() -> str:
    """Returns a random default avatar filename."""
    return random.choice(get_default_avatars())


def get_default_avatar_path(filename: str) -> str:
    """Returns the URL path for a default avatar."""
    return f'/static/img/default_avatars/{filename}'
```

**To add new default avatars:**
1. Drop image files into `app/static/img/default_avatars/`
2. Supported formats: PNG, JPG, JPEG, GIF, WEBP
3. Recommended size: 200x200 pixels
4. They'll be automatically available for new users

### Remaining Implementation Details

| Question | Notes |
|----------|-------|
| **Match scheduling** | Manual for V1 (admin sets dates, or left unscheduled) |
| **Third-place match** | N/A (using Gauntlet format) |

### Future Considerations

- **Multiple simultaneous tournaments**: Current design supports this
- **Team tournaments**: Would need new models
- **Rating/ELO system**: Could add to Registration model
- **API for mobile app**: Routes already support JSON

---

## Appendix A: Quick Reference Commands

```bash
# Development
cd /path/to/smash
source venv/bin/activate
flask run --debug

# Database
flask db init        # First time only
flask db migrate -m "Description"
flask db upgrade

# Create admin user
flask shell
>>> from app.models import User
>>> admin = User(email='admin@lumen.com', username='admin', is_admin=True)
>>> admin.set_password('adminpass')
>>> db.session.add(admin)
>>> db.session.commit()

# Production
sudo systemctl start smash
sudo systemctl status smash
sudo journalctl -u smash -f

# Nginx
sudo nginx -t
sudo systemctl reload nginx
```

---

## Appendix B: Dependencies (requirements.txt)

```
# Core
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-WTF==1.2.1
Flask-Migrate==4.0.5

# Database
SQLAlchemy==2.0.23

# Security
Werkzeug==3.0.1
email-validator==2.1.0

# Image processing
Pillow==10.1.0

# Production
gunicorn==21.2.0

# Scheduling (for auto-confirm)
APScheduler==3.10.4

# Future: Email
# Flask-Mail==0.9.1

# Development
python-dotenv==1.0.0
```

---

*Document prepared for implementation with Claude Code. Each phase is designed to be completable in a single coding session with clear deliverables.*
