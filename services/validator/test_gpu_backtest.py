#!/usr/bin/env python3
"""
Unit tests for GPU backtest functionality
"""

import pytest
import pickle
import os
from unittest.mock import patch, MagicMock
from main import detect_gpu, run_backtest, save_results

def test_detect_gpu_available():
    """Test GPU detection when GPU is available"""
    with patch('cupy.cuda.runtime.getDeviceCount', return_value=1):
        backend = detect_gpu()
        assert backend == "gpu"

def test_detect_gpu_not_available():
    """Test GPU detection when GPU is not available"""
    with patch('cupy.cuda.runtime.getDeviceCount', side_effect=Exception("No GPU")):
        backend = detect_gpu()
        assert backend == "cpu"

def test_detect_gpu_cupy_not_installed():
    """Test GPU detection when CuPy is not installed"""
    with patch('builtins.__import__', side_effect=ImportError("No module named 'cupy'")):
        backend = detect_gpu()
        assert backend == "cpu"

@pytest.mark.skipif(
    detect_gpu() == "cpu", 
    reason="GPU not available for testing"
)
def test_run_backtest_gpu():
    """Test backtest with GPU backend (only if GPU available)"""
    results = run_backtest(symbol="BTC-USD", backend="gpu", initial_cash=1000)
    
    assert results["gpu_accelerated"] is True
    assert results["initial_cash"] == 1000
    assert "total_return" in results
    assert "sharpe_ratio" in results
    assert "max_drawdown" in results
    assert results["computation_time"] > 0

def test_run_backtest_cpu():
    """Test backtest with CPU backend"""
    # Mock yfinance to avoid network calls in tests
    mock_data = MagicMock()
    mock_data.empty = False
    mock_data.__getitem__.return_value = [100, 101, 102, 103, 104]  # Mock price data
    
    with patch('yfinance.download', return_value=mock_data):
        with patch('vectorbt.Portfolio.from_holding') as mock_portfolio:
            # Mock portfolio methods
            mock_pf = MagicMock()
            mock_pf.total_return.return_value = 0.05
            mock_pf.sharpe_ratio.return_value = 1.2
            mock_pf.max_drawdown.return_value = 0.1
            mock_pf.value.return_value.iloc = [-1]
            mock_pf.value.return_value.iloc.__getitem__.return_value = 1050
            mock_pf.orders.records_readable = []
            mock_portfolio.return_value = mock_pf
            
            results = run_backtest(symbol="TEST", backend="cpu", initial_cash=1000)
            
            assert results["gpu_accelerated"] is False
            assert results["initial_cash"] == 1000
            assert results["symbol"] == "TEST"

def test_save_results():
    """Test saving results to pickle file"""
    test_results = {
        "portfolio_id": "test_123",
        "total_return": 0.05,
        "gpu_accelerated": False
    }
    
    filename = save_results(test_results)
    
    # Verify file was created
    assert os.path.exists(filename)
    
    # Verify contents
    with open(filename, 'rb') as f:
        loaded_results = pickle.load(f)
    
    assert loaded_results == test_results
    
    # Cleanup
    os.remove(filename)

def test_run_backtest_no_data():
    """Test backtest with no data available"""
    mock_data = MagicMock()
    mock_data.empty = True
    
    with patch('yfinance.download', return_value=mock_data):
        with pytest.raises(ValueError, match="No data available"):
            run_backtest(symbol="INVALID")

if __name__ == "__main__":
    pytest.main([__file__])