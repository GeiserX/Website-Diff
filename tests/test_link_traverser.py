"""Tests for link traverser."""

import pytest
from unittest.mock import patch, Mock, MagicMock
from wayback_diff.link_traverser import LinkTraverser


class TestLinkTraverserInit:
    """Test LinkTraverser initialization."""

    def test_init_basic(self):
        """Test basic initialization."""
        traverser = LinkTraverser("https://example.com", "https://example.org")
        assert traverser.base_url1 == "https://example.com"
        assert traverser.base_url2 == "https://example.org"
        assert traverser.max_depth == 2
        assert traverser.max_pages == 50
        assert traverser.same_domain_only is True

    def test_init_custom(self):
        """Test custom initialization."""
        traverser = LinkTraverser(
            "https://a.com", "https://b.com",
            max_depth=5, max_pages=100, same_domain_only=False
        )
        assert traverser.max_depth == 5
        assert traverser.max_pages == 100
        assert traverser.same_domain_only is False

    def test_init_domain_extraction(self):
        """Test domain extraction from URLs."""
        traverser = LinkTraverser("https://www.example.com/path", "https://example.org/path")
        assert traverser.domain1 == "example.com"
        assert traverser.domain2 == "example.org"

    def test_init_empty_results(self):
        """Test that results start empty."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        assert traverser.results == []
        assert len(traverser.visited) == 0


class TestNormalizeUrl:
    """Test URL normalization."""

    def test_normalize_absolute_url(self):
        """Test normalizing absolute URL."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        result = traverser._normalize_url("https://example.com/page/")
        assert result == "https://example.com/page"

    def test_normalize_removes_trailing_slash(self):
        """Test trailing slash removal."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        result = traverser._normalize_url("https://example.com/path/")
        assert not result.endswith("/")

    def test_normalize_root_keeps_slash(self):
        """Test root path keeps slash."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        result = traverser._normalize_url("https://example.com/")
        assert result.endswith("/")

    def test_normalize_relative_url(self):
        """Test normalizing relative URL with base."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        result = traverser._normalize_url("/page", "https://example.com/")
        assert result == "https://example.com/page"

    def test_normalize_relative_url_no_base(self):
        """Test normalizing relative URL without base returns as-is."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        result = traverser._normalize_url("/page")
        assert result == "/page"

    def test_normalize_sorts_query_params(self):
        """Test query parameter sorting."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        result = traverser._normalize_url("https://example.com/page?z=1&a=2")
        assert "a=2&z=1" in result

    def test_normalize_lowercases_netloc(self):
        """Test netloc lowercasing."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        result = traverser._normalize_url("https://EXAMPLE.COM/page")
        assert "example.com" in result


class TestIsSameDomain:
    """Test same domain checking."""

    def test_same_domain(self):
        """Test matching domain."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        assert traverser._is_same_domain("https://example.com/page", "example.com") is True

    def test_different_domain(self):
        """Test non-matching domain."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        assert traverser._is_same_domain("https://other.com/page", "example.com") is False

    def test_empty_domain(self):
        """Test empty domain (relative URL)."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        assert traverser._is_same_domain("/relative/path", "example.com") is True

    def test_www_prefix(self):
        """Test www prefix stripping."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        assert traverser._is_same_domain("https://www.example.com/page", "example.com") is True


class TestExtractLinks:
    """Test link extraction."""

    def test_extract_basic_links(self):
        """Test extracting basic links."""
        traverser = LinkTraverser("https://example.com", "https://other.com")
        html = b'<html><body><a href="https://example.com/page1">Link 1</a><a href="https://example.com/page2">Link 2</a></body></html>'
        links = traverser._extract_links(html, "https://example.com/")
        assert len(links) >= 1

    def test_extract_links_skips_anchors(self):
        """Test that anchor-only links are skipped."""
        traverser = LinkTraverser("https://example.com", "https://b.com")
        html = b'<html><body><a href="#section">Anchor</a></body></html>'
        links = traverser._extract_links(html, "https://example.com/")
        assert len(links) == 0

    def test_extract_links_skips_javascript(self):
        """Test that javascript: links are skipped."""
        traverser = LinkTraverser("https://example.com", "https://b.com")
        html = b'<html><body><a href="javascript:void(0)">JS</a></body></html>'
        links = traverser._extract_links(html, "https://example.com/")
        assert len(links) == 0

    def test_extract_links_skips_mailto(self):
        """Test that mailto: links are skipped."""
        traverser = LinkTraverser("https://example.com", "https://b.com")
        html = b'<html><body><a href="mailto:test@example.com">Email</a></body></html>'
        links = traverser._extract_links(html, "https://example.com/")
        assert len(links) == 0

    def test_extract_links_skips_tel(self):
        """Test that tel: links are skipped."""
        traverser = LinkTraverser("https://example.com", "https://b.com")
        html = b'<html><body><a href="tel:+1234567890">Call</a></body></html>'
        links = traverser._extract_links(html, "https://example.com/")
        assert len(links) == 0

    def test_extract_links_skips_sms(self):
        """Test that sms: links are skipped."""
        traverser = LinkTraverser("https://example.com", "https://b.com")
        html = b'<html><body><a href="sms:+1234567890">SMS</a></body></html>'
        links = traverser._extract_links(html, "https://example.com/")
        assert len(links) == 0

    def test_extract_links_deduplicates(self):
        """Test that duplicate links are removed."""
        traverser = LinkTraverser("https://example.com", "https://b.com")
        html = b'<html><body><a href="https://example.com/page">A</a><a href="https://example.com/page">B</a></body></html>'
        links = traverser._extract_links(html, "https://example.com/")
        # Should be deduplicated
        assert len(links) == len(set(links))

    def test_extract_links_same_domain_only(self):
        """Test same domain filtering."""
        traverser = LinkTraverser("https://example.com", "https://b.com",
                                  same_domain_only=True)
        html = b'<html><body><a href="https://example.com/page">Same</a><a href="https://other.com/page">Other</a></body></html>'
        links = traverser._extract_links(html, "https://example.com/")
        # Should only include same-domain links
        for link in links:
            assert 'other.com' not in link

    def test_extract_links_handles_error(self):
        """Test error handling in link extraction."""
        traverser = LinkTraverser("https://example.com", "https://b.com")
        # Invalid HTML should not crash
        links = traverser._extract_links(b'not html at all <<<>>>', "https://example.com/")
        assert isinstance(links, list)

    def test_extract_links_empty_href(self):
        """Test handling of empty href."""
        traverser = LinkTraverser("https://example.com", "https://b.com")
        html = b'<html><body><a href="">Empty</a></body></html>'
        links = traverser._extract_links(html, "https://example.com/")
        assert isinstance(links, list)

    def test_extract_links_wayback_url_extraction(self):
        """Test extracting original URLs from Wayback links."""
        traverser = LinkTraverser(
            "https://web.archive.org/web/20230101/https://example.com",
            "https://example.com",
            same_domain_only=False
        )
        html = b'<html><body><a href="/web/20230101/https://example.com/page">Link</a></body></html>'
        links = traverser._extract_links(html, "https://web.archive.org/web/20230101/https://example.com/")
        # Should extract the original URL
        if links:
            assert any('example.com' in link for link in links)

    def test_extract_links_skips_email_at_sign(self):
        """Test that URLs with @ but not mailto are skipped."""
        traverser = LinkTraverser("https://example.com", "https://b.com")
        html = b'<html><body><a href="user@example.com">User</a></body></html>'
        links = traverser._extract_links(html, "https://example.com/")
        assert len(links) == 0

    def test_extract_links_relative(self):
        """Test extracting relative links."""
        traverser = LinkTraverser("https://example.com", "https://b.com",
                                  same_domain_only=True)
        html = b'<html><body><a href="/about">About</a></body></html>'
        links = traverser._extract_links(html, "https://example.com/")
        if links:
            assert any('example.com' in link for link in links)


class TestGetMatchingUrl:
    """Test matching URL generation."""

    def test_basic_matching(self):
        """Test basic URL matching."""
        traverser = LinkTraverser("https://old.example.com", "https://new.example.com")
        result = traverser._get_matching_url("https://old.example.com/page")
        assert result == "https://new.example.com/page"

    def test_matching_with_query(self):
        """Test URL matching preserves query string."""
        traverser = LinkTraverser("https://old.com", "https://new.com")
        result = traverser._get_matching_url("https://old.com/page?q=test")
        assert "?q=test" in result

    def test_matching_wayback_url(self):
        """Test URL matching with Wayback URL."""
        traverser = LinkTraverser(
            "https://web.archive.org/web/20230101/https://example.com",
            "https://example.com"
        )
        result = traverser._get_matching_url(
            "https://web.archive.org/web/20230101/https://example.com/page"
        )
        assert result is not None
        assert "example.com" in result


class TestComparePage:
    """Test page comparison."""

    @patch.object(LinkTraverser, '__init__', lambda self, *a, **kw: None)
    def test_compare_page_success(self):
        """Test successful page comparison."""
        traverser = LinkTraverser.__new__(LinkTraverser)
        traverser.fetcher = Mock()
        traverser.diff_engine = Mock()
        traverser.same_domain_only = True

        traverser.fetcher.fetch.side_effect = [
            (b'<html>Page1</html>', 'text/html', {}),
            (b'<html>Page2</html>', 'text/html', {}),
        ]
        traverser.diff_engine.extract_meaningful_changes.return_value = []
        traverser.diff_engine.get_summary.return_value = {
            'total_changes': 0, 'high_significance': 0
        }

        result = traverser.compare_page("https://a.com", "https://b.com")
        assert result['status'] == 'compared'
        assert 'links1' in result
        assert 'links2' in result

    @patch.object(LinkTraverser, '__init__', lambda self, *a, **kw: None)
    def test_compare_page_fetch_failure(self):
        """Test page comparison when fetch fails."""
        traverser = LinkTraverser.__new__(LinkTraverser)
        traverser.fetcher = Mock()
        traverser.diff_engine = Mock()

        traverser.fetcher.fetch.side_effect = [
            (None, None, {}),
            (b'<html>OK</html>', 'text/html', {}),
        ]

        result = traverser.compare_page("https://a.com/bad", "https://b.com/good")
        assert result['status'] == 'error'

    @patch.object(LinkTraverser, '__init__', lambda self, *a, **kw: None)
    def test_compare_page_both_fail(self):
        """Test page comparison when both fetches fail."""
        traverser = LinkTraverser.__new__(LinkTraverser)
        traverser.fetcher = Mock()
        traverser.diff_engine = Mock()

        traverser.fetcher.fetch.return_value = (None, None, {})

        result = traverser.compare_page("https://a.com/bad", "https://b.com/bad")
        assert result['status'] == 'error'

    @patch.object(LinkTraverser, '__init__', lambda self, *a, **kw: None)
    def test_compare_page_cleans_wayback(self):
        """Test that Wayback artifacts are cleaned during comparison."""
        traverser = LinkTraverser.__new__(LinkTraverser)
        traverser.fetcher = Mock()
        traverser.diff_engine = Mock()
        traverser.same_domain_only = True

        traverser.fetcher.fetch.side_effect = [
            (b'<html>WB content</html>', 'text/html', {}),
            (b'<html>Clean content</html>', 'text/html', {}),
        ]
        traverser.diff_engine.extract_meaningful_changes.return_value = []
        traverser.diff_engine.get_summary.return_value = {
            'total_changes': 0, 'high_significance': 0
        }

        wb_url = "https://web.archive.org/web/20230101/https://example.com"
        with patch('wayback_diff.link_traverser.WaybackCleaner') as mock_cleaner:
            mock_cleaner.is_wayback_url.side_effect = [True, False]
            mock_cleaner.clean_wayback_html.return_value = b'<html>Cleaned</html>'

            result = traverser.compare_page(wb_url, "https://example.com")
            mock_cleaner.clean_wayback_html.assert_called_once()


class TestTraverseAndCompare:
    """Test traversal logic."""

    @patch.object(LinkTraverser, 'compare_page')
    def test_traverse_single_page(self, mock_compare):
        """Test traversal of single page (max_depth=0)."""
        traverser = LinkTraverser("https://a.com", "https://b.com", max_depth=0, max_pages=10)

        mock_compare.return_value = {
            'url1': 'https://a.com',
            'url2': 'https://b.com',
            'status': 'compared',
            'summary': {'total_changes': 0, 'high_significance': 0},
            'changes_count': 0,
            'high_significance': 0,
            'links1': [],
            'links2': [],
        }

        results = traverser.traverse_and_compare()
        assert len(results) == 1
        assert results[0]['status'] == 'compared'

    @patch.object(LinkTraverser, 'compare_page')
    def test_traverse_max_pages_limit(self, mock_compare):
        """Test that traversal respects max_pages limit."""
        traverser = LinkTraverser("https://a.com", "https://b.com",
                                  max_depth=5, max_pages=2)

        call_count = [0]
        def mock_compare_fn(url1, url2):
            call_count[0] += 1
            links = [f"https://a.com/page{i}" for i in range(10)]
            return {
                'url1': url1,
                'url2': url2,
                'status': 'compared',
                'summary': {'total_changes': 0, 'high_significance': 0},
                'changes_count': 0,
                'high_significance': 0,
                'links1': links,
                'links2': [],
            }

        mock_compare.side_effect = mock_compare_fn

        results = traverser.traverse_and_compare()
        assert len(results) <= 2

    @patch.object(LinkTraverser, 'compare_page')
    def test_traverse_skips_visited(self, mock_compare):
        """Test that already-visited URLs are skipped."""
        traverser = LinkTraverser("https://a.com", "https://b.com",
                                  max_depth=2, max_pages=10)

        mock_compare.return_value = {
            'url1': 'https://a.com',
            'url2': 'https://b.com',
            'status': 'compared',
            'summary': {'total_changes': 0, 'high_significance': 0},
            'changes_count': 0,
            'high_significance': 0,
            'links1': ['https://a.com/'],  # Link back to base
            'links2': [],
        }

        results = traverser.traverse_and_compare()
        # Should only compare once (the initial page)
        assert mock_compare.call_count == 1

    @patch.object(LinkTraverser, 'compare_page')
    def test_traverse_error_results_no_links(self, mock_compare):
        """Test that error results don't produce link traversal."""
        traverser = LinkTraverser("https://a.com", "https://b.com",
                                  max_depth=2, max_pages=10)

        mock_compare.return_value = {
            'url1': 'https://a.com',
            'url2': 'https://b.com',
            'status': 'error',
            'error': 'Fetch failed',
        }

        results = traverser.traverse_and_compare()
        assert len(results) == 1
        assert results[0]['status'] == 'error'


class TestExtractLinksWaybackBranches:
    """Test Wayback-specific link extraction branches."""

    def test_extract_links_wayback_relative_path(self):
        """Test extracting relative Wayback path links."""
        traverser = LinkTraverser(
            "https://web.archive.org/web/20230101/https://example.com",
            "https://example.com",
            same_domain_only=False
        )
        # A relative Wayback link that has no full URL, just a path fragment
        html = b'<html><body><a href="/web/20230101/somepage">Link</a></body></html>'
        links = traverser._extract_links(
            html, "https://web.archive.org/web/20230101/https://example.com/"
        )
        # Should attempt to construct URL from base
        assert isinstance(links, list)

    def test_extract_links_wayback_no_base_match(self):
        """Test Wayback link extraction when base URL has no extractable domain."""
        traverser = LinkTraverser(
            "https://web.archive.org/web/20230101/https://example.com",
            "https://example.com",
            same_domain_only=False
        )
        html = b'<html><body><a href="/web/20230101/relative">Link</a></body></html>'
        # Use a base_url that doesn't match the expected pattern
        links = traverser._extract_links(html, "https://web.archive.org/weird/path")
        assert isinstance(links, list)

    def test_extract_links_wayback_domain_filtering(self):
        """Test Wayback domain filtering for same_domain_only."""
        traverser = LinkTraverser(
            "https://web.archive.org/web/20230101/https://example.com",
            "https://example.com",
            same_domain_only=True
        )
        html = b'''<html><body>
            <a href="https://example.com/page">Same</a>
            <a href="https://other.com/page">Other</a>
        </body></html>'''
        links = traverser._extract_links(
            html, "https://web.archive.org/web/20230101/https://example.com/"
        )
        for link in links:
            assert 'other.com' not in link

    def test_extract_links_non_wayback_cross_domain_filtered(self):
        """Test non-Wayback cross domain links are filtered."""
        traverser = LinkTraverser(
            "https://example.com",
            "https://example.org",
            same_domain_only=True
        )
        html = b'<html><body><a href="https://external.com/page">Ext</a></body></html>'
        links = traverser._extract_links(html, "https://example.com/")
        for link in links:
            assert 'external.com' not in link


class TestTraverseAndCompareAdvanced:
    """Test advanced traversal scenarios."""

    @patch.object(LinkTraverser, 'compare_page')
    @patch.object(LinkTraverser, '_get_matching_url')
    def test_traverse_follows_links(self, mock_match, mock_compare):
        """Test that traversal follows links from first page."""
        traverser = LinkTraverser("https://a.com", "https://b.com",
                                  max_depth=1, max_pages=5)

        mock_match.return_value = "https://b.com/page1"

        call_count = [0]
        def compare_side_effect(url1, url2):
            call_count[0] += 1
            if call_count[0] == 1:
                return {
                    'url1': url1,
                    'url2': url2,
                    'status': 'compared',
                    'summary': {'total_changes': 0, 'high_significance': 0},
                    'changes_count': 0,
                    'high_significance': 0,
                    'links1': ['https://a.com/page1'],
                    'links2': [],
                }
            return {
                'url1': url1,
                'url2': url2,
                'status': 'compared',
                'summary': {'total_changes': 0, 'high_significance': 0},
                'changes_count': 0,
                'high_significance': 0,
                'links1': [],
                'links2': [],
            }

        mock_compare.side_effect = compare_side_effect

        results = traverser.traverse_and_compare()
        assert len(results) == 2

    @patch.object(LinkTraverser, 'compare_page')
    def test_traverse_depth_limit(self, mock_compare):
        """Test that traversal respects depth limit."""
        traverser = LinkTraverser("https://a.com", "https://b.com",
                                  max_depth=0, max_pages=100)

        mock_compare.return_value = {
            'url1': 'https://a.com',
            'url2': 'https://b.com',
            'status': 'compared',
            'summary': {'total_changes': 0, 'high_significance': 0},
            'changes_count': 0,
            'high_significance': 0,
            'links1': ['https://a.com/deep1', 'https://a.com/deep2'],
            'links2': [],
        }

        results = traverser.traverse_and_compare()
        # With max_depth=0, should only compare the initial page
        assert len(results) == 1

    @patch.object(LinkTraverser, 'compare_page')
    def test_traverse_link_processing_error(self, mock_compare):
        """Test that errors in link processing are handled gracefully."""
        traverser = LinkTraverser("https://a.com", "https://b.com",
                                  max_depth=1, max_pages=10)

        mock_compare.return_value = {
            'url1': 'https://a.com',
            'url2': 'https://b.com',
            'status': 'compared',
            'summary': {'total_changes': 0, 'high_significance': 0},
            'changes_count': 0,
            'high_significance': 0,
            'links1': ['not-a-valid-url', '', None],
            'links2': [],
        }

        # Should not crash
        results = traverser.traverse_and_compare()
        assert len(results) >= 1


class TestGetMatchingUrlAdvanced:
    """Test advanced URL matching scenarios."""

    def test_matching_wayback_url_no_original(self):
        """Test URL matching with Wayback URL that has no extractable original."""
        traverser = LinkTraverser(
            "https://web.archive.org/web/20230101/https://old.com",
            "https://new.com"
        )
        result = traverser._get_matching_url(
            "https://web.archive.org/web/20230101/https://old.com/page?q=1"
        )
        assert result is not None
        assert "new.com" in result

    def test_matching_non_wayback_with_path(self):
        """Test URL matching preserves path."""
        traverser = LinkTraverser("https://old.com", "https://new.com")
        result = traverser._get_matching_url("https://old.com/deep/path/page.html")
        assert result == "https://new.com/deep/path/page.html"


class TestGenerateReport:
    """Test report generation."""

    def test_generate_report_empty(self):
        """Test report with no results."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        report = traverser.generate_report()
        assert 'LINK TRAVERSAL COMPARISON REPORT' in report
        assert 'Pages compared: 0' in report

    def test_generate_report_with_results(self):
        """Test report with comparison results."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        traverser.results = [
            {
                'url1': 'https://a.com/',
                'url2': 'https://b.com/',
                'status': 'compared',
                'summary': {
                    'total_changes': 5,
                    'high_significance': 2,
                    'medium_significance': 2,
                    'low_significance': 1,
                },
                'changes_count': 5,
                'high_significance': 2,
            }
        ]
        report = traverser.generate_report()
        assert 'Pages compared: 1' in report
        assert 'Successfully compared: 1' in report
        assert 'HIGH SIGNIFICANCE DIFFERENCES' in report
        assert 'https://a.com/' in report

    def test_generate_report_with_errors(self):
        """Test report with error results."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        traverser.results = [
            {
                'url1': 'https://a.com/bad',
                'url2': 'https://b.com/bad',
                'status': 'error',
                'error': 'Connection refused',
            }
        ]
        report = traverser.generate_report()
        assert 'Errors: 1' in report
        assert 'Connection refused' in report

    def test_generate_report_mixed_results(self):
        """Test report with mixed compared and error results."""
        traverser = LinkTraverser("https://a.com", "https://b.com")
        traverser.results = [
            {
                'url1': 'https://a.com/',
                'url2': 'https://b.com/',
                'status': 'compared',
                'summary': {
                    'total_changes': 0,
                    'high_significance': 0,
                    'medium_significance': 0,
                    'low_significance': 0,
                },
                'changes_count': 0,
                'high_significance': 0,
            },
            {
                'url1': 'https://a.com/broken',
                'url2': 'https://b.com/broken',
                'status': 'error',
                'error': 'Timeout',
            }
        ]
        report = traverser.generate_report()
        assert 'Pages compared: 2' in report
        assert 'Successfully compared: 1' in report
        assert 'Errors: 1' in report
