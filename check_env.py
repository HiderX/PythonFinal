try:
    import akshare
    import yfinance
    import openai
    import rich
    import dotenv
    import pandas
    import requests
    print("All dependencies imported successfully!")
except ImportError as e:
    print(f"Import failed: {e}")
    exit(1)
