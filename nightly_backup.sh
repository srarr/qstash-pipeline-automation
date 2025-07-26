#!/bin/bash
# nightly_backup.sh - Automated backup script for QStash Pipeline

set -e

# Configuration
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
WEAVIATE_DATA_PATH="./infra/weaviate_data"
R2_BUCKET="s3://qstash-pipeline-backups"
R2_PREFIX="weaviate-data"
LOG_FILE="./logs/backup_${BACKUP_DATE}.log"

# Create logs directory if it doesn't exist
mkdir -p ./logs

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting nightly backup process"

# Check if required tools are available
if ! command -v aws &> /dev/null; then
    log "ERROR: AWS CLI not found. Please install aws-cli"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    log "ERROR: Docker not found. Please install Docker"
    exit 1
fi

# Check if Weaviate data directory exists
if [ ! -d "$WEAVIATE_DATA_PATH" ]; then
    log "WARNING: Weaviate data directory not found at $WEAVIATE_DATA_PATH"
    log "Creating empty backup marker"
    mkdir -p "$WEAVIATE_DATA_PATH"
    echo "No data to backup on $BACKUP_DATE" > "$WEAVIATE_DATA_PATH/backup_marker.txt"
fi

# Stop Weaviate service for consistent backup
log "Stopping Weaviate service for consistent backup"
cd infra
docker compose stop weaviate || log "WARNING: Failed to stop Weaviate service"

# Wait for service to fully stop
sleep 5

# Create backup
log "Starting data sync to R2 storage"
log "Source: $WEAVIATE_DATA_PATH"
log "Destination: $R2_BUCKET/$R2_PREFIX/$BACKUP_DATE/"

# Sync to R2 with deep archive storage class
aws s3 cp "$WEAVIATE_DATA_PATH" "$R2_BUCKET/$R2_PREFIX/$BACKUP_DATE/" \
  --recursive \
  --storage-class DEEP_ARCHIVE \
  --exclude "*.tmp" \
  --exclude "*.lock" \
  --exclude "*.log" 2>&1 | tee -a "$LOG_FILE"

SYNC_EXIT_CODE=${PIPESTATUS[0]}

if [ $SYNC_EXIT_CODE -eq 0 ]; then
    log "SUCCESS: Backup completed successfully"
    log "Backup location: $R2_BUCKET/$R2_PREFIX/$BACKUP_DATE/"
else
    log "ERROR: Backup failed with exit code $SYNC_EXIT_CODE"
fi

# Restart Weaviate service
log "Restarting Weaviate service"
docker compose start weaviate || log "WARNING: Failed to restart Weaviate service"

# Wait for service to be ready
sleep 10

# Verify service is healthy
if curl -s http://localhost:8080/v1/meta > /dev/null; then
    log "SUCCESS: Weaviate service is healthy after backup"
else
    log "WARNING: Weaviate service may not be fully ready"
fi

# Cleanup old local logs (keep last 30 days)
log "Cleaning up old backup logs"
find ./logs -name "backup_*.log" -mtime +30 -delete 2>/dev/null || true

# Create backup summary
BACKUP_SIZE=$(du -sh "$WEAVIATE_DATA_PATH" 2>/dev/null | cut -f1 || echo "Unknown")
log "Backup summary:"
log "  - Date: $BACKUP_DATE"
log "  - Size: $BACKUP_SIZE"
log "  - Status: $([ $SYNC_EXIT_CODE -eq 0 ] && echo 'SUCCESS' || echo 'FAILED')"
log "  - Location: $R2_BUCKET/$R2_PREFIX/$BACKUP_DATE/"

log "Nightly backup process completed"

# Exit with the same code as the sync operation
exit $SYNC_EXIT_CODE