# QStash Pipeline Automation - Operations Runbook

## Quick Start Commands

### Start/Stop Services

```bash
# Start all services
cd infra
docker compose up -d

# Start specific services
docker compose up -d redis weaviate
docker compose up -d orchestrator

# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v

# View logs
docker compose logs -f orchestrator
docker compose logs -f crawler
```

### Development Environment

```bash
# Open in DevContainer
# VS Code → Command Palette → "Remote-Containers: Reopen in Container"

# Install dependencies
pip install -r requirements-dev.txt

# Setup git hooks (one-time setup)
bash setup-git-hooks.sh

# Run tests
pytest -q

# Lint and format
ruff check .
black --check .

# On Windows: Make scripts executable for git
git add --chmod=+x nightly_backup.sh
git add --chmod=+x setup-git-hooks.sh
```

## QStash Integration Examples

### Manual Message Publishing

```bash
# Basic message with delay
curl -X POST "https://qstash.upstash.io/v2/publish" \
  -H "Authorization: Bearer ${QSTASH_TOKEN}" \
  -H "Upstash-Delay: 60" \
  -H "Content-Type: application/json" \
  -d '{"id": "test-123", "url": "https://example.com", "ts": "2024-01-01T12:00:00Z"}'

# Message with cron schedule (every 15 minutes)
curl -X POST "https://qstash.upstash.io/v2/publish" \
  -H "Authorization: Bearer ${QSTASH_TOKEN}" \
  -H "Upstash-Cron: */15 * * * *" \
  -H "Content-Type: application/json" \
  -d '{"concept": "bitcoin", "action": "analyze"}'

# Message with retry configuration
curl -X POST "https://qstash.upstash.io/v2/publish" \
  -H "Authorization: Bearer ${QSTASH_TOKEN}" \
  -H "Upstash-Delay: 30" \
  -H "Upstash-Retry: 3" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'

# Non-retryable message (goes to DLQ on first failure)
curl -X POST "https://qstash.upstash.io/v2/publish" \
  -H "Authorization: Bearer ${QSTASH_TOKEN}" \
  -H "Upstash-NonRetryable-Error: true" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://spam-site.com"}'
```

## Health Check Endpoints

### Service Health Checks

```bash
# Orchestrator service
curl http://localhost:8000/health
# Expected: {"status": "healthy", "service": "orchestrator", "services": {"weaviate": "healthy"}}

# Weaviate vector database
curl http://localhost:8080/v1/meta
# Expected: {"hostname": "...", "version": "1.25.4", ...}

# Redis queue
redis-cli -h localhost -p 6379 ping
# Expected: PONG

# Check all services
docker compose ps
# Expected: All services "Up" status
```

### Application Health Monitoring

```bash
# Check queue depth
redis-cli -h localhost -p 6379 llen start_urls

# Check Weaviate objects count
curl http://localhost:8080/v1/objects

# Monitor Docker service logs
docker compose logs -f --tail=50 orchestrator
```

## Backup and Recovery

### Nightly Backup Script (Cloudflare R2)

```bash
#!/usr/bin/env bash
# nightly_backup.sh - Sync Weaviate data to Cloudflare R2 storage

set -euo pipefail

# Configuration
BACKUP_DATE=$(date +%Y-%m-%d_%H-%M-%S)
WEAVIATE_DATA_PATH="./infra/weaviate_data"
R2_BUCKET="trading-backups"

# Configure rclone for Cloudflare R2
export RCLONE_CONFIG_R2_TYPE=s3
export RCLONE_CONFIG_R2_PROVIDER=Cloudflare
export RCLONE_CONFIG_R2_ACCESS_KEY_ID="${R2_KEY}"
export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="${R2_SECRET}"
export RCLONE_CONFIG_R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

echo "Starting backup at $(date)"

# Stop Weaviate to ensure consistent backup
docker compose stop weaviate

# Sync to R2 with progress and parallel transfers
rclone copy "${WEAVIATE_DATA_PATH}" "R2:${R2_BUCKET}/weaviate-data/${BACKUP_DATE}" \
  --progress \
  --transfers 8 \
  --exclude "*.tmp" \
  --exclude "*.lock"

# Restart Weaviate
docker compose start weaviate

echo "Backup completed: R2:${R2_BUCKET}/weaviate-data/${BACKUP_DATE}"
echo "Backup process finished at $(date)"

# Benefits of Cloudflare R2:
# - Zero egress fees (unlike AWS S3)
# - Free tier: 10 GB storage + 1M Class-A operations
# - Native integration with Cloudflare ecosystem
```

### Recovery Procedures

```bash
# Restore from backup
RESTORE_DATE="20240101_120000"
aws s3 cp "s3://your-backup-bucket/qstash-pipeline-backups/${RESTORE_DATE}/" \
  ./weaviate_data_restored/ --recursive

# Replace current data (CAUTION: This will overwrite existing data)
docker compose stop weaviate
rm -rf ./weaviate_data
mv ./weaviate_data_restored ./weaviate_data
docker compose start weaviate
```

## Troubleshooting Guide

### QStash Issues

#### DLQ (Dead Letter Queue) Replay
```bash
# List messages in DLQ
curl -H "Authorization: Bearer ${QSTASH_TOKEN}" \
  "https://qstash.upstash.io/v2/dlq"

# Replay specific message from DLQ
curl -X POST -H "Authorization: Bearer ${QSTASH_TOKEN}" \
  "https://qstash.upstash.io/v2/dlq/MESSAGE_ID/replay"

# Clear all DLQ messages
curl -X DELETE -H "Authorization: Bearer ${QSTASH_TOKEN}" \
  "https://qstash.upstash.io/v2/dlq"
```

#### Flow Control (429 Rate Limiting)
```bash
# Check current rate limits
curl -H "Authorization: Bearer ${QSTASH_TOKEN}" \
  "https://qstash.upstash.io/v2/stats"

# Implement exponential backoff in producer
# Add delay between requests: 1s, 2s, 4s, 8s, etc.
```

#### JWT Signature Verification Failures (401)
```bash
# Verify signing key is correct
echo $QSTASH_SIGNING_KEY

# Test JWT verification manually
python -c "
import jwt
import os
token = 'YOUR_JWT_TOKEN_HERE'
key = os.getenv('QSTASH_SIGNING_KEY')
try:
    decoded = jwt.decode(token, key, algorithms=['EdDSA'])
    print('Valid:', decoded)
except jwt.InvalidTokenError as e:
    print('Invalid:', e)
"

# Common issues:
# - Wrong signing key (check Upstash console)
# - Clock skew (check system time)
# - Token expired (check 'exp' claim)
```

### GPU Issues

#### GPU Not Detected
```bash
# Check GPU availability
python -c "
try:
    import cupy as cp
    print(f'GPU devices: {cp.cuda.runtime.getDeviceCount()}')
    print(f'GPU memory: {cp.cuda.runtime.memGetInfo()}')
except Exception as e:
    print(f'GPU not available: {e}')
"

# Check NVIDIA drivers
nvidia-smi

# Verify Docker GPU support
docker run --rm --gpus all nvidia/cuda:12.0-runtime-ubuntu22.04 nvidia-smi
```

#### CUDA Runtime Errors
```bash
# Common solutions:
# 1. Restart Docker service
sudo systemctl restart docker

# 2. Clear GPU memory
python -c "import cupy as cp; cp.get_default_memory_pool().free_all_blocks()"

# 3. Check CUDA version compatibility
python -c "import cupy; print(cupy.cuda.runtime.runtimeGetVersion())"
```

### Service-Specific Issues

#### Orchestrator Service
```bash
# Check FastAPI logs
docker compose logs orchestrator

# Test webhook endpoint
curl -X POST http://localhost:8000/api/qstash \
  -H "Content-Type: application/json" \
  -H "Upstash-Signature: test-token" \
  -d '{"test": "data"}'
```

#### Parser Service
```bash
# Test parser manually
echo "<html><body>Test content</body></html>" | python services/parser/main.py

# Check embedding model download
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('thenlper/gte-small')"
```

#### Validator Service
```bash
# Test backtest manually
cd services/validator
python main.py

# Check vectorbt installation
python -c "import vectorbt as vbt; print(vbt.__version__)"
```

## Performance Monitoring

### Key Metrics to Monitor

```bash
# Message processing rate
redis-cli -h localhost -p 6379 info stats | grep instantaneous_ops_per_sec

# Memory usage
docker stats --no-stream

# GPU utilization (if available)
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv

# Disk usage
df -h
du -sh ./weaviate_data
```

### Alerting Thresholds

- Queue depth > 1000 messages
- Memory usage > 80%
- GPU memory > 90%
- Disk usage > 85%
- Error rate > 5%

## Security Checklist

- [ ] All secrets stored in environment variables
- [ ] `.env` file in `.gitignore`
- [ ] JWT signature verification enabled
- [ ] Rate limiting configured (500 RPS)
- [ ] Network isolation via Docker networks
- [ ] Regular backup encryption
- [ ] Access logs monitored

## 38-Item Verification Checklist

### Environment Setup
- [ ] 1. `.env` file contains QSTASH_URL, QSTASH_TOKEN, QSTASH_SIGNING_KEY
- [ ] 2. `.env` file contains R2_ACCOUNT_ID, R2_KEY, R2_SECRET for backups
- [ ] 3. `.env` file is in `.gitignore`
- [ ] 4. Docker Desktop is running
- [ ] 5. VS Code DevContainer extensions installed
- [ ] 6. rclone installed and configured for Cloudflare R2

### Build and Infrastructure
- [ ] 5. `docker compose build` completes without errors
- [ ] 6. DevContainer opens successfully with docker-in-docker
- [ ] 7. All service images build successfully
- [ ] 8. Weaviate responds to `curl http://localhost:8080/v1/meta` with 200
- [ ] 9. Redis responds to `redis-cli ping` with PONG
- [ ] 10. Backup script has executable permissions (`git ls-files --stage nightly_backup.sh` shows 100755)

### Edge Worker (Cloudflare)
- [ ] 10. `wrangler deploy` succeeds with 200 OK
- [ ] 11. KV namespace binding configured correctly
- [ ] 12. Edge Worker processes concept requests
- [ ] 13. URLs stored in KV successfully

### Crawler Service
- [ ] 14. Crawler publishes messages to QStash
- [ ] 15. `Upstash-Delay: 60` header included
- [ ] 16. Redis queue integration working
- [ ] 17. httpx.AsyncClient used for non-blocking operations

### QStash Integration
- [ ] 18. QStash webhook receives messages
- [ ] 19. JWT signature verification passes
- [ ] 20. Invalid signatures return 401
- [ ] 21. Messages stored in Weaviate successfully
- [ ] 22. Retry logic works (10s, 30s, 60s)
- [ ] 23. DLQ receives failed messages after max retries
- [ ] 24. Cron scheduling works (`Upstash-Cron: */15 * * * *`)
- [ ] 25. Rate limiting at 500 RPS configured

### Parser Service
- [ ] 26. Arrow IPC output format validated
- [ ] 27. IPC stream size < 1 MB
- [ ] 28. SentenceTransformer embeddings generated
- [ ] 29. HTML tag stripping works correctly

### Validator Service
- [ ] 30. GPU detection via `cupy.cuda.runtime.getDeviceCount() > 0`
- [ ] 31. CPU fallback works when GPU unavailable
- [ ] 32. vectorbt backtesting completes
- [ ] 33. Results saved in pickle format

### Testing
- [ ] 34. `pytest -q` all tests pass
- [ ] 35. GPU tests skip when hardware unavailable
- [ ] 36. respx mocks httpx calls correctly
- [ ] 37. Arrow IPC round-trip tests pass

### CI/CD and Quality
- [ ] 38. GitHub Actions workflow passes
- [ ] 39. `ruff check .` returns 0 errors
- [ ] 40. `black --check .` passes formatting check
- [ ] 41. Docker images build in CI
- [ ] 42. Edge Worker tests pass (`npm test`)

### Monitoring and Operations
- [ ] 43. Health endpoints return 200
- [ ] 44. Backup script syncs to R2 successfully
- [ ] 45. DLQ replay procedures documented
- [ ] 46. JWT troubleshooting guide complete
- [ ] 47. GPU fallback procedures tested

### Security and Compliance
- [ ] 48. No secrets in version control
- [ ] 49. Environment variables validated at startup
- [ ] 50. Network isolation configured
- [ ] 51. Access logging enabled

## Emergency Contacts and Resources

- **QStash Documentation**: https://upstash.com/docs/qstash
- **Weaviate Documentation**: https://weaviate.io/developers/weaviate
- **vectorbt Documentation**: https://vectorbt.dev/
- **Docker Compose Reference**: https://docs.docker.com/compose/

---

**Last Updated**: $(date)
**Version**: 1.0.0
**Maintainer**: QStash Pipeline Team