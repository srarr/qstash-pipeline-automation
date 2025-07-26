#!/usr/bin/env python3
"""
Unit tests for JWT signature verification
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import jwt

from main import app

client = TestClient(app)

def test_qstash_webhook_missing_signature():
    """Test webhook with missing signature header"""
    response = client.post(
        "/api/qstash",
        json={"test": "data"},
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 401
    assert "Missing Upstash-Signature header" in response.json()["detail"]

def test_qstash_webhook_invalid_signature():
    """Test webhook with invalid signature"""
    with patch.dict('os.environ', {'QSTASH_SIGNING_KEY': 'test-key'}):
        response = client.post(
            "/api/qstash",
            json={"test": "data"},
            headers={
                "Content-Type": "application/json",
                "Upstash-Signature": "invalid.jwt.token"
            }
        )
        assert response.status_code == 401
        assert "Invalid signature" in response.json()["detail"]

@patch('main.weaviate_client')
def test_qstash_webhook_valid_signature(mock_weaviate):
    """Test webhook with valid signature"""
    # Mock Weaviate client
    mock_weaviate.batch.add_data_object = MagicMock()
    
    # Create a valid JWT token for testing
    test_payload = {"sub": "test", "iat": 1234567890}
    test_key = "test-signing-key"
    
    with patch.dict('os.environ', {'QSTASH_SIGNING_KEY': test_key}):
        with patch('jwt.decode') as mock_jwt_decode:
            mock_jwt_decode.return_value = test_payload
            
            response = client.post(
                "/api/qstash",
                json={"id": "test-123", "url": "https://example.com"},
                headers={
                    "Content-Type": "application/json",
                    "Upstash-Signature": "valid.jwt.token"
                }
            )
            
            assert response.status_code == 200
            assert response.json()["ok"] is True
            assert response.json()["processed"] == "test-123"
            
            # Verify JWT decode was called with correct parameters
            mock_jwt_decode.assert_called_once_with(
                "valid.jwt.token",
                test_key,
                algorithms=["EdDSA"]
            )

def test_health_check():
    """Test health check endpoint"""
    with patch('main.weaviate_client') as mock_weaviate:
        mock_weaviate.is_ready.return_value = True
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "orchestrator"
        assert data["services"]["weaviate"] == "healthy"

def test_health_check_weaviate_down():
    """Test health check when Weaviate is down"""
    with patch('main.weaviate_client') as mock_weaviate:
        mock_weaviate.is_ready.return_value = False
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["services"]["weaviate"] == "unhealthy"

if __name__ == "__main__":
    pytest.main([__file__])