#!/usr/bin/env python3
"""
Unit tests for QStash producer with respx mocking
"""

import pytest
import asyncio
import json
import os
from unittest.mock import patch
import httpx
import respx

# Import from crawler service
import sys
sys.path.append('services/crawler')
from main import publish_to_qstash

@pytest.mark.asyncio
async def test_publish_to_qstash_success():
    """Test successful QStash message publishing with respx mock"""
    test_url = "https://example.com/test-article"
    
    with respx.mock:
        # Mock the QStash API response
        respx.post("https://qstash.upstash.io/v2/publish").mock(
            return_value=httpx.Response(200, json={"messageId": "msg_123"})
        )
        
        with patch.dict('os.environ', {
            'QSTASH_URL': 'https://qstash.upstash.io/v2/publish',
            'QSTASH_TOKEN': 'test-token-123'
        }):
            response = await publish_to_qstash(test_url)
            
            # Verify response status
            assert response.status_code == 200
            
            # Verify the request was made with correct headers
            request = respx.calls.last.request
            assert request.headers["Authorization"] == "Bearer test-token-123"
            assert request.headers["Upstash-Delay"] == "60"
            assert request.headers["Content-Type"] == "application/json"
            
            # Verify the payload structure
            payload = json.loads(request.content)
            assert payload["url"] == test_url
            assert "id" in payload
            assert "ts" in payload

@pytest.mark.asyncio
async def test_publish_to_qstash_server_error():
    """Test QStash API server error handling"""
    test_url = "https://example.com/test"
    
    with respx.mock:
        # Mock a 500 error response
        respx.post("https://qstash.upstash.io/v2/publish").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        
        with patch.dict('os.environ', {
            'QSTASH_URL': 'https://qstash.upstash.io/v2/publish',
            'QSTASH_TOKEN': 'test-token'
        }):
            with pytest.raises(httpx.HTTPStatusError):
                await publish_to_qstash(test_url)

@pytest.mark.asyncio
async def test_publish_to_qstash_timeout():
    """Test QStash API timeout handling"""
    test_url = "https://example.com/test"
    
    with respx.mock:
        # Mock a timeout
        respx.post("https://qstash.upstash.io/v2/publish").mock(
            side_effect=httpx.TimeoutException("Request timeout")
        )
        
        with patch.dict('os.environ', {
            'QSTASH_URL': 'https://qstash.upstash.io/v2/publish',
            'QSTASH_TOKEN': 'test-token'
        }):
            with pytest.raises(httpx.TimeoutException):
                await publish_to_qstash(test_url)

if __name__ == "__main__":
    pytest.main([__file__])