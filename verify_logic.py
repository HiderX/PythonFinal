import os
import sys
from dotenv import load_dotenv
load_dotenv()

from stock_data import StockDataProvider
from ai_summarizer import MarketSummarizer
from watchlist import WatchlistManager

def test_headless():
    print("--- Headless Verification ---")
    
    # 1. Test Proxy/Network
    print("[1] Testing Stock Data Fetching...")
    provider = StockDataProvider(use_proxy=os.getenv("PROXIES") is not None)
    
    # Test US Stock
    print("  Fetching AAPL (US)...")
    aapl = provider.get_price("AAPL", "US")
    if aapl and "error" not in aapl:
        print(f"  Success: {aapl['name']} - ${aapl['price']}")
    else:
        print(f"  Failed: {aapl}")

    # Test CN Stock
    print("  Fetching 600519 (CN)...")
    moutai = provider.get_price("600519", "CN")
    if moutai and "error" not in moutai:
        print(f"  Success: {moutai['name']} - ¥{moutai['price']}")
    else:
        print(f"  Failed: {moutai}")

    # 2. Test AI Summary
    print("\n[2] Testing AI Summarizer...")
    summarizer = MarketSummarizer()
    if summarizer.client:
        mock_data = [
            {"name": "Apple", "symbol": "AAPL", "price": 150.0, "change_percent": 1.5},
            {"name": "Moutai", "symbol": "600519", "price": 1800.0, "change_percent": -0.5}
        ]
        print("  Generating summary for mock data...")
        summary = summarizer.summarize_market(mock_data)
        print(f"  Summary Result: {summary[:50]}...")
    else:
        print("  Skipping AI test (No Client configured)")

    print("\n--- Verification Finished ---")

if __name__ == "__main__":
    test_headless()
