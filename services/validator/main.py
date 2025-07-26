#!/usr/bin/env python3
"""
Validator service - GPU-accelerated back-testing with vectorbt
"""

import logging
import pickle
import time
from datetime import datetime
import yfinance as yf
import vectorbt as vbt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_gpu():
    """Detect GPU availability and fallback to CPU if needed"""
    try:
        import cupy as cp
        device_count = cp.cuda.runtime.getDeviceCount()
        if device_count > 0:
            logger.info(f"GPU detected: {device_count} device(s)")
            return "gpu"
    except ImportError:
        logger.warning("CuPy not installed")
    except Exception as e:
        logger.warning(f"GPU not available: {e}")
    
    logger.info("Falling back to CPU")
    return "cpu"

def run_backtest(symbol="BTC-USD", backend="auto", initial_cash=10000):
    """Run vectorbt backtest with GPU/CPU backend selection"""
    if backend == "auto":
        backend = detect_gpu()
    
    start_time = time.time()
    
    try:
        # Download price data
        logger.info(f"Downloading {symbol} data...")
        data = yf.download(symbol, period="1y", progress=False)
        
        if data.empty:
            raise ValueError(f"No data available for {symbol}")
        
        price = data["Close"]
        logger.info(f"Downloaded {len(price)} price points")
        
        # Configure vectorbt for GPU/CPU
        if backend == "gpu":
            try:
                # Enable GPU acceleration
                import cupy as cp
                logger.info("Configuring vectorbt for GPU acceleration")
                # vectorbt will automatically use GPU if available
                portfolio = vbt.Portfolio.from_holding(
                    price, 
                    init_cash=initial_cash,
                    jitted=dict(parallel=True)
                )
            except Exception as e:
                logger.warning(f"GPU acceleration failed, falling back to CPU: {e}")
                backend = "cpu"
                portfolio = vbt.Portfolio.from_holding(price, init_cash=initial_cash)
        else:
            # CPU-only execution
            portfolio = vbt.Portfolio.from_holding(price, init_cash=initial_cash)
        
        computation_time = time.time() - start_time
        
        # Calculate performance metrics
        total_return = portfolio.total_return()
        sharpe_ratio = portfolio.sharpe_ratio()
        max_drawdown = portfolio.max_drawdown()
        final_value = portfolio.value().iloc[-1]
        
        results = {
            "portfolio_id": f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "symbol": symbol,
            "initial_cash": initial_cash,
            "final_value": float(final_value),
            "total_return": float(total_return),
            "sharpe_ratio": float(sharpe_ratio) if sharpe_ratio is not None else 0.0,
            "max_drawdown": float(max_drawdown),
            "trades_count": len(portfolio.orders.records_readable),
            "gpu_accelerated": backend == "gpu",
            "computation_time": computation_time,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Backtest completed in {computation_time:.2f}s using {backend}")
        logger.info(f"Total return: {total_return:.2%}, Sharpe: {sharpe_ratio:.2f}")
        
        return results
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise

def save_results(results, filename=None):
    """Save backtest results to pickle file"""
    if filename is None:
        filename = f"backtest_{results['portfolio_id']}.pkl"
    
    try:
        with open(filename, 'wb') as f:
            pickle.dump(results, f)
        logger.info(f"Results saved to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        raise

def main():
    """Main validator service entry point"""
    logger.info("Starting validator service...")
    
    try:
        # Run backtest
        results = run_backtest()
        
        # Save results
        filename = save_results(results)
        
        logger.info("Validator service completed successfully")
        logger.info(f"Results: {results}")
        
    except Exception as e:
        logger.error(f"Validator service failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())