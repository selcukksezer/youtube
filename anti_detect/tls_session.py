"""
Chrome TLS Impersonation Session (JA3 / JA4 Protocol)
Covers items: 22
"""
import requests
from typing import Optional

try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    curl_requests = None
    CURL_CFFI_AVAILABLE = False

class TlsChromeSession:
    """
    Simulates genuine Google Chrome TLS handshake (JA3/JA4 fingerprint) using curl_cffi (Rule 22).
    Eliminates Python-requests signature leak during API or HTTP calls.
    """
    def __init__(self, impersonate: str = "chrome124", proxy_url: Optional[str] = None):
        self.impersonate = impersonate
        self.proxy_url = proxy_url
        if CURL_CFFI_AVAILABLE:
            proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
            self.session = curl_requests.Session(impersonate=impersonate, proxies=proxies)
        else:
            self.session = requests.Session()

    def get(self, url: str, **kwargs):
        if CURL_CFFI_AVAILABLE and "impersonate" not in kwargs:
            kwargs["impersonate"] = self.impersonate
        return self.session.get(url, **kwargs)

    def post(self, url: str, **kwargs):
        if CURL_CFFI_AVAILABLE and "impersonate" not in kwargs:
            kwargs["impersonate"] = self.impersonate
        return self.session.post(url, **kwargs)
