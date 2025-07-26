#!/usr/bin/env bash
# Test R2 configuration

export R2_ACCOUNT_ID="199aa822a7dfdac0c5551898c85397a8"
export R2_KEY="4893443d6aa93ca2533b3ef056685e1"
export R2_SECRET="c41bcc7b5caf6d4eea7e93ab3544730e260f4395615f6f426d650a022aa6b"

# Configure rclone for Cloudflare R2
export RCLONE_CONFIG_R2_TYPE=s3
export RCLONE_CONFIG_R2_PROVIDER=Cloudflare
export RCLONE_CONFIG_R2_ACCESS_KEY_ID="${R2_KEY}"
export RCLONE_CONFIG_R2_SECRET_ACCESS_KEY="${R2_SECRET}"
export RCLONE_CONFIG_R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

echo "R2 Configuration Test:"
echo "Account ID: ${R2_ACCOUNT_ID}"
echo "Endpoint: https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
echo "Bucket: trading-backups"

# Test if rclone can list the bucket
if command -v rclone &> /dev/null; then
    echo "Testing R2 connection..."
    rclone lsd R2:trading-backups || echo "Bucket listing failed (expected if empty)"
else
    echo "rclone not found - install with: curl -fsSL https://rclone.org/install.sh | bash"
fi