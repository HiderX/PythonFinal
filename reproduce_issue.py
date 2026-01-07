
import yfinance as yf
import pandas as pd

def test_single_fetch():
    print("--- Testing Single Fetch ---")
    symbol = "AMZN"
    print(f"Fetching {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        print(f"Price: {info.last_price}")
        print(f"Prev Close: {info.previous_close}")
        
        hist = ticker.history(period="1d")
        print("History head:")
        print(hist.head())
    except Exception as e:
        print(f"Error: {e}")

def test_batch_fetch():
    print("\n--- Testing Batch Fetch ---")
    tickers = ["AMZN", "600519.SS", "TSLA"]
    print(f"Fetching {tickers}...")
    try:
        data = yf.download(tickers, period="1d", group_by='ticker', threads=True)
        print("Data columns:")
        print(data.columns)
        print("Data head:")
        print(data.head())
        
        for t in tickers:
            print(f"\nChecking {t}:")
            try:
                if isinstance(data.columns, pd.MultiIndex):
                    if t in data.columns:
                        df = data[t]
                        print(df)
                    else:
                        print(f"{t} not in columns")
                else:
                    print("Not MultiIndex")
                    print(data)
            except Exception as e:
                print(f"Error extracting {t}: {e}")

    except Exception as e:
        print(f"Batch Error: {e}")

if __name__ == "__main__":
    test_single_fetch()
    test_batch_fetch()
