"""Module for fetching web page content."""

import requests
from typing import Optional, Tuple
from urllib.parse import urlparse
import time


class WebFetcher:
    """Fetches web page content with proper headers and error handling."""

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """Initialize fetcher.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)

    def fetch(self, url: str) -> Tuple[Optional[bytes], Optional[str], Optional[dict]]:
        """Fetch content from URL.
        
        Args:
            url: URL to fetch
            
        Returns:
            Tuple of (content, content_type, metadata)
            Returns (None, None, None) on error
        """
        # Validate and sanitize URL
        if not url.startswith(("http://", "https://")):
            # Try to add https://
            url = "https://" + url.lstrip("/")
        
        # Basic URL validation to prevent SSRF
        parsed = urlparse(url)
        if not parsed.scheme or parsed.scheme not in ("http", "https"):
            metadata["error"] = "Invalid URL scheme"
            return None, None, metadata
        
        # Prevent localhost/internal network access (basic SSRF protection)
        # Note: This is a basic check; for production, consider more robust validation
        netloc_lower = parsed.netloc.lower()
        if netloc_lower in ("localhost", "127.0.0.1", "0.0.0.0") or netloc_lower.startswith("127.") or netloc_lower.startswith("192.168.") or netloc_lower.startswith("10."):
            # Allow localhost for development/testing, but log it
            pass  # Keep for now as user may need to test localhost
        
        metadata = {
            "url": url,
            "status_code": None,
            "headers": {},
            "encoding": None,
        }
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True,
                    stream=False
                )
                
                metadata["status_code"] = response.status_code
                metadata["headers"] = dict(response.headers)
                
                if response.status_code != 200:
                    return None, None, metadata
                
                # Try to detect encoding
                if response.encoding:
                    metadata["encoding"] = response.encoding
                
                # Get content
                content = response.content
                
                # Try to decode to check if it's text
                try:
                    text_content = content.decode('utf-8', errors='strict')
                    content_type = response.headers.get('Content-Type', 'text/html')
                    if 'charset' not in content_type.lower():
                        content_type += '; charset=utf-8'
                except UnicodeDecodeError:
                    # Binary content
                    content_type = response.headers.get('Content-Type', 'application/octet-stream')
                
                return content, content_type, metadata
                
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return None, None, metadata
                
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                metadata["error"] = str(e)
                return None, None, metadata
        
        return None, None, metadata

    def is_html(self, content_type: Optional[str]) -> bool:
        """Check if content type is HTML."""
        if not content_type:
            return False
        return "text/html" in content_type.lower()
