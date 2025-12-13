"""Tests for web fetcher."""

import pytest
from unittest.mock import Mock, patch
from website_diff.fetcher import WebFetcher


class TestWebFetcher:
    """Test cases for WebFetcher."""
    
    def test_is_html(self):
        """Test HTML content type detection."""
        fetcher = WebFetcher()
        assert fetcher.is_html("text/html")
        assert fetcher.is_html("text/html; charset=utf-8")
        assert not fetcher.is_html("application/json")
        assert not fetcher.is_html(None)
    
    @patch('website_diff.fetcher.requests.Session.get')
    def test_fetch_success(self, mock_get):
        """Test successful fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html><body>Test</body></html>'
        mock_response.headers = {'Content-Type': 'text/html; charset=utf-8'}
        mock_response.encoding = 'utf-8'
        mock_get.return_value = mock_response
        
        fetcher = WebFetcher()
        content, content_type, metadata = fetcher.fetch("https://example.com")
        
        assert content == b'<html><body>Test</body></html>'
        assert content_type == 'text/html; charset=utf-8'
        assert metadata['status_code'] == 200
    
    @patch('website_diff.fetcher.requests.Session.get')
    def test_fetch_404(self, mock_get):
        """Test 404 response."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        fetcher = WebFetcher()
        content, content_type, metadata = fetcher.fetch("https://example.com/notfound")
        
        assert content is None
        assert metadata['status_code'] == 404
    
    def test_url_normalization(self):
        """Test URL normalization."""
        fetcher = WebFetcher()
        
        # Test adding https://
        content, _, _ = fetcher.fetch("example.com")
        # Should not raise an error (will fail in actual request, but URL is normalized)
