"""Module for traversing web pages and comparing all linked pages."""

import re
from typing import List, Dict, Set, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from wayback_diff.fetcher import WebFetcher
from wayback_diff.wayback_cleaner import WaybackCleaner
from wayback_diff.diff_engine import DiffEngine


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
        
        # Track visited URLs (normalized to avoid duplicates)
        self.visited: Set[str] = set()  # Track normalized URL pairs
        
        # Results
        self.results: List[Dict] = []
    
    def _normalize_url(self, url: str, base_url: str = None) -> str:
        """Normalize URL for comparison and deduplication."""
        # Handle relative URLs
        if not url.startswith(("http://", "https://")):
            if base_url:
                url = urljoin(base_url, url)
            else:
                return url  # Can't normalize without base
        
        # Remove fragments and normalize
        parsed = urlparse(url)
        
        # Normalize path (remove trailing slashes except for root)
        path = parsed.path.rstrip('/')
        if not path:
            path = '/'
        
        # Build normalized URL
        normalized = f"{parsed.scheme}://{parsed.netloc.lower()}{path}"
        
        # Sort query parameters for consistent comparison
        if parsed.query:
            params = sorted(parsed.query.split('&'))
            normalized += f"?{'&'.join(params)}"
        
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
                    
                    # Skip invalid URLs (emails, malformed)
                    if '@' in href and not href.startswith('mailto:'):
                        continue
                    if not href.startswith(('http://', 'https://')):
                        normalized = self._normalize_url(href, base_url)
                    else:
                        normalized = self._normalize_url(href)
                    
                    # Skip if normalization failed or resulted in invalid URL
                    if not normalized or not normalized.startswith(('http://', 'https://')):
                        continue
                    
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
        
        # Normalize URLs for deduplication
        normalized_url1 = self._normalize_url(url1)
        normalized_url2 = self._normalize_url(url2)
        visit_key = f"{normalized_url1}|||{normalized_url2}"
        
        # Queue for BFS traversal: (url1, url2, depth, normalized_key)
        queue: List[Tuple[str, str, int, str]] = [(url1, url2, 0, visit_key)]
        
        while queue and len(self.results) < self.max_pages:
            url1, url2, depth, visit_key = queue.pop(0)
            
            # Skip if already visited or too deep
            if visit_key in self.visited or depth > self.max_depth:
                if visit_key in self.visited:
                    print(f"Skipping already visited: {url1}")
                continue
            
            # Mark as visited
            self.visited.add(visit_key)
            
            print(f"Comparing (depth {depth}): {url1} <-> {url2}")
            
            # Compare pages
            result = self.compare_page(url1, url2)
            self.results.append(result)
            
            # Add links to queue if not too deep
            if depth < self.max_depth and result.get('status') == 'compared':
                links1 = result.get('links1', [])
                links_added = 0
                
                # Deduplicate links before processing
                seen_links = set()
                unique_links = []
                for link in links1:
                    # Normalize to check for duplicates
                    try:
                        if WaybackCleaner.is_wayback_url(link) or '/web/' in link:
                            # Extract original URL
                            match = re.search(r'/web/\d+[a-z]*/(https?://[^"\'<>)\s]+)', link)
                            if match:
                                link = match.group(1)
                        
                        normalized_check = self._normalize_url(link, url1)
                        if normalized_check and normalized_check not in seen_links:
                            seen_links.add(normalized_check)
                            unique_links.append(link)
                    except:
                        continue
                
                for link in unique_links:
                    if links_added >= 10:  # Limit links per page
                        break
                    
                    try:
                        # Normalize the link
                        normalized_link1 = self._normalize_url(link, url1)
                        if not normalized_link1 or not normalized_link1.startswith(('http://', 'https://')):
                            continue
                        
                        matching_link = self._get_matching_url(normalized_link1)
                        
                        if matching_link:
                            normalized_link2 = self._normalize_url(matching_link, url2)
                            if not normalized_link2:
                                continue
                            
                            link_visit_key = f"{normalized_link1}|||{normalized_link2}"
                            
                            # Only add if not already visited
                            if link_visit_key not in self.visited:
                                queue.append((normalized_link1, normalized_link2, depth + 1, link_visit_key))
                                links_added += 1
                            else:
                                if depth == 0:  # Only print for first level to reduce noise
                                    print(f"  Skipping duplicate link: {normalized_link1}")
                    except Exception as e:
                        if depth == 0:
                            print(f"  Error processing link {link}: {e}")
                        continue
        
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

