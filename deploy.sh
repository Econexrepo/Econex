#!/bin/bash
set -e

TARGET_DIR=/home/teran8777/econex

# Clone repo if it doesn't exist (first deploy), otherwise just pull latest
if [ ! -d "$TARGET_DIR/.git" ]; then
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

# Build and start containers
docker compose build
docker compose up -d

# Verify
docker compose ps
echo "Deployment complete"
