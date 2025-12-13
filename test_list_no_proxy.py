import os
# Force disable proxy
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

from stock_data import StockDataProvider
from ui import display_stock_list

def test_list_feature():
    print("Testing Stock List Feature (No Proxy)...")
    
    provider = StockDataProvider(use_proxy=False)
    
    # 1. Test CN
    print("\nFetching CN stock list...")
    try:
        cn_list = provider.get_stock_list("CN")
        print(f"CN List Size: {len(cn_list)}")
        if cn_list:
            display_stock_list(cn_list, page=1, page_size=5)
    except Exception as e:
        print(f"CN Fetch Error: {e}")

    # 2. Test US
    print("\nFetching US stock list...")
    try:
        us_list = provider.get_stock_list("US")
        print(f"US List Size: {len(us_list)}")
    except Exception as e:
        print(f"US Fetch Error: {e}")

if __name__ == "__main__":
    test_list_feature()
