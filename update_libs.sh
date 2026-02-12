#!/bin/bash
# Update Python libraries by rebuilding the backend container
# Usage: ./update_libs.sh

echo "[$(date)] Starting library update..."

# 1. Pull latest base image (optional, good for security updates)
# sudo docker pull python:3.11-slim

# 2. Rebuild backend without cache to fetch latest pip packages
echo "Rebuilding backend..."
sudo docker compose build --no-cache backend

# 3. Restart backend service
echo "Restarting service..."
sudo docker compose up -d backend

# 4. Clean up old images
echo "Cleaning up..."
sudo docker image prune -f

echo "[$(date)] Update complete."
