#!/bin/bash

# Manual Deployment Script for AI Memory Pipeline on Synology NAS
# Run this script directly on the NAS (via SSH as admin or root)
#
# Volume mapping:
#   /volume1/SharedMemory → Shared memory (me/wife documents)
#   /volume3/docker/*     → Docker/container project data

set -e

set -e

cd /volume1/docker/AI-Memory

echo "=== Stopping existing containers ==="
/usr/local/bin/docker compose down || true

echo "=== Pulling latest images ==="
/usr/local/bin/docker compose pull

echo "=== Starting containers ==="
/usr/local/bin/docker compose up -d

echo "=== Waiting for services to be ready ==="
sleep 10

echo "=== Checking container status ==="
/usr/local/bin/docker compose ps

echo "=== Deployment complete! ==="
