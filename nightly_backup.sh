#!/usr/bin/env bash
# nightly_backup.sh - Automated backup script for QStash Pipeline using Cloudflare R2

set -euo pipefail

# Configuration
BACKUP_DATE=$(date +%Y-%m-%d_%H-%M-%S)
WEAVIATE_DATA_PATH="./infra/weaviate_data"
R2_BUCKET="trading-backups"
R2_PREFIX="weaviate-data"
LOG_FILE="./logs/backup_${BACKUP_DATE}.log"

# Create logs directory if it doesn't exist
mkdir -p ./logs

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting nightly backup process with Cloudflare R2"

# Check if required environment variables are set
if [[ -z "${R2_ACCOUNT_ID:-}" || -z "${R2_KEY:-}" || -z "${R2_SECRET:-}" ]]; then
    log "ERROR: R2 credentials not found. Please set R2_ACCOUNT_ID, R2_KEY, and R2_SECRET"
    exit 1
fi

# Check if required tools are available
if ! command -v rclone &> /dev/null; then
    log "ERROR: rclone not found. Please install rclone"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    log "ERROR: Docker not found. Please install Docker"
    exit 1
fi

# Configure rclone for Cloudflare R2
export RCLONE_CONFIG_R2_TYPE=s3
export RCLONE_CONFIG_R2_PROVIDER=Cloudflare
export RCLONE_CONFIG_R2_ACCESS_KEY_ID="${R2_KEY}"
export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="${R2_SECRET}"
export RCLONE_CONFIG_R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

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

# Create backup destination path
BACKUP_DEST="${R2_BUCKET}/${R2_PREFIX}/${BACKUP_DATE}"

# Create backup using rclone
log "Starting data sync to Cloudflare R2"
log "Source: $WEAVIATE_DATA_PATH"
log "Destination: R2:$BACKUP_DEST"

# Sync to R2 with progress and parallel transfers
rclone copy "$WEAVIATE_DATA_PATH" "R2:$BACKUP_DEST" \
  --progress \
  --transfers 8 \
  --exclude "*.tmp" \
  --exclude "*.lock" \
  --exclude "*.log" \
  --log-file "$LOG_FILE" \
  --log-level INFO

SYNC_EXIT_CODE=$?

if [ $SYNC_EXIT_CODE -eq 0 ]; then
    log "SUCCESS: Backup completed successfully"
    log "Backup location: R2:$BACKUP_DEST"
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

# Get backup size information
BACKUP_SIZE=$(du -sh "$WEAVIATE_DATA_PATH" 2>/dev/null | cut -f1 || echo "Unknown")

# List files in R2 to verify upload
log "Verifying backup in R2..."
rclone ls "R2:$BACKUP_DEST" --max-depth 1 | head -10 | while read line; do
    log "  Uploaded: $line"
done

# Cleanup old local logs (keep last 30 days)
log "Cleaning up old backup logs"
find ./logs -name "backup_*.log" -mtime +30 -delete 2>/dev/null || true

# Create backup summary
log "Backup summary:"
log "  - Date: $BACKUP_DATE"
log "  - Size: $BACKUP_SIZE"
log "  - Status: $([ $SYNC_EXIT_CODE -eq 0 ] && echo 'SUCCESS' || echo 'FAILED')"
log "  - Location: R2:$BACKUP_DEST"
log "  - Provider: Cloudflare R2 (Zero egress fees)"

log "Nightly backup process completed"

# Exit with the same code as the sync operation
exit $SYNC_EXIT_CODE