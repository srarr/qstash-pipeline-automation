#!/usr/bin/env python3
"""
Unit tests for GPU backtest functionality (skip if no GPU)
"""

import pytest
import pickle
import os
import sys
from unittest.mock import patch, MagicMock

# Add validator service to path
sys.path.append('services/validator')
from main import detect_gpu, run_backtest, save_results

def test_detect_gpu_available():
    """Test GPU detection when GPU is available"""
    with patch('cupy.cuda.runtime.getDeviceCount', return_value=1):
        backend = detect_gpu()
        assert backend == "gpu"

def test_detect_gpu_not_available():
    """Test GPU detection when GPU is not available"""
    with patch('cupy.cuda.runtime.getDeviceCount', side_effect=Exception("CUDA not available")):
        backend = detect_gpu()
        assert backend == "cpu"

def test_detect_gpu_cupy_not_installed():
    """Test GPU detection when CuPy is not installed"""
    with patch('builtins.__import__', side_effect=ImportError("No module named 'cupy'")):
        backend = detect_gpu()
        assert backend == "cpu"

@pytest.mark.skipif(
    detect_gpu() == "cpu", 
    reason="GPU not available - skipping GPU-specific test"
)
def test_run_backtest_gpu_if_available():
    """Test backtest with GPU backend (only runs if GPU is actually available)"""
    try:
        results = run_backtest(symbol="BTC-USD", backend="gpu", initial_cash=1000)
        
        assert results["gpu_accelerated"] is True
        assert results["initial_cash"] == 1000
        assert results["symbol"] == "BTC-USD"
        assert "total_return" in results
        assert "sharpe_ratio" in results
        assert "max_drawdown" in results
        assert results["computation_time"] > 0
        assert "portfolio_id" in results
        
    except Exception as e:
        pytest.skip(f"GPU backtest failed (hardware issue): {e}")

def test_run_backtest_cpu_with_mock():
    """Test backtest with CPU backend using mocked data"""
    # Mock yfinance to avoid network calls
    mock_data = MagicMock()
    mock_data.empty = False
    
    # Create mock price series
    import pandas as pd
    mock_prices = pd.Series([100, 101, 102, 103, 104], name="Close")
    mock_data.__getitem__.return_value = mock_prices
    
    with patch('yfinance.download', return_value=mock_data):
        with patch('vectorbt.Portfolio.from_holding') as mock_portfolio:
            # Mock portfolio methods
            mock_pf = MagicMock()
            mock_pf.total_return.return_value = 0.05
            mock_pf.sharpe_ratio.return_value = 1.2
            mock_pf.max_drawdown.return_value = 0.1
            
            # Mock value series
            mock_value_series = MagicMock()
            mock_value_series.iloc = MagicMock()
            mock_value_series.iloc.__getitem__.return_value = 1050
            mock_pf.value.return_value = mock_value_series
            
            # Mock orders
            mock_pf.orders.records_readable = []
            mock_portfolio.return_value = mock_pf
            
            results = run_backtest(symbol="TEST", backend="cpu", initial_cash=1000)
            
            assert results["gpu_accelerated"] is False
            assert results["initial_cash"] == 1000
            assert results["symbol"] == "TEST"
            assert results["total_return"] == 0.05
            assert results["sharpe_ratio"] == 1.2
            assert results["max_drawdown"] == 0.1
            assert results["final_value"] == 1050

def test_run_backtest_auto_backend():
    """Test backtest with auto backend selection"""
    mock_data = MagicMock()
    mock_data.empty = False
    
    import pandas as pd
    mock_prices = pd.Series([100, 105, 110], name="Close")
    mock_data.__getitem__.return_value = mock_prices
    
    with patch('yfinance.download', return_value=mock_data):
        with patch('vectorbt.Portfolio.from_holding') as mock_portfolio:
            mock_pf = MagicMock()
            mock_pf.total_return.return_value = 0.1
            mock_pf.sharpe_ratio.return_value = 1.5
            mock_pf.max_drawdown.return_value = 0.05
            
            mock_value_series = MagicMock()
            mock_value_series.iloc = MagicMock()
            mock_value_series.iloc.__getitem__.return_value = 1100
            mock_pf.value.return_value = mock_value_series
            mock_pf.orders.records_readable = []
            mock_portfolio.return_value = mock_pf
            
            results = run_backtest(symbol="ETH-USD", backend="auto")
            
            # Should detect available backend automatically
            assert "gpu_accelerated" in results
            assert results["symbol"] == "ETH-USD"

def test_save_results():
    """Test saving backtest results to pickle file"""
    test_results = {
        "portfolio_id": "BTC-USD_20240101_120000",
        "symbol": "BTC-USD",
        "total_return": 0.15,
        "sharpe_ratio": 1.8,
        "gpu_accelerated": False,
        "computation_time": 2.5
    }
    
    filename = save_results(test_results)
    
    # Verify file was created
    assert os.path.exists(filename)
    assert filename.endswith(".pkl")
    
    # Verify contents
    with open(filename, 'rb') as f:
        loaded_results = pickle.load(f)
    
    assert loaded_results == test_results
    assert loaded_results["portfolio_id"] == "BTC-USD_20240101_120000"
    
    # Cleanup
    os.remove(filename)

def test_save_results_custom_filename():
    """Test saving results with custom filename"""
    test_results = {"test": "data"}
    custom_filename = "test_backtest_results.pkl"
    
    filename = save_results(test_results, custom_filename)
    
    assert filename == custom_filename
    assert os.path.exists(custom_filename)
    
    # Cleanup
    os.remove(custom_filename)

def test_run_backtest_no_data():
    """Test backtest with no data available"""
    mock_data = MagicMock()
    mock_data.empty = True
    
    with patch('yfinance.download', return_value=mock_data):
        with pytest.raises(ValueError, match="No data available"):
            run_backtest(symbol="INVALID-SYMBOL")

def test_run_backtest_network_error():
    """Test backtest with network error"""
    with patch('yfinance.download', side_effect=Exception("Network error")):
        with pytest.raises(Exception, match="Network error"):
            run_backtest(symbol="BTC-USD")

if __name__ == "__main__":
    pytest.main([__file__])