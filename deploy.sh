#!/bin/bash
set -e

TARGET_DIR=/home/dasunimandini/econex

# Clone repo if it doesn't exist (first deploy), otherwise just pull latest
if [ ! -d "$TARGET_DIR/.git" ]; then
    # Remove stale directory that isn't a git repo (e.g., from a failed deploy)
    if [ -d "$TARGET_DIR" ]; then
        rm -rf "$TARGET_DIR"
    fi
    git clone https://github.com/NethmiTharushi22/Econex.git "$TARGET_DIR"
else
    cd "$TARGET_DIR"
    git pull origin main
fi

cd "$TARGET_DIR"

# Write .env file from the env vars already sourced
cat > .env << EOF
SECRET_KEY=$SECRET_KEY
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
FRONTEND_ORIGIN=http://34.21.192.28
DATABASE_URL=$DATABASE_URL
WAREHOUSE_DATABASE_URL=$WAREHOUSE_DATABASE_URL
GROQ_API_KEY=$GROQ_API_KEY
SMTP_HOST=$SMTP_HOST
SMTP_PORT=$SMTP_PORT
SMTP_USER=$SMTP_USER
SMTP_PASSWORD=$SMTP_PASSWORD
HF_TOKEN=
EOF

# Build and start containers (--no-cache ensures env/config changes take effect)
docker compose build --no-cache
docker compose up -d --force-recreate

# Wait for backend to initialize
echo "Waiting 15s for backend to start..."
sleep 15

# Show container status
echo "=== Container Status ==="
docker compose ps

# Show backend logs so CI can diagnose crashes
echo "=== Backend Logs ==="
docker compose logs --tail=80 backend

# Fail the deploy if backend isn't running
if ! docker compose ps backend | grep -q "Up"; then
    echo "ERROR: Backend container is not running!"
    exit 1
fi

echo "Deployment complete"
