
import akshare as ak
import pandas as pd
import sys

# Suppress warnings
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

def check_akshare():
    print("Fetching akshare spot data...")
    try:
        df = ak.stock_zh_a_spot_em()
        # Filter for ONE code to check
        target = "920925" 
        row = df[df['代码'] == target]
        if not row.empty:
            print(f"Found {target}:")
            print(row.iloc[0])
            price = row.iloc[0]['最新价']
            print(f"Price raw type: {type(price)}")
            print(f"Price value: {price}")
        else:
            print(f"Code {target} not found in akshare results.")
            
        # Check general 920 stats
        beijing_new = df[df['代码'].astype(str).str.startswith('920')]
        print(f"\nFound {len(beijing_new)} stocks starting with 920.")
        if not beijing_new.empty:
            print("Sample prices:")
            print(beijing_new[['代码', '名称', '最新价']].head())

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_akshare()
