#!/bin/bash
set -e

cd /home/teran8777/econex

# Build and start containers
docker compose build
docker compose up -d

# Verify
docker compose ps
echo "Deployment complete"
