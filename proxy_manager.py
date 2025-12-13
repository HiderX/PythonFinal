import os
import requests
import random
from typing import Optional

class ProxyManager:
    """
    Manages a pool of proxies and provides methods to get a usable proxy.
    Currently supports a static list from environment variables or a default list for testing.
    Future improvements: Integrate with a dynamic proxy provider API.
    """
    def __init__(self):
        self.proxies = self._load_proxies()
        self.current_index = 0

    def _load_proxies(self) -> list:
        """
        Loads proxies from the 'PROXIES' environment variable.
        Format: "http://ip:port,http://user:pass@ip:port"
        """
        proxies_env = os.getenv("PROXIES")
        if proxies_env:
            return [p.strip() for p in proxies_env.split(",") if p.strip()]
        return []

    def get_proxy(self) -> Optional[dict]:
        """
        Returns a proxy dictionary for requests, or None if no proxies are available.
        Rotates through the list of proxies.
        """
        if not self.proxies:
            return None
        
        proxy_url = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        
        return {
            "http": proxy_url,
            "https": proxy_url
        }

    def validate_proxy(self, proxy: dict, test_url: str = "https://www.google.com", timeout: int = 5) -> bool:
        """
        Validates if a proxy is working by making a request to a test URL.
        """
        try:
            response = requests.get(test_url, proxies=proxy, timeout=timeout)
            return response.status_code == 200
        except Exception:
            return False

if __name__ == "__main__":
    # Test the ProxyManager
    pm = ProxyManager()
    print(f"Loaded proxies: {len(pm.proxies)}")
    
    proxy = pm.get_proxy()
    if proxy:
        print(f"Testing proxy: {proxy}")
        is_valid = pm.validate_proxy(proxy)
        print(f"Valid: {is_valid}")
    else:
        print("No proxies configured.")
