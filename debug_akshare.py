import requests
import os

print("Testing Proxy Connectivity...")
proxies = {
    "http": os.environ.get("http_proxy"),
    "https": os.environ.get("https_proxy")
}
print(f"Current Proxies: {proxies}")

try:
    print("Requesting Baidu...")
    r = requests.get("https://www.baidu.com", timeout=5)
    print(f"Baidu Status: {r.status_code}")
except Exception as e:
    print(f"Baidu Error: {e}")

try:
    print("Requesting Eastmoney (Direct URL)...")
    # A URL commonly used by akshare
    url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=20&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152"
    r = requests.get(url, timeout=5)
    print(f"Eastmoney Status: {r.status_code}")
except Exception as e:
    print(f"Eastmoney Error: {e}")

    print("--- Debugging Akshare ---")
    try:
        print("Fetching CN Spot...")
        df_cn = ak.stock_zh_a_spot_em()
        if df_cn.empty:
            print("CN DF is empty!")
        else:
            print(f"CN DF Shape: {df_cn.shape}")
            print("CN Columns:", df_cn.columns.tolist())
            print(df_cn.head(2))
            
    except Exception as e:
        print(f"CN Error: {e}")

    try:
        print("\nFetching US Spot...")
        df_us = ak.stock_us_spot_em()
        if df_us.empty:
            print("US DF is empty!")
        else:
            print(f"US DF Shape: {df_us.shape}")
            print("US Columns:", df_us.columns.tolist())
            print(df_us.head(2))
    except Exception as e:
        print(f"US Error: {e}")

if __name__ == "__main__":
    debug_ak()
