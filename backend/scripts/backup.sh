#!/bin/bash

# BAIS Database Backup Script
set -e

BACKUP_DIR="/var/backups/bais"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="bais_backup_${TIMESTAMP}.sql"

echo "📦 Creating BAIS database backup..."

# Create backup directory
mkdir -p $BACKUP_DIR

# Create database backup
docker-compose exec -T postgres pg_dump -U bais_user bais_production > "$BACKUP_DIR/$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_DIR/$BACKUP_FILE"

echo "✅ Backup created: $BACKUP_DIR/$BACKUP_FILE.gz"

# Clean up old backups (keep last 30 days)
find $BACKUP_DIR -name "bais_backup_*.sql.gz" -mtime +30 -delete

echo "🧹 Old backups cleaned up"
