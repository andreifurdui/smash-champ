#!/bin/bash
# .smash Deployment Script
# Deploys the table tennis championship app to smash.lumen.local

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_DIR="/home/a-f/smash-champ"
VENV_DIR="$PROJECT_DIR/venv"
ENV_FILE="$PROJECT_DIR/.env"

echo -e "${GREEN}=== .smash Deployment Script ===${NC}"
echo ""

# Check if running with sudo for system operations
check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}Note: Run with sudo for nginx/systemd setup${NC}"
        echo "  sudo $0"
        echo ""
        SKIP_SYSTEM=true
    else
        SKIP_SYSTEM=false
    fi
}

# Step 1: Python virtual environment
setup_venv() {
    echo -e "${GREEN}[1/6] Setting up Python virtual environment...${NC}"

    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
        echo "  Created virtual environment"
    else
        echo "  Virtual environment already exists"
    fi

    source "$VENV_DIR/bin/activate"
    pip install -q --upgrade pip
    pip install -q -r "$PROJECT_DIR/requirements.txt"
    echo "  Dependencies installed"
}

# Step 2: Environment file with SECRET_KEY
setup_env() {
    echo -e "${GREEN}[2/6] Setting up environment...${NC}"

    if [ ! -f "$ENV_FILE" ]; then
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        cat > "$ENV_FILE" << EOF
# .smash Environment Configuration
SECRET_KEY=$SECRET_KEY
DATABASE_URL=sqlite:///$PROJECT_DIR/instance/smash.db
EOF
        echo "  Created .env with generated SECRET_KEY"
    else
        echo "  .env already exists"
    fi

    # Export for current session
    export $(grep -v '^#' "$ENV_FILE" | xargs)
}

# Step 3: Database setup
setup_database() {
    echo -e "${GREEN}[3/6] Setting up database...${NC}"

    source "$VENV_DIR/bin/activate"
    cd "$PROJECT_DIR"

    # Create instance directory if needed
    mkdir -p "$PROJECT_DIR/instance"

    # Run migrations
    flask db upgrade
    echo "  Database migrations applied"
}

# Step 4: Create logs directory
setup_logs() {
    echo -e "${GREEN}[4/6] Setting up logs directory...${NC}"

    mkdir -p "$PROJECT_DIR/logs"
    echo "  Logs directory ready"
}

# Step 5: Nginx configuration
setup_nginx() {
    echo -e "${GREEN}[5/6] Setting up Nginx...${NC}"

    if [ "$SKIP_SYSTEM" = true ]; then
        echo -e "  ${YELLOW}Skipped (run with sudo)${NC}"
        return
    fi

    # Copy nginx config
    cp "$PROJECT_DIR/nginx.conf" /etc/nginx/sites-available/smash

    # Enable site
    if [ ! -L /etc/nginx/sites-enabled/smash ]; then
        ln -s /etc/nginx/sites-available/smash /etc/nginx/sites-enabled/smash
    fi

    # Test nginx config
    nginx -t

    # Reload nginx
    systemctl reload nginx
    echo "  Nginx configured and reloaded"
}

# Step 6: Systemd service
setup_systemd() {
    echo -e "${GREEN}[6/6] Setting up systemd service...${NC}"

    if [ "$SKIP_SYSTEM" = true ]; then
        echo -e "  ${YELLOW}Skipped (run with sudo)${NC}"
        return
    fi

    # Copy service file
    cp "$PROJECT_DIR/smash.service" /etc/systemd/system/smash.service

    # Create environment file for systemd
    mkdir -p /etc/systemd/system/smash.service.d
    cat > /etc/systemd/system/smash.service.d/env.conf << EOF
[Service]
EnvironmentFile=$ENV_FILE
EOF

    # Reload systemd
    systemctl daemon-reload

    # Enable and start service
    systemctl enable smash
    systemctl restart smash

    echo "  Systemd service enabled and started"
}

# Print status
print_status() {
    echo ""
    echo -e "${GREEN}=== Deployment Complete ===${NC}"
    echo ""
    echo "Project: $PROJECT_DIR"
    echo "URL: http://smash.muncher.lumen.lan"
    echo ""

    if [ "$SKIP_SYSTEM" = true ]; then
        echo -e "${YELLOW}Manual steps required (run with sudo):${NC}"
        echo "  1. sudo cp nginx.conf /etc/nginx/sites-available/smash"
        echo "  2. sudo ln -s /etc/nginx/sites-available/smash /etc/nginx/sites-enabled/"
        echo "  3. sudo cp smash.service /etc/systemd/system/"
        echo "  4. Add 'EnvironmentFile=$ENV_FILE' to service"
        echo "  5. sudo systemctl daemon-reload"
        echo "  6. sudo systemctl enable --now smash"
        echo "  7. sudo systemctl reload nginx"
        echo ""
        echo "Or just run: sudo $0"
    else
        echo "Service status:"
        systemctl status smash --no-pager -l | head -5
    fi

    echo ""
    echo -e "${YELLOW}Don't forget to create an admin user:${NC}"
    echo "  cd $PROJECT_DIR && source venv/bin/activate"
    echo "  flask shell"
    echo "  >>> from app.models import User"
    echo "  >>> from app.extensions import db"
    echo "  >>> u = User(email='admin@lumen.com', username='admin', is_admin=True)"
    echo "  >>> u.set_password('your-password')"
    echo "  >>> db.session.add(u); db.session.commit()"
}

# Main
main() {
    cd "$PROJECT_DIR"
    check_sudo
    setup_venv
    setup_env
    setup_database
    setup_logs
    setup_nginx
    setup_systemd
    print_status
}

main "$@"
