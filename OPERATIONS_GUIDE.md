# 🛡️ QStash Pipeline - Day-2 Operations Guide

## 🎯 Cost Protection & Monitoring Setup

### 1. Enable Cost Caps & Notifications

#### Cloudflare R2 Usage Alerts
```bash
# Set up in Cloudflare Dashboard
# 1. Go to Billing → Notifications
# 2. Create alert for R2 usage:
#    - Storage: Alert at 8 GB (80% of 10 GB free tier)
#    - Class-A Operations: Alert at 800K (80% of 1M free tier)
#    - Class-B Operations: Alert at 8M (80% of 10M free tier)
```

#### QStash Daily Limits
```bash
# Set up in Upstash Console
# 1. Go to QStash → Settings → Alerts
# 2. Set daily limit: 450 messages (90% of 500 free tier)
# 3. Enable email notifications
```

#### Environment Protection
```bash
# Add to .env file
MAX_CONCEPTS_PER_DAY=50
QSTASH_DAILY_LIMIT=450
R2_STORAGE_ALERT_GB=8
```

### 2. Start Monitoring Stack

#### Launch Prometheus + Grafana + Loki
```bash
# Start monitoring services
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d

# Access dashboards
echo "Grafana: http://localhost:3000 (admin/admin)"
echo "Prometheus: http://localhost:9090"
echo "Loki: http://localhost:3100"
```

#### Key Metrics to Monitor
- **Weaviate Memory**: Keep heap usage < 80%
- **QStash Rate**: Monitor daily message count
- **Service Health**: All services up and responding
- **R2 Storage**: Track backup storage growth
- **GPU Utilization**: Monitor validator performance

### 3. Load Testing

#### Run 50 Concepts/Day Test
```bash
# Set environment variables
export QSTASH_TOKEN="your_token_here"
export MAX_CONCEPTS=50

# Run load test
chmod +x load-test.sh
./load-test.sh

# Monitor results in Grafana dashboard
```

#### Expected Results
- **Message Rate**: ~50 messages over test period
- **Processing Time**: < 5 minutes per concept
- **Memory Usage**: Weaviate heap < 80%
- **Error Rate**: < 5%
- **Free Tier Usage**: Well within limits

### 4. Production Checklist

#### Daily Operations
- [ ] Check Grafana dashboard for red alerts
- [ ] Verify QStash message count < 450/day
- [ ] Monitor R2 storage growth < 8 GB
- [ ] Confirm all services healthy (green status)
- [ ] Review error logs in Loki

#### Weekly Operations
- [ ] Run backup verification: `bash nightly_backup.sh --dry-run`
- [ ] Check GPU validator performance metrics
- [ ] Review and rotate logs if needed
- [ ] Update dependencies if security patches available
- [ ] Verify CI/CD pipeline still green

#### Monthly Operations
- [ ] Review cost usage reports (should be $0)
- [ ] Update monitoring alert thresholds if needed
- [ ] Performance optimization review
- [ ] Backup retention cleanup (keep last 30 days)
- [ ] Security audit of secrets and access

### 5. Alert Response Playbook

#### High Memory Usage (Weaviate > 80%)
```bash
# 1. Check current usage
curl http://localhost:8080/v1/metrics | grep heap

# 2. Restart Weaviate if needed
docker compose restart weaviate

# 3. Consider data cleanup or scaling
```

#### QStash Rate Limit Approaching
```bash
# 1. Check current usage in Upstash console
# 2. Temporarily reduce concept processing
# 3. Implement backoff strategy in crawler

# Emergency stop
docker compose stop crawler
```

#### Service Down Alert
```bash
# 1. Check service status
docker compose ps

# 2. View logs for errors
docker compose logs [service_name]

# 3. Restart if needed
docker compose restart [service_name]
```

#### R2 Storage Alert
```bash
# 1. Check current usage
rclone size R2:trading-backups

# 2. Clean old backups
rclone delete R2:trading-backups --min-age 30d

# 3. Consider backup compression
```

### 6. Performance Optimization

#### GPU Validator Tuning
```bash
# Check GPU utilization
nvidia-smi

# Monitor validator processing time
docker compose logs validator | grep "computation_time"

# Adjust batch sizes if needed
```

#### Weaviate Optimization
```bash
# Monitor query performance
curl http://localhost:8080/v1/metrics | grep query_duration

# Optimize vector dimensions if needed
# Consider index tuning for large datasets
```

### 7. Troubleshooting Common Issues

#### Issue: "QStash webhook signature verification failed"
```bash
# Solution: Check QSTASH_SIGNING_KEY in environment
echo $QSTASH_SIGNING_KEY
# Verify key matches Upstash console
```

#### Issue: "R2 backup failed - credentials invalid"
```bash
# Solution: Verify R2 credentials
export R2_ACCOUNT_ID="your_account_id"
export R2_KEY="your_key"
export R2_SECRET="your_secret"

# Test connection
rclone lsd R2:trading-backups
```

#### Issue: "GPU not detected in validator"
```bash
# Solution: Check GPU availability
nvidia-smi
docker run --gpus all nvidia/cuda:12.0-runtime-ubuntu22.04 nvidia-smi

# Verify Docker GPU support
```

### 8. Scaling Considerations

#### When to Scale Up
- Consistent memory usage > 70%
- Processing time > 10 minutes per concept
- Queue backlog > 100 messages
- Error rate > 10%

#### Scaling Options
1. **Horizontal**: Add more validator instances
2. **Vertical**: Increase memory/CPU allocation
3. **Storage**: Upgrade to R2 paid tier if needed
4. **Processing**: Optimize algorithms and batch sizes

---

## 🎯 Success Metrics

Your system is healthy when:
- ✅ All services show green status
- ✅ Memory usage < 80%
- ✅ Processing < 50 concepts/day within free tiers
- ✅ Error rate < 5%
- ✅ Backup success rate > 95%
- ✅ Zero unexpected costs

**With these monitoring and protection measures in place, your QStash Pipeline will run reliably and cost-effectively in production! 🚀**