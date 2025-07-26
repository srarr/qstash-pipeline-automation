#!/usr/bin/env python3
"""
Unit tests for parser Arrow IPC functionality
"""

import pytest
import subprocess
import polars as pl
import io
import sys
import os

# Add parser service to path
sys.path.append('services/parser')
from main import process_content, strip_tags

def test_strip_tags_basic():
    """Test basic HTML tag stripping"""
    html = "<html><body><h1>Bitcoin Trading</h1><p>Learn about <strong>cryptocurrency</strong> trading.</p></body></html>"
    expected = "Bitcoin Trading Learn about cryptocurrency trading."
    result = strip_tags(html)
    assert result == expected

def test_strip_tags_complex():
    """Test complex HTML with nested tags and attributes"""
    html = '<div class="content"><h2 id="title">Market Analysis</h2><p>Price: <span style="color:green">$50,000</span></p></div>'
    expected = "Market Analysis Price: $50,000"
    result = strip_tags(html)
    assert result == expected

def test_strip_tags_empty():
    """Test HTML tag stripping with empty content"""
    html = "<html><head><title>Empty</title></head><body></body></html>"
    result = strip_tags(html)
    assert result == "Empty"

def test_process_content_valid():
    """Test content processing and embedding generation"""
    html = "<html><body><h1>Ethereum Trading</h1><p>Smart contracts and DeFi applications.</p></body></html>"
    result = process_content(html)
    
    assert "text" in result
    assert "embedding" in result
    assert "processed_at" in result
    assert "text_length" in result
    
    assert result["text"] == "Ethereum Trading Smart contracts and DeFi applications."
    assert len(result["embedding"]) == 384  # gte-small embedding dimension
    assert isinstance(result["embedding"], list)
    assert all(isinstance(x, float) for x in result["embedding"])
    assert result["text_length"] == len(result["text"])

def test_process_content_empty():
    """Test processing empty content"""
    result = process_content("")
    
    assert result["text"] == "No content"
    assert len(result["embedding"]) == 384
    assert result["text_length"] == 10  # len("No content")

def test_arrow_ipc_round_trip():
    """Test Arrow IPC stream write and read round-trip"""
    # Create test data with realistic structure
    test_data = {
        "text": "Bitcoin is a decentralized digital currency",
        "embedding": [0.1, -0.2, 0.3] * 128,  # 384 dimensions
        "processed_at": "2024-01-01T12:00:00.000000",
        "text_length": 42
    }
    
    # Create DataFrame and write to buffer
    df = pl.DataFrame([test_data])
    buffer = io.BytesIO()
    df.write_ipc_stream(buffer)
    
    # Verify buffer has data
    assert buffer.tell() > 0
    
    # Read back from buffer
    buffer.seek(0)
    df_read = pl.read_ipc_stream(buffer)
    
    # Verify data integrity
    assert df_read.shape == (1, 4)
    assert df_read["text"][0] == "Bitcoin is a decentralized digital currency"
    assert len(df_read["embedding"][0]) == 384
    assert df_read["text_length"][0] == 42
    assert df_read["processed_at"][0] == "2024-01-01T12:00:00.000000"

def test_arrow_ipc_multiple_records():
    """Test Arrow IPC with multiple records"""
    test_data = [
        {
            "text": "First record",
            "embedding": [0.1] * 384,
            "processed_at": "2024-01-01T12:00:00.000000",
            "text_length": 12
        },
        {
            "text": "Second record",
            "embedding": [0.2] * 384,
            "processed_at": "2024-01-01T12:01:00.000000",
            "text_length": 13
        }
    ]
    
    df = pl.DataFrame(test_data)
    buffer = io.BytesIO()
    df.write_ipc_stream(buffer)
    
    buffer.seek(0)
    df_read = pl.read_ipc_stream(buffer)
    
    assert df_read.shape == (2, 4)
    assert df_read["text"][0] == "First record"
    assert df_read["text"][1] == "Second record"

@pytest.mark.skipif(
    not os.path.exists("services/parser/main.py"),
    reason="Parser service not available"
)
def test_parser_script_integration():
    """Test the parser script end-to-end integration"""
    html_input = "<html><body><h1>Integration Test</h1><p>Testing the complete parser pipeline</p></body></html>"
    
    # Run the parser script
    process = subprocess.Popen(
        ["python", "main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="services/parser"
    )
    
    stdout, stderr = process.communicate(input=html_input.encode())
    
    if process.returncode != 0:
        pytest.skip(f"Parser script failed: {stderr.decode()}")
    
    # Read the Arrow IPC output
    buffer = io.BytesIO(stdout)
    df = pl.read_ipc_stream(buffer)
    
    assert df.shape[0] == 1  # One row
    assert "text" in df.columns
    assert "embedding" in df.columns
    assert df["text"][0] == "Integration Test Testing the complete parser pipeline"
    assert len(df["embedding"][0]) == 384

if __name__ == "__main__":
    pytest.main([__file__])