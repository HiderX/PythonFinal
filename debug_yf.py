
import yfinance as yf

def check_yf_bj():
    symbol = "920925.BJ"
    print(f"Checking {symbol} via yfinance...")
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        print("History:")
        print(hist)
        
        info = ticker.fast_info
        print("\nFast Info:")
        print(f"Last Price: {info.last_price}")
        print(f"Prev Close: {info.previous_close}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_yf_bj()
