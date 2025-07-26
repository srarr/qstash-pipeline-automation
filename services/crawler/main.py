#!/usr/bin/env python3
"""
Crawler service main entry point
Processes URLs from Redis queue and publishes to QStash
"""

import asyncio
import os
import logging
import json
import uuid
from datetime import datetime
import httpx
import redis.asyncio as aioredis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QSTASH_URL = os.getenv("QSTASH_URL")
QSTASH_TOKEN = os.getenv("QSTASH_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

async def publish_to_qstash(url: str):
    """Publish URL to QStash with delay header"""
    message = {
        "id": str(uuid.uuid4()),
        "url": url,
        "ts": datetime.utcnow().isoformat()
    }
    
    headers = {
        "Authorization": f"Bearer {QSTASH_TOKEN}",
        "Upstash-Delay": "60",  # 60 second delay
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            QSTASH_URL,
            headers=headers,
            json=message
        )
        response.raise_for_status()
        logger.info(f"Published URL {url} to QStash with ID {message['id']}")
        return response

async def main():
    """Main crawler service loop"""
    logger.info("Starting crawler service...")
    
    if not QSTASH_URL or not QSTASH_TOKEN:
        logger.error("QSTASH_URL and QSTASH_TOKEN must be set")
        return
    
    redis_client = aioredis.from_url(REDIS_URL)
    
    try:
        while True:
            # Pop URL from Redis list
            url = await redis_client.lpop("start_urls")
            
            if url:
                url = url.decode('utf-8') if isinstance(url, bytes) else url
                logger.info(f"Processing URL: {url}")
                
                try:
                    await publish_to_qstash(url)
                except Exception as e:
                    logger.error(f"Failed to publish URL {url}: {e}")
            else:
                # No URLs in queue, wait before checking again
                await asyncio.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Crawler service stopped")
    finally:
        await redis_client.close()

if __name__ == "__main__":
    asyncio.run(main())