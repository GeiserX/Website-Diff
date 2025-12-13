"""Tests for Wayback Machine cleaner."""

import pytest
from website_diff.wayback_cleaner import WaybackCleaner


class TestWaybackCleaner:
    """Test cases for WaybackCleaner."""
    
    def test_is_wayback_url(self):
        """Test Wayback URL detection."""
        assert WaybackCleaner.is_wayback_url("https://web.archive.org/web/20230101/https://example.com/")
        assert WaybackCleaner.is_wayback_url("/web/20230101/https://example.com/")
        assert not WaybackCleaner.is_wayback_url("https://example.com/")
    
    def test_extract_timestamp(self):
        """Test timestamp extraction."""
        url = "https://web.archive.org/web/20230101120000/https://example.com/"
        timestamp = WaybackCleaner.extract_timestamp(url)
        assert timestamp == "20230101120000"
        
        url2 = "/web/20230101/https://example.com/"
        timestamp2 = WaybackCleaner.extract_timestamp(url2)
        assert timestamp2 == "20230101"
    
    def test_remove_wayback_header(self):
        """Test header removal."""
        content = b'''<!DOCTYPE html>
<html>
<head>
<script src="//archive.org/includes/analytics.js"></script>
<script>__wm.init();</script>
<!-- End Wayback Rewrite JS Include -->
<meta charset="utf-8">
<title>Test</title>
</head>
<body>Content</body>
</html>'''
        
        cleaned = WaybackCleaner.remove_wayback_header(content)
        assert b'archive.org/includes/analytics.js' not in cleaned
        assert b'__wm.init' not in cleaned
        assert b'<meta charset="utf-8">' in cleaned
        assert b'Content' in cleaned
    
    def test_remove_wayback_footer(self):
        """Test footer removal."""
        content = b'''<body>Content</body>
</html>
<!--
     FILE ARCHIVED ON 23:59:13 Nov 20, 2021 AND RETRIEVED FROM THE
     INTERNET ARCHIVE ON 00:41:42 Dec 01, 2021.
-->'''
        
        cleaned = WaybackCleaner.remove_wayback_footer(content)
        assert b'FILE ARCHIVED ON' not in cleaned
        assert cleaned.endswith(b'</html>\n')
    
    def test_remove_wayback_urls(self):
        """Test URL prefix removal."""
        content = b'''<a href="http://web.archive.org/web/20230101/https://example.com/page">Link</a>
<img src="/web/20230101im_/https://example.com/image.png">
<link href="/web/20230101cs_/https://example.com/style.css">'''
        
        cleaned = WaybackCleaner.remove_wayback_urls(content, "20230101")
        assert b'web.archive.org' not in cleaned
        assert b'/web/20230101' not in cleaned
        assert b'https://example.com/page' in cleaned
        assert b'https://example.com/image.png' in cleaned
    
    def test_clean_wayback_html(self):
        """Test complete cleaning."""
        content = b'''<!DOCTYPE html>
<html>
<head>
<script src="//archive.org/includes/analytics.js"></script>
<!-- End Wayback Rewrite JS Include -->
<title>Test</title>
</head>
<body>
<a href="http://web.archive.org/web/20230101/https://example.com/">Link</a>
</body>
</html>
<!-- FILE ARCHIVED ON -->'''
        
        cleaned = WaybackCleaner.clean_wayback_html(content, "https://web.archive.org/web/20230101/https://example.com/")
        # Check that wayback artifacts are removed
        assert b'archive.org' not in cleaned or b'archive.org/includes' not in cleaned
        assert b'web.archive.org' not in cleaned
        assert b'https://example.com/' in cleaned
        # The cleaner should remove the footer comment
        cleaned_str = cleaned.decode('utf-8', errors='ignore')
        assert 'FILE ARCHIVED ON' not in cleaned_str or cleaned_str.count('FILE ARCHIVED ON') == 0
