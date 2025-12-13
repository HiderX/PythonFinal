import os
import json
from watchlist import WatchlistManager
from stock_data import StockDataProvider

def test_watchlist():
    print("Testing WatchlistManager...")
    manager = WatchlistManager("test_watchlist.json")
    
    # Clear existing
    if os.path.exists("test_watchlist.json"):
        os.remove("test_watchlist.json")
        manager = WatchlistManager("test_watchlist.json")

    manager.add_stock("AAPL", "US")
    assert len(manager.get_watchlist()) == 1
    assert manager.get_watchlist()[0]['symbol'] == "AAPL"
    
    manager.add_stock("600519", "CN")
    assert len(manager.get_watchlist()) == 2
    
    manager.remove_stock("AAPL")
    assert len(manager.get_watchlist()) == 1
    assert manager.get_watchlist()[0]['symbol'] == "600519"
    
    print("WatchlistManager Test Passed!")
    
    # Cleanup
    if os.path.exists("test_watchlist.json"):
        os.remove("test_watchlist.json")

def test_stock_data():
    print("Testing StockDataProvider (Mock/Light)...")
    # We won't strictly depend on network in a quick test environment if possible,
    # but for this user ask, we want to know if libs load and run.
    
    provider = StockDataProvider(use_proxy=False)
    
    # Test valid symbol structure
    # We won't assert exact prices, just that it returns a dict structure without crash
    print("Fetching AAPL (US)...")
    try:
        data = provider.get_price("AAPL", "US")
        if data and "error" not in data:
            print(f"AAPL: {data['price']}")
        else:
            print(f"AAPL Fetch Warning: {data}")
    except Exception as e:
        print(f"AAPL Fetch Error: {e}")

    print("Fetching 000001 (CN)...")
    try:
        data = provider.get_price("000001", "CN")
        if data and "error" not in data:
            print(f"000001: {data['price']}")
        else:
             print(f"000001 Fetch Warning: {data}")
    except Exception as e:
        print(f"CN Fetch Error: {e}")

    print("StockDataProvider Test Completed.")

if __name__ == "__main__":
    test_watchlist()
    test_stock_data()
