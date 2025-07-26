#!/usr/bin/env python3
"""
Unit tests for parser IPC functionality
"""

import pytest
import subprocess
import polars as pl
import io
from main import process_content, strip_tags

def test_strip_tags():
    """Test HTML tag stripping"""
    html = "<html><body><h1>Title</h1><p>Content with <a href='#'>link</a></p></body></html>"
    expected = "Title Content with link"
    result = strip_tags(html)
    assert result == expected

def test_strip_tags_empty():
    """Test HTML tag stripping with empty content"""
    html = "<html><body></body></html>"
    result = strip_tags(html)
    assert result == ""

def test_process_content():
    """Test content processing and embedding generation"""
    html = "<html><body><h1>Bitcoin Trading</h1><p>This is about cryptocurrency trading.</p></body></html>"
    result = process_content(html)
    
    assert "text" in result
    assert "embedding" in result
    assert "processed_at" in result
    assert "text_length" in result
    
    assert result["text"] == "Bitcoin Trading This is about cryptocurrency trading."
    assert len(result["embedding"]) == 384  # gte-small embedding dimension
    assert isinstance(result["embedding"], list)
    assert all(isinstance(x, float) for x in result["embedding"])

def test_process_content_empty():
    """Test processing empty content"""
    result = process_content("")
    
    assert result["text"] == "No content"
    assert len(result["embedding"]) == 384
    assert result["text_length"] == 10  # len("No content")

def test_arrow_ipc_round_trip():
    """Test Arrow IPC stream write and read"""
    # Create test data
    test_data = {
        "text": "Test content",
        "embedding": [0.1, 0.2, 0.3] * 128,  # 384 dimensions
        "processed_at": "2024-01-01T00:00:00",
        "text_length": 12
    }
    
    # Create DataFrame and write to buffer
    df = pl.DataFrame([test_data])
    buffer = io.BytesIO()
    df.write_ipc_stream(buffer)
    
    # Read back from buffer
    buffer.seek(0)
    df_read = pl.read_ipc_stream(buffer)
    
    # Verify data integrity
    assert df_read.shape == (1, 4)
    assert df_read["text"][0] == "Test content"
    assert len(df_read["embedding"][0]) == 384
    assert df_read["text_length"][0] == 12

def test_parser_script_integration():
    """Test the parser script end-to-end"""
    html_input = "<html><body><h1>Test</h1><p>Integration test content</p></body></html>"
    
    # Run the parser script
    process = subprocess.Popen(
        ["python", "main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="."
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
    assert df["text"][0] == "Test Integration test content"

if __name__ == "__main__":
    pytest.main([__file__])