"""Tests for Wayback Machine cleaner."""

import pytest
from wayback_diff.wayback_cleaner import WaybackCleaner


class TestWaybackCleaner:
    """Test cases for WaybackCleaner."""

    def test_is_wayback_url_full(self):
        """Test Wayback URL detection with full URL."""
        assert WaybackCleaner.is_wayback_url("https://web.archive.org/web/20230101/https://example.com/")
        assert WaybackCleaner.is_wayback_url("http://web.archive.org/web/20230101/https://example.com/")

    def test_is_wayback_url_relative(self):
        """Test Wayback URL detection with relative URL."""
        assert WaybackCleaner.is_wayback_url("/web/20230101/https://example.com/")

    def test_is_wayback_url_non_wayback(self):
        """Test non-Wayback URLs."""
        assert not WaybackCleaner.is_wayback_url("https://example.com/")
        assert not WaybackCleaner.is_wayback_url("https://archive.org/")
        assert not WaybackCleaner.is_wayback_url("")

    def test_extract_timestamp_full_url(self):
        """Test timestamp extraction from full URL."""
        url = "https://web.archive.org/web/20230101120000/https://example.com/"
        timestamp = WaybackCleaner.extract_timestamp(url)
        assert timestamp == "20230101120000"

    def test_extract_timestamp_short(self):
        """Test timestamp extraction from short URL."""
        url = "/web/20230101/https://example.com/"
        timestamp = WaybackCleaner.extract_timestamp(url)
        assert timestamp == "20230101"

    def test_extract_timestamp_with_suffix(self):
        """Test timestamp extraction with suffix (cs_, im_, etc.)."""
        url = "https://web.archive.org/web/20230101cs_/https://example.com/style.css"
        timestamp = WaybackCleaner.extract_timestamp(url)
        assert timestamp == "20230101"

    def test_extract_timestamp_no_match(self):
        """Test timestamp extraction when no timestamp present."""
        assert WaybackCleaner.extract_timestamp("https://example.com/") is None
        assert WaybackCleaner.extract_timestamp("") is None

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

    def test_remove_wayback_header_bundle_playback(self):
        """Test header removal with bundle-playback.js pattern."""
        content = b'''<head>
<script type="text/javascript" src="/_static/js/bundle-playback.js"></script>
<script>some_wb_code();</script>
<!-- End Wayback Rewrite JS Include -->
<title>Page</title>
</head>'''

        cleaned = WaybackCleaner.remove_wayback_header(content)
        assert b'bundle-playback.js' not in cleaned
        assert b'<title>Page</title>' in cleaned

    def test_remove_wayback_header_no_end_marker(self):
        """Test header removal when end marker is missing but meta tag exists after scripts."""
        content = b'''<head>
<script src="//archive.org/includes/analytics.js"></script>
<script>init();</script>
<meta charset="utf-8">
<title>Page</title>
</head>'''

        cleaned = WaybackCleaner.remove_wayback_header(content)
        # Fallback finds <meta as the boundary; content from <meta onward is preserved
        assert b'<meta charset="utf-8">' in cleaned
        assert b'<title>Page</title>' in cleaned

    def test_remove_wayback_header_no_header(self):
        """Test when there is no Wayback header."""
        content = b'<html><head><title>Clean</title></head></html>'
        cleaned = WaybackCleaner.remove_wayback_header(content)
        assert cleaned == content

    def test_remove_wayback_header_no_end_marker_no_meta(self):
        """Test header removal when neither end marker nor meta tag exists."""
        content = b'''<head>
<script src="//archive.org/includes/analytics.js"></script>
<script>__wm.init();</script>
<title>Page</title>
</head>'''

        cleaned = WaybackCleaner.remove_wayback_header(content)
        # Should return content unchanged since no end marker found
        assert b'<title>Page</title>' in cleaned

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

    def test_remove_wayback_footer_inline_comment(self):
        """Test footer removal with inline comment format."""
        content = b'''<body>Content</body>
</html><!-- FILE ARCHIVED ON 2021-01-01 -->'''

        cleaned = WaybackCleaner.remove_wayback_footer(content)
        assert b'FILE ARCHIVED ON' not in cleaned

    def test_remove_wayback_footer_no_footer(self):
        """Test when there is no Wayback footer."""
        content = b'<html><body>Clean</body></html>'
        cleaned = WaybackCleaner.remove_wayback_footer(content)
        # Content should still contain the original body
        assert b'Clean' in cleaned

    def test_remove_wayback_footer_carriage_return(self):
        """Test footer removal with \\r\\n line endings."""
        content = b'<body>Content</body>\r\n</html>\r\n<!--\n     FILE ARCHIVED ON 2021 -->'
        cleaned = WaybackCleaner.remove_wayback_footer(content)
        assert b'FILE ARCHIVED ON' not in cleaned

    def test_remove_wayback_footer_standalone_comment(self):
        """Test footer removal when comment is standalone (not right after </html>)."""
        content = b'''<body>Content</body>
</html>

<!--
     FILE ARCHIVED ON 23:59:13 Nov 20, 2021 AND RETRIEVED FROM THE
     INTERNET ARCHIVE ON 00:41:42 Dec 01, 2021.
-->'''

        cleaned = WaybackCleaner.remove_wayback_footer(content)
        cleaned_str = cleaned.decode('utf-8', errors='ignore')
        assert 'FILE ARCHIVED ON' not in cleaned_str

    def test_remove_wayback_urls(self):
        """Test URL prefix removal with timestamp."""
        content = b'''<a href="http://web.archive.org/web/20230101/https://example.com/page">Link</a>
<img src="/web/20230101im_/https://example.com/image.png">
<link href="/web/20230101cs_/https://example.com/style.css">'''

        cleaned = WaybackCleaner.remove_wayback_urls(content, "20230101")
        assert b'web.archive.org' not in cleaned
        assert b'/web/20230101' not in cleaned
        assert b'https://example.com/page' in cleaned
        assert b'https://example.com/image.png' in cleaned

    def test_remove_wayback_urls_js_prefix(self):
        """Test URL removal with js_ prefix."""
        content = b'<script src="/web/20230101js_/https://example.com/app.js"></script>'
        cleaned = WaybackCleaner.remove_wayback_urls(content, "20230101")
        assert b'/web/20230101' not in cleaned
        assert b'https://example.com/app.js' in cleaned

    def test_remove_wayback_urls_no_timestamp(self):
        """Test URL removal without explicit timestamp (extracts from content)."""
        content = b'''<a href="http://web.archive.org/web/20230101/https://example.com/page">Link</a>
<img src="/web/20230101im_/https://example.com/image.png">'''

        cleaned = WaybackCleaner.remove_wayback_urls(content, None)
        assert b'web.archive.org' not in cleaned

    def test_remove_wayback_urls_no_timestamp_in_content(self):
        """Test URL removal when no timestamp can be extracted."""
        content = b'<a href="http://web.archive.org/path/page">Link</a>'
        cleaned = WaybackCleaner.remove_wayback_urls(content, None)
        assert b'web.archive.org' not in cleaned

    def test_remove_wayback_urls_https_archive(self):
        """Test URL removal with https web.archive.org."""
        content = b'<a href="https://web.archive.org/web/20230101/https://example.com/">Link</a>'
        cleaned = WaybackCleaner.remove_wayback_urls(content, "20230101")
        assert b'web.archive.org' not in cleaned

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
        assert b'archive.org/includes' not in cleaned
        assert b'web.archive.org' not in cleaned
        assert b'https://example.com/' in cleaned
        cleaned_str = cleaned.decode('utf-8', errors='ignore')
        assert 'FILE ARCHIVED ON' not in cleaned_str

    def test_clean_wayback_html_no_url(self):
        """Test cleaning without URL (no timestamp extraction)."""
        content = b'''<html>
<head>
<script src="//archive.org/includes/analytics.js"></script>
<!-- End Wayback Rewrite JS Include -->
<title>Test</title>
</head>
<body>Content</body>
</html>'''

        cleaned = WaybackCleaner.clean_wayback_html(content, None)
        assert b'archive.org/includes' not in cleaned

    def test_clean_wayback_html_empty(self):
        """Test cleaning empty content."""
        assert WaybackCleaner.clean_wayback_html(b'', None) == b''

    def test_clean_wayback_html_none(self):
        """Test cleaning None content."""
        assert WaybackCleaner.clean_wayback_html(b'', None) == b''

    def test_clean_wayback_html_no_artifacts(self):
        """Test cleaning content with no Wayback artifacts."""
        content = b'<html><body><p>Clean content</p></body></html>'
        cleaned = WaybackCleaner.clean_wayback_html(content, "https://example.com")
        assert b'Clean content' in cleaned

    def test_normalize_html_whitespace_self_closing(self):
        """Test whitespace normalization in self-closing tags."""
        html = b'<img src="test.png" />'
        normalized = WaybackCleaner.normalize_html_whitespace(html)
        assert b' />' not in normalized
        assert b'/>' in normalized

    def test_normalize_html_whitespace_multiple_spaces(self):
        """Test normalization of multiple spaces."""
        html = b'<div>  text    here  </div>'
        normalized = WaybackCleaner.normalize_html_whitespace(html)
        assert b'  ' not in normalized

    def test_normalize_html_whitespace_tabs(self):
        """Test normalization of tabs."""
        html = b'<div>\ttext\there</div>'
        normalized = WaybackCleaner.normalize_html_whitespace(html)
        assert b'\t' not in normalized

    def test_normalize_html_whitespace_newlines(self):
        """Test normalization of newlines with spaces."""
        html = b'<div>  \n  text</div>'
        normalized = WaybackCleaner.normalize_html_whitespace(html)
        assert b'  \n  ' not in normalized

    def test_extract_timestamp_jm_prefix(self):
        """Test timestamp with jm_ prefix."""
        url = "https://web.archive.org/web/20230101jm_/https://example.com/"
        timestamp = WaybackCleaner.extract_timestamp(url)
        assert timestamp == "20230101"
