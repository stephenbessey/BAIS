#!/bin/bash

# BAIS Database Restore Script
set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  This will restore database from: $BACKUP_FILE"
echo "This will OVERWRITE the current database!"
read -p "Are you sure? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Restore cancelled"
    exit 1
fi

echo "🔄 Restoring database..."

# Stop services
docker-compose stop bais-api worker scheduler

# Restore database
gunzip -c "$BACKUP_FILE" | docker-compose exec -T postgres psql -U bais_user -d bais_production

# Start services
docker-compose start bais-api worker scheduler

echo "✅ Database restored successfully"

---
# Makefile
