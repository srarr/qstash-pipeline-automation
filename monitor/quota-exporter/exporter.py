#!/usr/bin/env python3
"""
Custom Prometheus exporter for R2 and QStash quota metrics
"""

import os
import time
import requests
import boto3
from prometheus_client import start_http_server, Gauge, Info
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
r2_storage_bytes = Gauge('r2_storage_bytes', 'R2 storage usage in bytes')
qstash_daily_remaining = Gauge('qstash_daily_remaining', 'QStash daily messages remaining')
qstash_messages_sent_total = Gauge('qstash_messages_sent_total', 'Total QStash messages sent today')
quota_info = Info('quota_exporter', 'Quota exporter information')

class QuotaExporter:
    def __init__(self):
        self.r2_account_id = os.getenv('R2_ACCOUNT_ID')
        self.r2_key = os.getenv('R2_KEY')
        self.r2_secret = os.getenv('R2_SECRET')
        self.qstash_token = os.getenv('QSTASH_TOKEN')
        
        # Initialize R2 client
        if all([self.r2_account_id, self.r2_key, self.r2_secret]):
            self.r2_client = boto3.client(
                's3',
                endpoint_url=f'https://{self.r2_account_id}.r2.cloudflarestorage.com',
                aws_access_key_id=self.r2_key,
                aws_secret_access_key=self.r2_secret,
                region_name='auto'
            )
        else:
            self.r2_client = None
            logger.warning("R2 credentials not found, R2 metrics will be unavailable")
    
    def get_r2_usage(self):
        """Get R2 storage usage"""
        if not self.r2_client:
            return 0
        
        try:
            # List objects in trading-backups bucket and calculate total size
            response = self.r2_client.list_objects_v2(Bucket='trading-backups')
            total_size = 0
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    total_size += obj['Size']
            
            logger.info(f"R2 storage usage: {total_size} bytes")
            return total_size
            
        except Exception as e:
            logger.error(f"Failed to get R2 usage: {e}")
            return 0
    
    def get_qstash_usage(self):
        """Get QStash daily usage"""
        if not self.qstash_token:
            logger.warning("QStash token not found")
            return 500, 0  # Default values
        
        try:
            headers = {
                'Authorization': f'Bearer {self.qstash_token}',
                'Content-Type': 'application/json'
            }
            
            # Get QStash usage from API
            response = requests.get(
                'https://qstash.upstash.io/v2/usage',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                daily_remaining = data.get('dailyRemaining', 500)
                messages_sent = 500 - daily_remaining
                
                logger.info(f"QStash usage: {messages_sent}/500 messages sent today")
                return daily_remaining, messages_sent
            else:
                logger.error(f"QStash API error: {response.status_code}")
                return 500, 0
                
        except Exception as e:
            logger.error(f"Failed to get QStash usage: {e}")
            return 500, 0
    
    def collect_metrics(self):
        """Collect all quota metrics"""
        logger.info("Collecting quota metrics...")
        
        # Get R2 storage usage
        r2_usage = self.get_r2_usage()
        r2_storage_bytes.set(r2_usage)
        
        # Get QStash usage
        daily_remaining, messages_sent = self.get_qstash_usage()
        qstash_daily_remaining.set(daily_remaining)
        qstash_messages_sent_total.set(messages_sent)
        
        # Update info metric
        quota_info.info({
            'version': '1.0.0',
            'r2_free_tier_gb': '10',
            'qstash_free_tier_daily': '500'
        })
        
        logger.info("Metrics collection completed")

def main():
    """Main exporter loop"""
    logger.info("Starting quota exporter on port 8080")
    
    exporter = QuotaExporter()
    
    # Start Prometheus metrics server
    start_http_server(8080)
    
    # Collect metrics every 5 minutes
    while True:
        try:
            exporter.collect_metrics()
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
        
        time.sleep(300)  # 5 minutes

if __name__ == '__main__':
    main()