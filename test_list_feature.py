from stock_data import StockDataProvider
from ui import display_stock_list, console
import os

def test_list_feature():
    print("Testing Stock List Feature...")
    
    provider = StockDataProvider(use_proxy=False)
    
    # 1. Test CN
    print("\nFetching CN stock list (First 5000+ items usually)...")
    try:
        cn_list = provider.get_stock_list("CN")
        print(f"CN List Size: {len(cn_list)}")
        
        if not cn_list:
            print("Network issue detected. Using MOCK data for UI verification.")
            cn_list = [
                {"symbol": f"600{i:03d}", "name": f"Mock Stock {i}", "price": 10.5 + i, "change_percent": 1.2 if i%2==0 else -0.5, "volume": 1000*i}
                for i in range(1, 55) # 55 items, should be 3 pages (20 per page)
            ]
            
        print("Displaying Page 1 (Expected: 20 items)...")
        display_stock_list(cn_list, page=1, page_size=20)
        
        print("\nDisplaying Page 3 (Expected: 15 items)...")
        display_stock_list(cn_list, page=3, page_size=20)
        
    except Exception as e:
        print(f"CN Fetch Error: {e}")

    # 2. Test US
    print("\nFetching US stock list...")
    try:
        us_list = provider.get_stock_list("US")
        print(f"US List Size: {len(us_list)}")
        if us_list:
             print("Displaying Page 1 (Mock UI):")
             display_stock_list(us_list, page=1, page_size=10)
        else:
             print("US list is empty or API unavailable.")
    except Exception as e:
        print(f"US Fetch Error: {e}")

if __name__ == "__main__":
    test_list_feature()
