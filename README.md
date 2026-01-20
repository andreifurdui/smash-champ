# .smash

Office table tennis championship app for .lumen (~20 users).

## Features
- User registration with avatars and taglines
- Tournament management (group stage + Gauntlet playoffs)
- Score submission with opponent confirmation
- Statistics, leaderboards, and head-to-head comparisons

## Tech Stack
- Flask 3.x + SQLAlchemy + Flask-Login
- SQLite database
- Tailwind CSS + Alpine.js
- Gunicorn + Nginx

## Quick Start

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Initialize database
flask db upgrade

# Development
flask run --debug

# Production
gunicorn -c gunicorn.conf.py wsgi:app
```

## Environment Variables
Set these in your environment or `.env` file:
- `SECRET_KEY`: Random string for session security (required in production)
- `DATABASE_URL`: SQLite path (default: sqlite:///instance/smash.db)

## Admin Setup
```bash
flask shell
>>> from app.models import User
>>> from app.extensions import db
>>> u = User(email='admin@lumen.com', username='admin', is_admin=True)
>>> u.set_password('your-password')
>>> db.session.add(u); db.session.commit()
```

## Deployment

Run the deployment script:
```bash
# Full deployment (with nginx + systemd)
sudo ./deploy.sh

# Or without sudo (skips system config, prints manual steps)
./deploy.sh
```

The script will:
1. Create virtual environment and install dependencies
2. Generate SECRET_KEY and create `.env` file
3. Run database migrations
4. Set up Nginx reverse proxy
5. Configure systemd service
6. Start the application

After deployment, access at: http://smash.muncher.lumen.lan

---
Built with fire for .lumen
