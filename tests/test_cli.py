"""Tests for CLI."""

import json
import pytest
import sys
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
import tempfile
import os

from wayback_diff.cli import format_output, main


class TestFormatOutput:
    """Test cases for format_output function."""

    def _make_summary(self, total=5, added=2, removed=1, modified=2,
                      high=1, medium=2, low=2):
        return {
            'total_changes': total,
            'added': added,
            'removed': removed,
            'modified': modified,
            'high_significance': high,
            'medium_significance': medium,
            'low_significance': low,
        }

    def _make_change(self, change_type='modified', old_text='Old', new_text='New',
                     significance='high'):
        return {
            'type': change_type,
            'old_text': old_text,
            'new_text': new_text,
            'significance': significance,
        }

    def test_format_output_text(self):
        """Test text output formatting."""
        summary = self._make_summary()
        changes = [self._make_change()]

        output = format_output(changes, summary, 'text')

        assert 'WAYBACK DIFF SUMMARY' in output
        assert 'Total changes: 5' in output
        assert 'Added: 2' in output
        assert 'Removed: 1' in output
        assert 'Modified: 2' in output
        assert 'High: 1' in output
        assert 'Medium: 2' in output
        assert 'Low: 2' in output
        assert 'HIGH SIGNIFICANCE CHANGES' in output

    def test_format_output_json(self):
        """Test JSON output formatting."""
        summary = self._make_summary(total=1, added=0, removed=0, modified=1,
                                     high=1, medium=0, low=0)
        changes = [self._make_change()]

        output = format_output(changes, summary, 'json')

        data = json.loads(output)
        assert 'summary' in data
        assert 'changes' in data
        assert data['summary']['total_changes'] == 1

    def test_format_output_unified_returns_empty(self):
        """Test unified format returns empty string."""
        summary = self._make_summary()
        changes = [self._make_change()]

        output = format_output(changes, summary, 'unified')
        assert output == ""

    def test_format_output_text_no_changes(self):
        """Test text output with no changes."""
        summary = self._make_summary(total=0, added=0, removed=0, modified=0,
                                     high=0, medium=0, low=0)
        output = format_output([], summary, 'text')
        assert 'Total changes: 0' in output
        assert 'HIGH SIGNIFICANCE CHANGES' not in output
        assert 'MEDIUM SIGNIFICANCE CHANGES' not in output

    def test_format_output_text_medium_changes(self):
        """Test text output with medium significance changes."""
        summary = self._make_summary(total=3, added=0, removed=0, modified=3,
                                     high=0, medium=3, low=0)
        changes = [self._make_change(significance='medium') for _ in range(3)]
        output = format_output(changes, summary, 'text')
        assert 'MEDIUM SIGNIFICANCE CHANGES' in output

    def test_format_output_text_more_than_10_medium(self):
        """Test text output with more than 10 medium changes (truncation)."""
        summary = self._make_summary(total=15, added=0, removed=0, modified=15,
                                     high=0, medium=15, low=0)
        changes = [self._make_change(significance='medium') for _ in range(15)]
        output = format_output(changes, summary, 'text')
        assert 'MEDIUM SIGNIFICANCE CHANGES' in output
        assert '... and 5 more medium significance changes' in output

    def test_format_output_text_more_than_20_high(self):
        """Test text output with more than 20 high changes (truncation)."""
        summary = self._make_summary(total=25, added=0, removed=0, modified=25,
                                     high=25, medium=0, low=0)
        changes = [self._make_change(significance='high') for _ in range(25)]
        output = format_output(changes, summary, 'text')
        assert 'HIGH SIGNIFICANCE CHANGES' in output
        assert '... and 5 more high significance changes' in output

    def test_format_output_text_low_changes_small_count(self):
        """Test text output with a small number of low significance changes."""
        summary = self._make_summary(total=3, added=0, removed=0, modified=3,
                                     high=0, medium=0, low=3)
        changes = [self._make_change(significance='low') for _ in range(3)]
        output = format_output(changes, summary, 'text')
        assert 'LOW SIGNIFICANCE CHANGES' in output
        assert '3 low significance changes' in output

    def test_format_output_text_low_changes_large_count(self):
        """Test text output with more than 50 low significance changes (hidden)."""
        summary = self._make_summary(total=55, added=0, removed=0, modified=55,
                                     high=0, medium=0, low=55)
        changes = [self._make_change(significance='low') for _ in range(55)]
        output = format_output(changes, summary, 'text')
        # Low changes > 50 are not shown
        assert 'LOW SIGNIFICANCE CHANGES' not in output

    def test_format_output_text_added_change(self):
        """Test text output with added change (no old_text)."""
        summary = self._make_summary(total=1, added=1, removed=0, modified=0,
                                     high=1, medium=0, low=0)
        changes = [self._make_change(change_type='added', old_text='', new_text='New Content')]
        output = format_output(changes, summary, 'text')
        assert 'NEW:' in output

    def test_format_output_text_removed_change(self):
        """Test text output with removed change (no new_text)."""
        summary = self._make_summary(total=1, added=0, removed=1, modified=0,
                                     high=1, medium=0, low=0)
        changes = [self._make_change(change_type='removed', old_text='Old Content', new_text='')]
        output = format_output(changes, summary, 'text')
        assert 'OLD:' in output

    def test_format_output_json_unicode(self):
        """Test JSON output with unicode characters."""
        summary = self._make_summary(total=1, added=0, removed=0, modified=1,
                                     high=1, medium=0, low=0)
        changes = [self._make_change(old_text='Texto viejo', new_text='Texto nuevo')]
        output = format_output(changes, summary, 'json')
        data = json.loads(output)
        assert 'viejo' in data['changes'][0]['old_text']


class TestMain:
    """Test cases for CLI main function."""

    @patch('wayback_diff.cli.WebFetcher')
    def test_main_basic_comparison(self, mock_fetcher_cls):
        """Test basic URL comparison flow."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        mock_fetcher.fetch.side_effect = [
            (b'<html><body><h1>Old</h1></body></html>', 'text/html', {'status_code': 200}),
            (b'<html><body><h1>New</h1></body></html>', 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        with patch('sys.argv', ['wayback-diff', 'https://example.com/old', 'https://example.com/new']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Should exit with 1 or 2 (changes detected)
            assert exc_info.value.code in (1, 2)

    @patch('wayback_diff.cli.WebFetcher')
    def test_main_identical_pages(self, mock_fetcher_cls):
        """Test comparison of identical pages exits with 0."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html><body><p>Same content</p></body></html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        with patch('sys.argv', ['wayback-diff', 'https://example.com/a', 'https://example.com/b']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch('wayback_diff.cli.WebFetcher')
    def test_main_fetch_failure_url1(self, mock_fetcher_cls):
        """Test exit code 1 when URL1 fetch fails."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        mock_fetcher.fetch.return_value = (None, None, {'error': 'Connection failed'})

        with patch('sys.argv', ['wayback-diff', 'https://example.com/bad', 'https://example.com/good']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch('wayback_diff.cli.WebFetcher')
    def test_main_fetch_failure_url2(self, mock_fetcher_cls):
        """Test exit code 1 when URL2 fetch fails."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        mock_fetcher.fetch.side_effect = [
            (b'<html>OK</html>', 'text/html', {'status_code': 200}),
            (None, None, {'error': 'Timeout'}),
        ]
        mock_fetcher.is_html.return_value = True

        with patch('sys.argv', ['wayback-diff', 'https://example.com/a', 'https://example.com/bad']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch('wayback_diff.cli.WebFetcher')
    def test_main_fetch_failure_url1_no_error_key(self, mock_fetcher_cls):
        """Test exit code 1 when URL1 fetch fails with no error key in metadata."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        mock_fetcher.fetch.return_value = (None, None, {})

        with patch('sys.argv', ['wayback-diff', 'https://example.com/bad', 'https://example.com/good']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch('wayback_diff.cli.WebFetcher')
    def test_main_json_format(self, mock_fetcher_cls):
        """Test --format json flag."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html><body><p>Same</p></body></html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com', '--format', 'json']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch('wayback_diff.cli.WebFetcher')
    def test_main_unified_format(self, mock_fetcher_cls):
        """Test --format unified flag."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        mock_fetcher.fetch.side_effect = [
            (b'<html>Old</html>', 'text/html', {'status_code': 200}),
            (b'<html>New</html>', 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com', '--format', 'unified']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # unified diff with changes exits non-zero
            assert exc_info.value.code in (1, 2)

    @patch('wayback_diff.cli.WebFetcher')
    def test_main_output_to_file(self, mock_fetcher_cls):
        """Test --output flag writes to file."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html><body>Same</body></html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        with tempfile.TemporaryDirectory() as tmpdir:
            outfile = os.path.join(tmpdir, 'output.txt')
            with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com', '-o', outfile]):
                with pytest.raises(SystemExit):
                    main()
            assert os.path.exists(outfile)

    @patch('wayback_diff.cli.WebFetcher')
    def test_main_verbose(self, mock_fetcher_cls):
        """Test --verbose flag."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html>Same</html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com', '--verbose']):
            with pytest.raises(SystemExit):
                main()

    @patch('wayback_diff.cli.WebFetcher')
    def test_main_non_html_warning(self, mock_fetcher_cls):
        """Test warning when content is not HTML."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'{"key": "value"}'
        mock_fetcher.fetch.side_effect = [
            (content, 'application/json', {'status_code': 200}),
            (content, 'application/json', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = False

        with patch('sys.argv', ['wayback-diff', 'https://a.com/api', 'https://b.com/api']):
            with pytest.raises(SystemExit):
                main()

    @patch('wayback_diff.cli.WaybackCleaner')
    @patch('wayback_diff.cli.WebFetcher')
    def test_main_wayback_url_cleaning(self, mock_fetcher_cls, mock_cleaner_cls):
        """Test Wayback URL auto-cleaning."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html>Content</html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True
        mock_cleaner_cls.is_wayback_url.side_effect = [True, False]
        mock_cleaner_cls.clean_wayback_html.return_value = content

        wb_url = 'https://web.archive.org/web/20230101/https://example.com/'
        with patch('sys.argv', ['wayback-diff', wb_url, 'https://example.com/', '--verbose']):
            with pytest.raises(SystemExit):
                main()
        mock_cleaner_cls.clean_wayback_html.assert_called_once()

    @patch('wayback_diff.cli.WaybackCleaner')
    @patch('wayback_diff.cli.WebFetcher')
    def test_main_no_clean_wayback_flag(self, mock_fetcher_cls, mock_cleaner_cls):
        """Test --no-clean-wayback flag skips cleaning."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html>Content</html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        wb_url = 'https://web.archive.org/web/20230101/https://example.com/'
        with patch('sys.argv', ['wayback-diff', wb_url, 'https://example.com/', '--no-clean-wayback']):
            with pytest.raises(SystemExit):
                main()
        mock_cleaner_cls.clean_wayback_html.assert_not_called()

    @patch('wayback_diff.cli.MarkdownReportGenerator')
    @patch('wayback_diff.cli.WebFetcher')
    def test_main_markdown_report(self, mock_fetcher_cls, mock_report_cls):
        """Test --markdown flag generates report."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html>Same</html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        mock_gen = Mock()
        mock_report_cls.return_value = mock_gen
        mock_gen.generate_comparison_report.return_value = "# Report"
        mock_gen.save_report.return_value = "/tmp/report.md"

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com',
                                    '--markdown', '--report-dir', tmpdir]):
                with pytest.raises(SystemExit):
                    main()
            mock_gen.generate_comparison_report.assert_called_once()
            mock_gen.save_report.assert_called_once()

    @patch('wayback_diff.cli.VISUAL_COMPARISON_AVAILABLE', False)
    @patch('wayback_diff.cli.WebFetcher')
    def test_main_visual_not_available(self, mock_fetcher_cls):
        """Test --visual flag when dependencies not available."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html>Content</html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com', '--visual']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch('wayback_diff.cli.VISUAL_COMPARISON_AVAILABLE', True)
    @patch('wayback_diff.cli.VisualComparison')
    @patch('wayback_diff.cli.MarkdownReportGenerator')
    @patch('wayback_diff.cli.WebFetcher')
    def test_main_visual_comparison_success(self, mock_fetcher_cls, mock_report_cls,
                                            mock_visual_cls):
        """Test --visual flag with successful comparison."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html>Same</html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        mock_visual = Mock()
        mock_visual_cls.return_value = mock_visual
        mock_visual.compare_urls.return_value = {
            'chrome': {
                'difference_ratio': 0.02,
                'different_pixels': 100,
                'screenshot1': '/tmp/s1.png',
                'screenshot2': '/tmp/s2.png',
                'comparison': '/tmp/comp.png',
            }
        }

        mock_gen = Mock()
        mock_report_cls.return_value = mock_gen
        mock_gen.generate_comparison_report.return_value = "# Report"
        mock_gen.save_report.return_value = "/tmp/report.md"

        with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com', '--visual']):
            with pytest.raises(SystemExit):
                main()

    @patch('wayback_diff.cli.VISUAL_COMPARISON_AVAILABLE', True)
    @patch('wayback_diff.cli.VisualComparison')
    @patch('wayback_diff.cli.MarkdownReportGenerator')
    @patch('wayback_diff.cli.WebFetcher')
    def test_main_visual_comparison_with_error_result(self, mock_fetcher_cls,
                                                       mock_report_cls, mock_visual_cls):
        """Test --visual flag when browser returns error."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html>Same</html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        mock_visual = Mock()
        mock_visual_cls.return_value = mock_visual
        mock_visual.compare_urls.return_value = {
            'chrome': {'error': 'No chrome found'}
        }

        mock_gen = Mock()
        mock_report_cls.return_value = mock_gen
        mock_gen.generate_comparison_report.return_value = "# Report"
        mock_gen.save_report.return_value = "/tmp/report.md"

        with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com', '--visual']):
            with pytest.raises(SystemExit):
                main()

    @patch('wayback_diff.cli.VISUAL_COMPARISON_AVAILABLE', True)
    @patch('wayback_diff.cli.VisualComparison')
    @patch('wayback_diff.cli.WebFetcher')
    def test_main_visual_comparison_exception(self, mock_fetcher_cls, mock_visual_cls):
        """Test --visual flag when visual comparison raises exception."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html>Same</html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        mock_visual_cls.side_effect = Exception("Browser crash")

        with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com',
                                '--visual', '--verbose']):
            with pytest.raises(SystemExit):
                main()

    @patch('wayback_diff.cli.VISUAL_COMPARISON_AVAILABLE', True)
    @patch('wayback_diff.cli.VisualComparison')
    @patch('wayback_diff.cli.WebFetcher')
    def test_main_visual_import_error(self, mock_fetcher_cls, mock_visual_cls):
        """Test --visual flag when ImportError occurs."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html>Same</html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        mock_visual_cls.side_effect = ImportError("No selenium")

        with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com', '--visual']):
            with pytest.raises(SystemExit):
                main()

    @patch('wayback_diff.cli.LinkTraverser')
    @patch('wayback_diff.cli.WebFetcher')
    def test_main_traverse_mode(self, mock_fetcher_cls, mock_traverser_cls):
        """Test --traverse flag."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html>Content</html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        mock_traverser = Mock()
        mock_traverser_cls.return_value = mock_traverser
        mock_traverser.traverse_and_compare.return_value = []
        mock_traverser.generate_report.return_value = "Traversal report"

        with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com', '--traverse']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch('wayback_diff.cli.LinkTraverser')
    @patch('wayback_diff.cli.WebFetcher')
    def test_main_traverse_with_high_diffs(self, mock_fetcher_cls, mock_traverser_cls):
        """Test --traverse with high significance differences exits with 2."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html>Content</html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        mock_traverser = Mock()
        mock_traverser_cls.return_value = mock_traverser
        mock_traverser.traverse_and_compare.return_value = [
            {'status': 'compared', 'high_significance': 5}
        ]
        mock_traverser.generate_report.return_value = "Report"

        with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com', '--traverse']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2

    @patch('wayback_diff.cli.LinkTraverser')
    @patch('wayback_diff.cli.WebFetcher')
    def test_main_traverse_compared_no_high(self, mock_fetcher_cls, mock_traverser_cls):
        """Test --traverse with compared pages but no high significance exits with 1."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html>Content</html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        mock_traverser = Mock()
        mock_traverser_cls.return_value = mock_traverser
        mock_traverser.traverse_and_compare.return_value = [
            {'status': 'compared', 'high_significance': 0}
        ]
        mock_traverser.generate_report.return_value = "Report"

        with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com', '--traverse']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch('wayback_diff.cli.MarkdownReportGenerator')
    @patch('wayback_diff.cli.LinkTraverser')
    @patch('wayback_diff.cli.WebFetcher')
    def test_main_traverse_with_markdown(self, mock_fetcher_cls, mock_traverser_cls,
                                         mock_report_cls):
        """Test --traverse --markdown generates report."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html>Content</html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        mock_traverser = Mock()
        mock_traverser_cls.return_value = mock_traverser
        mock_traverser.traverse_and_compare.return_value = []
        mock_traverser.generate_report.return_value = "Report"

        mock_gen = Mock()
        mock_report_cls.return_value = mock_gen
        mock_gen.generate_comparison_report.return_value = "# Report"
        mock_gen.save_report.return_value = "/tmp/report.md"

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com',
                                    '--traverse', '--markdown', '--report-dir', tmpdir]):
                with pytest.raises(SystemExit):
                    main()
            mock_gen.save_report.assert_called_once()

    @patch('wayback_diff.cli.LinkTraverser')
    @patch('wayback_diff.cli.WebFetcher')
    def test_main_traverse_output_to_file(self, mock_fetcher_cls, mock_traverser_cls):
        """Test --traverse -o flag writes report to file."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html>Content</html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        mock_traverser = Mock()
        mock_traverser_cls.return_value = mock_traverser
        mock_traverser.traverse_and_compare.return_value = []
        mock_traverser.generate_report.return_value = "Traversal report text"

        with tempfile.TemporaryDirectory() as tmpdir:
            outfile = os.path.join(tmpdir, 'out.txt')
            with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com',
                                    '--traverse', '-o', outfile, '--verbose']):
                with pytest.raises(SystemExit):
                    main()
            assert os.path.exists(outfile)
            with open(outfile) as f:
                assert 'Traversal report text' in f.read()

    @patch('wayback_diff.cli.DiffEngine')
    @patch('wayback_diff.cli.WebFetcher')
    def test_main_high_significance_exits_2(self, mock_fetcher_cls, mock_engine_cls):
        """Test exit code 2 for high significance changes."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        mock_fetcher.fetch.side_effect = [
            (b'<html>Old</html>', 'text/html', {'status_code': 200}),
            (b'<html>New</html>', 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        mock_engine = Mock()
        mock_engine_cls.return_value = mock_engine
        mock_engine.extract_meaningful_changes.return_value = [
            {'type': 'modified', 'significance': 'high', 'old_text': 'Old', 'new_text': 'New'}
        ]
        mock_engine.get_summary.return_value = {
            'total_changes': 1, 'added': 0, 'removed': 0, 'modified': 1,
            'high_significance': 1, 'medium_significance': 0, 'low_significance': 0,
        }

        with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2

    @patch('wayback_diff.cli.WebFetcher')
    def test_main_browsers_auto(self, mock_fetcher_cls):
        """Test --browsers auto flag parsing."""
        mock_fetcher = Mock()
        mock_fetcher_cls.return_value = mock_fetcher
        content = b'<html>Same</html>'
        mock_fetcher.fetch.side_effect = [
            (content, 'text/html', {'status_code': 200}),
            (content, 'text/html', {'status_code': 200}),
        ]
        mock_fetcher.is_html.return_value = True

        # Just verify parsing works (no --visual so browsers arg is stored but not used)
        with patch('sys.argv', ['wayback-diff', 'https://a.com', 'https://b.com',
                                '--browsers', 'chrome', 'firefox']):
            with pytest.raises(SystemExit):
                main()
