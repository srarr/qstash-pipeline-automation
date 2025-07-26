#!/usr/bin/env python3
"""
Unit tests for QStash producer
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch
import httpx
import respx

from main import publish_to_qstash

@pytest.mark.asyncio
async def test_publish_to_qstash_success():
    """Test successful QStash message publishing"""
    test_url = "https://example.com/test"
    
    with respx.mock:
        # Mock the QStash API response
        respx.post("https://qstash.upstash.io/v2/publish").mock(
            return_value=httpx.Response(200, json={"messageId": "test-id"})
        )
        
        with patch.dict('os.environ', {
            'QSTASH_URL': 'https://qstash.upstash.io/v2/publish',
            'QSTASH_TOKEN': 'test-token'
        }):
            response = await publish_to_qstash(test_url)
            
            assert response.status_code == 200
            
            # Verify the request was made with correct headers
            request = respx.calls.last.request
            assert request.headers["Authorization"] == "Bearer test-token"
            assert request.headers["Upstash-Delay"] == "60"
            assert request.headers["Content-Type"] == "application/json"
            
            # Verify the payload structure
            payload = json.loads(request.content)
            assert payload["url"] == test_url
            assert "id" in payload
            assert "ts" in payload

@pytest.mark.asyncio
async def test_publish_to_qstash_http_error():
    """Test QStash API error handling"""
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

if __name__ == "__main__":
    pytest.main([__file__])