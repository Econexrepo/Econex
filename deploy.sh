#!/bin/bash
set -e

cd /home/teran8777/econex

# Pull latest code (repo is public, no auth needed)
git pull origin main

# Build and start containers
docker compose build
docker compose up -d

# Verify
docker compose ps
echo "Deployment complete"
