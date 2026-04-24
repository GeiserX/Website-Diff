"""Tests for web fetcher."""

import pytest
from unittest.mock import Mock, patch, PropertyMock
import requests
from wayback_diff.fetcher import WebFetcher


class TestWebFetcher:
    """Test cases for WebFetcher."""

    def test_init_defaults(self):
        """Test default initialization."""
        fetcher = WebFetcher()
        assert fetcher.timeout == 30
        assert fetcher.max_retries == 3

    def test_init_custom(self):
        """Test custom initialization."""
        fetcher = WebFetcher(timeout=10, max_retries=5)
        assert fetcher.timeout == 10
        assert fetcher.max_retries == 5

    def test_default_headers_set(self):
        """Test that default headers are set on session."""
        fetcher = WebFetcher()
        assert 'User-Agent' in fetcher.session.headers

    def test_is_html(self):
        """Test HTML content type detection."""
        fetcher = WebFetcher()
        assert fetcher.is_html("text/html") is True
        assert fetcher.is_html("text/html; charset=utf-8") is True
        assert fetcher.is_html("TEXT/HTML") is True
        assert fetcher.is_html("application/json") is False
        assert fetcher.is_html("application/xml") is False
        assert fetcher.is_html("image/png") is False
        assert fetcher.is_html(None) is False
        assert fetcher.is_html("") is False

    @patch('wayback_diff.fetcher.requests.Session.get')
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

    @patch('wayback_diff.fetcher.requests.Session.get')
    def test_fetch_success_adds_charset(self, mock_get):
        """Test that charset is added when missing from content type."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html>Test</html>'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.encoding = 'utf-8'
        mock_get.return_value = mock_response

        fetcher = WebFetcher()
        content, content_type, metadata = fetcher.fetch("https://example.com")

        assert 'charset=utf-8' in content_type

    @patch('wayback_diff.fetcher.requests.Session.get')
    def test_fetch_binary_content(self, mock_get):
        """Test fetching binary content that cannot decode as utf-8."""
        mock_response = Mock()
        mock_response.status_code = 200
        # Create content that fails strict utf-8 decode
        mock_response.content = bytes([0xFF, 0xFE, 0x00, 0x01, 0x80, 0x81])
        mock_response.headers = {'Content-Type': 'application/octet-stream'}
        mock_response.encoding = None
        mock_get.return_value = mock_response

        fetcher = WebFetcher()
        content, content_type, metadata = fetcher.fetch("https://example.com/file.bin")

        assert content is not None
        assert 'application/octet-stream' in content_type

    @patch('wayback_diff.fetcher.requests.Session.get')
    def test_fetch_404(self, mock_get):
        """Test 404 response."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_get.return_value = mock_response

        fetcher = WebFetcher()
        content, content_type, metadata = fetcher.fetch("https://example.com/notfound")

        assert content is None
        assert metadata['status_code'] == 404

    @patch('wayback_diff.fetcher.requests.Session.get')
    def test_fetch_500(self, mock_get):
        """Test 500 response."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.headers = {'Server': 'nginx'}
        mock_get.return_value = mock_response

        fetcher = WebFetcher()
        content, content_type, metadata = fetcher.fetch("https://example.com/error")

        assert content is None
        assert metadata['status_code'] == 500

    @patch('wayback_diff.fetcher.requests.Session.get')
    def test_fetch_timeout_retries(self, mock_get):
        """Test timeout with retries."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        fetcher = WebFetcher(timeout=1, max_retries=2)
        content, content_type, metadata = fetcher.fetch("https://example.com")

        assert content is None
        assert mock_get.call_count == 2

    @patch('wayback_diff.fetcher.requests.Session.get')
    def test_fetch_request_exception_retries(self, mock_get):
        """Test request exception with retries."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        fetcher = WebFetcher(timeout=1, max_retries=3)
        content, content_type, metadata = fetcher.fetch("https://example.com")

        assert content is None
        assert mock_get.call_count == 3
        assert 'error' in metadata

    @patch('wayback_diff.fetcher.requests.Session.get')
    def test_fetch_timeout_then_success(self, mock_get):
        """Test timeout on first attempt then success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html>OK</html>'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.encoding = 'utf-8'

        mock_get.side_effect = [
            requests.exceptions.Timeout("timeout"),
            mock_response,
        ]

        fetcher = WebFetcher(timeout=1, max_retries=3)
        content, content_type, metadata = fetcher.fetch("https://example.com")

        assert content == b'<html>OK</html>'
        assert mock_get.call_count == 2

    def test_url_auto_https_prefix(self):
        """Test URL normalization adds https://."""
        fetcher = WebFetcher()
        # We can't fully test since it will try to make a real request,
        # but we can verify the URL validation logic via mocking.
        with patch.object(fetcher.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b'<html>OK</html>'
            mock_response.headers = {'Content-Type': 'text/html'}
            mock_response.encoding = 'utf-8'
            mock_get.return_value = mock_response

            fetcher.fetch("example.com")
            # Should have added https:// prefix
            call_url = mock_get.call_args[0][0]
            assert call_url.startswith("https://")

    @patch('wayback_diff.fetcher.requests.Session.get')
    def test_fetch_metadata_includes_headers(self, mock_get):
        """Test that metadata includes response headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html>OK</html>'
        mock_response.headers = {
            'Content-Type': 'text/html',
            'X-Custom': 'value'
        }
        mock_response.encoding = 'utf-8'
        mock_get.return_value = mock_response

        fetcher = WebFetcher()
        _, _, metadata = fetcher.fetch("https://example.com")

        assert metadata['headers']['X-Custom'] == 'value'

    @patch('wayback_diff.fetcher.requests.Session.get')
    def test_fetch_metadata_includes_encoding(self, mock_get):
        """Test that metadata includes encoding."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html>OK</html>'
        mock_response.headers = {'Content-Type': 'text/html; charset=iso-8859-1'}
        mock_response.encoding = 'iso-8859-1'
        mock_get.return_value = mock_response

        fetcher = WebFetcher()
        _, _, metadata = fetcher.fetch("https://example.com")

        assert metadata['encoding'] == 'iso-8859-1'

    @patch('wayback_diff.fetcher.requests.Session.get')
    def test_fetch_no_encoding(self, mock_get):
        """Test fetch when response has no encoding."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html>OK</html>'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.encoding = None
        mock_get.return_value = mock_response

        fetcher = WebFetcher()
        _, _, metadata = fetcher.fetch("https://example.com")

        assert metadata['encoding'] is None

    @patch('wayback_diff.fetcher.requests.Session.get')
    def test_fetch_private_ip_allowed(self, mock_get):
        """Test that private IP addresses pass through (logged but allowed)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html>OK</html>'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.encoding = 'utf-8'
        mock_get.return_value = mock_response

        fetcher = WebFetcher()
        content, _, _ = fetcher.fetch("https://192.168.1.1/page")
        assert content is not None

    @patch('wayback_diff.fetcher.requests.Session.get')
    def test_fetch_localhost_allowed(self, mock_get):
        """Test that localhost passes through."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<html>OK</html>'
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.encoding = 'utf-8'
        mock_get.return_value = mock_response

        fetcher = WebFetcher()
        content, _, _ = fetcher.fetch("https://localhost:8080/page")
        assert content is not None
