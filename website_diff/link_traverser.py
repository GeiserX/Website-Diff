"""Module for traversing web pages and comparing all linked pages."""

import re
from typing import List, Dict, Set, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from website_diff.fetcher import WebFetcher
from website_diff.wayback_cleaner import WaybackCleaner
from website_diff.diff_engine import DiffEngine


class LinkTraverser:
    """Traverse web pages and compare all linked pages."""
    
    def __init__(self, base_url1: str, base_url2: str, max_depth: int = 2, 
                 max_pages: int = 50, same_domain_only: bool = True):
        """Initialize link traverser.
        
        Args:
            base_url1: Base URL for first site
            base_url2: Base URL for second site
            max_depth: Maximum depth to traverse (default: 2)
            max_pages: Maximum number of pages to compare (default: 50)
            same_domain_only: Only traverse links within the same domain
        """
        self.base_url1 = base_url1
        self.base_url2 = base_url2
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.same_domain_only = same_domain_only
        
        self.fetcher = WebFetcher(timeout=30)
        self.diff_engine = DiffEngine(ignore_whitespace=True)
        
        # Extract domains
        parsed1 = urlparse(base_url1)
        parsed2 = urlparse(base_url2)
        self.domain1 = parsed1.netloc.lower().lstrip("www.")
        self.domain2 = parsed2.netloc.lower().lstrip("www.")
        
        # Track visited URLs
        self.visited1: Set[str] = set()
        self.visited2: Set[str] = set()
        
        # Results
        self.results: List[Dict] = []
    
    def _normalize_url(self, url: str, base_url: str) -> str:
        """Normalize URL for comparison."""
        # Handle relative URLs
        if not url.startswith(("http://", "https://")):
            url = urljoin(base_url, url)
        
        # Remove fragments
        parsed = urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        
        return normalized
    
    def _is_same_domain(self, url: str, base_domain: str) -> bool:
        """Check if URL is in the same domain."""
        parsed = urlparse(url)
        url_domain = parsed.netloc.lower().lstrip("www.")
        return url_domain == base_domain or url_domain == ""
    
    def _extract_links(self, html: bytes, base_url: str) -> List[str]:
        """Extract all links from HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            links = []
            
            # Extract from <a> tags
            for a_tag in soup.find_all('a', href=True):
                href = a_tag.get('href', '')
                if href:
                    # Skip anchors, javascript, mailto, tel
                    if href.startswith(('#', 'javascript:', 'mailto:', 'tel:', 'sms:')):
                        continue
                    
                    # Extract original URL from Wayback if needed
                    if WaybackCleaner.is_wayback_url(href) or '/web/' in href:
                        # Try to extract original URL from Wayback path
                        original = WaybackCleaner.extract_timestamp(href)
                        if original:
                            # Pattern: /web/TIMESTAMP/ORIGINAL_URL
                            match = re.search(r'/web/\d+[a-z]*/(https?://[^"\'<>)\s]+)', href)
                            if match:
                                href = match.group(1)
                            else:
                                # Try relative wayback path
                                match = re.search(r'/web/\d+[a-z]*/([^"\'<>)\s/]+)', href)
                                if match:
                                    # This is a relative path, construct full URL
                                    path_part = match.group(1)
                                    if base_url and WaybackCleaner.is_wayback_url(base_url):
                                        # Extract original domain from base_url
                                        base_match = re.search(r'/web/\d+[a-z]*/(https?://[^/]+)', base_url)
                                        if base_match:
                                            original_base = base_match.group(1)
                                            href = urljoin(original_base, path_part)
                                        else:
                                            continue
                                    else:
                                        continue
                                else:
                                    continue
                    
                    normalized = self._normalize_url(href, base_url)
                    
                    # For Wayback URLs, extract the original domain
                    if WaybackCleaner.is_wayback_url(base_url):
                        # Extract original domain from base_url
                        base_match = re.search(r'/web/\d+[a-z]*/(https?://[^/]+)', base_url)
                        if base_match:
                            original_domain = urlparse(base_match.group(1)).netloc.lower().lstrip("www.")
                            url_domain = urlparse(normalized).netloc.lower().lstrip("www.")
                            if self.same_domain_only and url_domain != original_domain and url_domain != "":
                                continue
                    elif self.same_domain_only:
                        base_domain = urlparse(base_url).netloc.lower().lstrip("www.")
                        if not self._is_same_domain(normalized, base_domain):
                            continue
                    
                    links.append(normalized)
            
            return list(set(links))  # Remove duplicates
            
        except Exception as e:
            print(f"Error extracting links: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_matching_url(self, url1: str) -> Optional[str]:
        """Get matching URL from second site."""
        # Extract original URL from Wayback if needed
        if WaybackCleaner.is_wayback_url(url1):
            timestamp = WaybackCleaner.extract_timestamp(url1)
            # Extract the original URL from Wayback path
            match = re.search(r'/web/\d+[a-z]*/(https?://[^/]+)', url1)
            if match:
                original_url = match.group(1)
                parsed_orig = urlparse(original_url)
                path1 = parsed_orig.path
            else:
                parsed1 = urlparse(url1)
                path1 = parsed1.path
        else:
            parsed1 = urlparse(url1)
            path1 = parsed1.path
        
        # Try to construct matching URL
        parsed2 = urlparse(self.base_url2)
        url2 = f"{parsed2.scheme}://{parsed2.netloc}{path1}"
        
        parsed1 = urlparse(url1)
        if parsed1.query:
            url2 += f"?{parsed1.query}"
        
        return url2
    
    def compare_page(self, url1: str, url2: str) -> Dict:
        """Compare a single page pair."""
        # Fetch content
        content1, ct1, meta1 = self.fetcher.fetch(url1)
        content2, ct2, meta2 = self.fetcher.fetch(url2)
        
        if not content1 or not content2:
            return {
                'url1': url1,
                'url2': url2,
                'status': 'error',
                'error': 'Failed to fetch one or both pages'
            }
        
        # Clean Wayback artifacts if needed
        if WaybackCleaner.is_wayback_url(url1):
            content1 = WaybackCleaner.clean_wayback_html(content1, url1)
        if WaybackCleaner.is_wayback_url(url2):
            content2 = WaybackCleaner.clean_wayback_html(content2, url2)
        
        # Compare
        changes = self.diff_engine.extract_meaningful_changes(content1, content2)
        summary = self.diff_engine.get_summary(changes)
        
        # Extract links for further traversal
        links1 = self._extract_links(content1, url1)
        links2 = self._extract_links(content2, url2)
        
        return {
            'url1': url1,
            'url2': url2,
            'status': 'compared',
            'summary': summary,
            'changes_count': len(changes),
            'high_significance': summary['high_significance'],
            'links1': links1,
            'links2': links2
        }
    
    def traverse_and_compare(self, start_path: str = "/") -> List[Dict]:
        """Traverse and compare all pages starting from a path.
        
        Args:
            start_path: Starting path (default: "/")
            
        Returns:
            List of comparison results
        """
        # Use base URLs directly for start
        url1 = self.base_url1
        url2 = self.base_url2
        
        # Queue for BFS traversal
        queue: List[Tuple[str, str, int]] = [(url1, url2, 0)]  # (url1, url2, depth)
        
        while queue and len(self.results) < self.max_pages:
            url1, url2, depth = queue.pop(0)
            
            # Skip if already visited or too deep
            if url1 in self.visited1 or depth > self.max_depth:
                continue
            
            self.visited1.add(url1)
            self.visited2.add(url2)
            
            print(f"Comparing (depth {depth}): {url1} <-> {url2}")
            
            # Compare pages
            result = self.compare_page(url1, url2)
            self.results.append(result)
            
            # Add links to queue if not too deep
            if depth < self.max_depth and result.get('status') == 'compared':
                links1 = result.get('links1', [])
                for link in links1[:10]:  # Limit links per page
                    if link not in self.visited1:
                        matching_link = self._get_matching_url(link)
                        if matching_link:
                            queue.append((link, matching_link, depth + 1))
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate a comparison report."""
        lines = []
        lines.append("=" * 80)
        lines.append("LINK TRAVERSAL COMPARISON REPORT")
        lines.append("=" * 80)
        lines.append(f"Base URL 1: {self.base_url1}")
        lines.append(f"Base URL 2: {self.base_url2}")
        lines.append(f"Pages compared: {len(self.results)}")
        lines.append("")
        
        # Group by status
        compared = [r for r in self.results if r.get('status') == 'compared']
        errors = [r for r in self.results if r.get('status') == 'error']
        
        lines.append(f"Successfully compared: {len(compared)}")
        lines.append(f"Errors: {len(errors)}")
        lines.append("")
        
        # High significance differences
        high_diff = [r for r in compared if r.get('high_significance', 0) > 0]
        if high_diff:
            lines.append("HIGH SIGNIFICANCE DIFFERENCES:")
            lines.append("-" * 80)
            for result in high_diff:
                lines.append(f"\n{result['url1']}")
                lines.append(f"  -> {result['url2']}")
                lines.append(f"  High significance changes: {result.get('high_significance', 0)}")
                lines.append(f"  Total changes: {result.get('changes_count', 0)}")
        
        # All results summary
        lines.append("")
        lines.append("=" * 80)
        lines.append("DETAILED RESULTS")
        lines.append("=" * 80)
        for i, result in enumerate(self.results, 1):
            lines.append(f"\n{i}. {result['url1']}")
            if result.get('status') == 'compared':
                summary = result.get('summary', {})
                lines.append(f"   Changes: {summary.get('total_changes', 0)}")
                lines.append(f"   High: {summary.get('high_significance', 0)}, "
                           f"Medium: {summary.get('medium_significance', 0)}, "
                           f"Low: {summary.get('low_significance', 0)}")
            else:
                lines.append(f"   Error: {result.get('error', 'Unknown error')}")
        
        return "\n".join(lines)
