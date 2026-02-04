#!/bin/bash
# Backup script for Trading Noobs Database

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="tradingnoobs_db_$TIMESTAMP.sql"

# Create backup directory if not exists
mkdir -p $BACKUP_DIR

echo "Starting backup to $BACKUP_DIR/$FILENAME..."

# Run pg_dump inside the container
docker exec tradingnoobs-db pg_dump -U postgres tradingnoobs > $BACKUP_DIR/$FILENAME

# Optional: Compress the backup
gzip $BACKUP_DIR/$FILENAME

# Remove backups older than 30 days
find $BACKUP_DIR -type f -name "*.gz" -mtime +30 -delete

echo "Backup completed successfully!"
