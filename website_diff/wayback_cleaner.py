"""Module for cleaning Wayback Machine artifacts from HTML content."""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse


class WaybackCleaner:
    """Cleans Wayback Machine artifacts from HTML content."""

    # Wayback Machine banner IDs and classes
    WAYBACK_BANNER_IDS = [
        "wm-ipp", "wm-bipp", "wm-toolbar", "wm-ipp-base",
        "wm-ipp-inside", "wm-ipp-base", "wm-ipp-print"
    ]

    # Wayback Machine script patterns
    WAYBACK_SCRIPT_PATTERNS = [
        r"archive\.org/includes/analytics\.js",
        r"bundle-playback\.js",
        r"wombat\.js",
        r"ruffle\.js",
        r"web-static\.archive\.org",
        r"__wm",
        r"archive_analytics",
    ]

    # Wayback Machine CSS patterns
    WAYBACK_CSS_PATTERNS = [
        r"banner-styles\.css",
        r"iconochive\.css",
        r"web-static\.archive\.org",
    ]

    @staticmethod
    def is_wayback_url(url: str) -> bool:
        """Check if URL is a Wayback Machine URL."""
        return "web.archive.org" in url or url.startswith("/web/")

    @staticmethod
    def extract_timestamp(url: str) -> Optional[str]:
        """Extract timestamp from Wayback Machine URL.
        
        Returns timestamp in format YYYYMMDDHHMMSS or None if not found.
        """
        # Pattern: /web/TIMESTAMP/ or /web/TIMESTAMPcs_/ etc.
        match = re.search(r'/web/(\d+[a-z]*)', url)
        if match:
            timestamp = match.group(1)
            # Extract numeric part
            numeric_match = re.match(r'(\d+)', timestamp)
            if numeric_match:
                return numeric_match.group(1)
        return None

    @staticmethod
    def remove_wayback_header(content: bytes) -> bytes:
        """Remove Wayback Machine header (scripts and CSS injected at the start).
        
        Removes everything from the first analytics script to the "End Wayback Rewrite JS Include" comment.
        """
        # Find the start of Wayback header
        start_patterns = [
            b'<script src="//archive.org/includes/analytics.js',
            b'<script src="/archive.org/includes/analytics.js',
            b'<script type="text/javascript" src="/_static/js/bundle-playback.js',
        ]
        
        start_idx = -1
        for pattern in start_patterns:
            idx = content.find(pattern)
            if idx >= 0:
                start_idx = idx
                break
        
        if start_idx < 0:
            return content
        
        # Find the end marker
        end_marker = b'<!-- End Wayback Rewrite JS Include -->'
        end_idx = content.find(end_marker, start_idx)
        
        if end_idx < 0:
            # Try alternative end markers
            end_marker = b'<!-- End Wayback Rewrite JS Include -->\n'
            end_idx = content.find(end_marker, start_idx)
            if end_idx < 0:
                # If we can't find the end, try to find the next <meta> or <title> tag
                # This is a fallback for pages where the comment might be missing
                next_tag = content.find(b'<meta', start_idx)
                if next_tag > start_idx:
                    end_idx = next_tag
                else:
                    return content
        
        # Remove the header section
        return content[:start_idx] + content[end_idx + len(end_marker):]

    @staticmethod
    def remove_wayback_footer(content: bytes) -> bytes:
        """Remove Wayback Machine footer (archival comments at the end)."""
        # Find the footer comment
        footer_patterns = [
            b'</html>\n<!--\n     FILE ARCHIVED ON ',
            b'</html>\r\n<!--\n     FILE ARCHIVED ON ',
            b'</html><!--\n     FILE ARCHIVED ON ',
        ]
        
        for pattern in footer_patterns:
            start_idx = content.rfind(pattern)
            if start_idx >= 0:
                # Find the end of the HTML tag
                html_end = content.rfind(b'</html>')
                if html_end >= 0:
                    return content[:html_end + len(b'</html>')] + b'\n'
        
        # Fallback: try to find just the comment
        comment_start = content.rfind(b'<!--\n     FILE ARCHIVED ON ')
        if comment_start >= 0:
            html_end = content.rfind(b'</html>', 0, comment_start)
            if html_end >= 0:
                return content[:html_end + len(b'</html>')] + b'\n'
        
        return content

    @staticmethod
    def remove_wayback_urls(content: bytes, timestamp: Optional[str] = None) -> bytes:
        """Remove Wayback Machine URL prefixes from links.
        
        Converts URLs like:
        - http://web.archive.org/web/TIMESTAMPcs_/https://example.com/style.css
        - /web/TIMESTAMP/https://example.com/page.html
        To:
        - https://example.com/style.css
        - https://example.com/page.html
        """
        if timestamp:
            timestamp_bytes = timestamp.encode('ascii')
        else:
            # Try to extract timestamp from content
            match = re.search(rb'/web/(\d+[a-z]*)', content)
            if match:
                timestamp_bytes = re.match(rb'(\d+)', match.group(1))
                if timestamp_bytes:
                    timestamp_bytes = timestamp_bytes.group(1)
                else:
                    timestamp_bytes = match.group(1)
            else:
                timestamp_bytes = None
        
        if not timestamp_bytes:
            # Still try to remove common patterns
            content = content.replace(b'http://web.archive.org', b'')
            content = content.replace(b'https://web.archive.org', b'')
            # Remove /web/TIMESTAMP/ patterns (try common prefixes)
            for prefix in [b'', b'im_', b'js_', b'cs_', b'jm_']:
                pattern = rb'/web/\d+[a-z]*' + prefix + rb'/'
                content = re.sub(pattern, b'', content)
            return content
        
        # Remove absolute Wayback URLs
        content = content.replace(b'http://web.archive.org', b'')
        content = content.replace(b'https://web.archive.org', b'')
        
        # Remove relative Wayback paths with timestamp
        for prefix in [b'', b'im_', b'js_', b'cs_', b'jm_']:
            pattern = b'/web/' + timestamp_bytes + prefix + b'/'
            content = content.replace(pattern, b'')
        
        # Also handle patterns without prefix separator
        pattern = b'/web/' + timestamp_bytes + b'/'
        content = content.replace(pattern, b'')
        
        return content

    @staticmethod
    def clean_wayback_html(html: bytes, url: Optional[str] = None) -> bytes:
        """Clean all Wayback Machine artifacts from HTML content.
        
        Args:
            html: The HTML content as bytes
            url: Optional URL to extract timestamp from
            
        Returns:
            Cleaned HTML content
        """
        if not html:
            return html
        
        # Extract timestamp if URL provided
        timestamp = None
        if url:
            timestamp = WaybackCleaner.extract_timestamp(url)
        
        # Remove header
        html = WaybackCleaner.remove_wayback_header(html)
        
        # Remove footer
        html = WaybackCleaner.remove_wayback_footer(html)
        
        # Remove URL prefixes
        html = WaybackCleaner.remove_wayback_urls(html, timestamp)
        
        return html

    @staticmethod
    def normalize_html_whitespace(html: bytes) -> bytes:
        """Normalize whitespace in HTML to make comparison easier.
        
        This removes trailing whitespace in tags and normalizes spacing,
        similar to what Wayback Machine does.
        """
        # Remove trailing space before /> in self-closing tags
        html = re.sub(rb' +/>', rb'/>', html)
        
        # Normalize multiple spaces to single space (but preserve in text content)
        # This is a simple approach - more sophisticated would require parsing
        html = re.sub(rb'[ \t]+', rb' ', html)
        html = re.sub(rb' *\n *', rb'\n', html)
        
        return html
