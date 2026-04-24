"""Tests for markdown report generator."""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
from wayback_diff.report_generator import MarkdownReportGenerator


class TestMarkdownReportGeneratorInit:
    """Test report generator initialization."""

    def test_init_creates_directory(self):
        """Test that output directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "reports")
            gen = MarkdownReportGenerator(output_dir=output_dir)
            assert os.path.isdir(output_dir)

    def test_init_default_dir(self):
        """Test default output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                gen = MarkdownReportGenerator()
                assert gen.output_dir == Path("./reports")
            finally:
                os.chdir(old_cwd)
                # Clean up if created
                reports_dir = os.path.join(tmpdir, "reports")
                if os.path.exists(reports_dir):
                    shutil.rmtree(reports_dir)


class TestGenerateComparisonReport:
    """Test report generation."""

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

    def _make_change(self, change_type='modified', old_text='Old content',
                     new_text='New content', significance='high'):
        return {
            'type': change_type,
            'old_text': old_text,
            'new_text': new_text,
            'significance': significance,
        }

    def test_basic_report(self):
        """Test basic report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            report = gen.generate_comparison_report(
                "https://old.example.com",
                "https://new.example.com",
                [],
                self._make_summary(total=0, added=0, removed=0, modified=0,
                                   high=0, medium=0, low=0)
            )

            assert '# Website Comparison Report' in report
            assert 'https://old.example.com' in report
            assert 'https://new.example.com' in report
            assert '**Total Changes:** 0' in report

    def test_report_with_high_changes(self):
        """Test report with high significance changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            changes = [self._make_change(significance='high')]
            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                changes, self._make_summary()
            )

            assert '## High Significance Changes' in report
            assert 'MODIFIED' in report
            assert 'Old content' in report
            assert 'New content' in report

    def test_report_with_medium_changes(self):
        """Test report with medium significance changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            changes = [self._make_change(significance='medium') for _ in range(3)]
            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                changes, self._make_summary(high=0, medium=3, low=0)
            )

            assert '## Medium Significance Changes' in report
            assert '**Total:** 3 changes' in report

    def test_report_medium_changes_truncation(self):
        """Test medium changes are truncated after 10."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            changes = [self._make_change(significance='medium') for _ in range(15)]
            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                changes, self._make_summary(total=15, high=0, medium=15, low=0)
            )

            assert '... and 5 more medium significance changes' in report

    def test_report_high_changes_truncation(self):
        """Test high changes are truncated after 50."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            changes = [self._make_change(significance='high') for _ in range(55)]
            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                changes, self._make_summary(total=55, high=55, medium=0, low=0)
            )

            assert '... and 5 more high significance changes' in report

    def test_report_added_change(self):
        """Test report with added change (no old_text)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            changes = [self._make_change(change_type='added', old_text='', new_text='New')]
            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                changes, self._make_summary(total=1, added=1, removed=0, modified=0)
            )

            assert 'ADDED' in report
            assert '**Added/New:**' in report

    def test_report_removed_change(self):
        """Test report with removed change (no new_text)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            changes = [self._make_change(change_type='removed', old_text='Gone', new_text='')]
            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                changes, self._make_summary(total=1, added=0, removed=1, modified=0)
            )

            assert 'REMOVED' in report
            assert '**Removed/Changed:**' in report

    def test_report_long_text_truncation(self):
        """Test that long text is truncated in report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            long_text = 'A' * 500
            changes = [self._make_change(old_text=long_text, new_text=long_text)]
            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                changes, self._make_summary()
            )

            assert '...' in report

    def test_report_recommendations_high_significance(self):
        """Test recommendations when high significance changes exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                [], self._make_summary(high=5)
            )

            assert 'Action Required' in report

    def test_report_recommendations_minimal_changes(self):
        """Test recommendations when changes are minimal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                [], self._make_summary(total=2, high=0, medium=2, low=0)
            )

            assert 'Migration Status' in report

    def test_report_with_visual_results(self):
        """Test report with visual comparison results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)

            visual_results = {
                'chrome': {
                    'difference_ratio': 0.02,
                    'different_pixels': 500,
                    'total_pixels': 100000,
                    'screenshot1': '',
                    'screenshot2': '',
                    'comparison': '',
                }
            }

            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                [], self._make_summary(total=0, high=0, medium=0, low=0),
                visual_results=visual_results
            )

            assert '## Visual Comparison' in report
            assert 'CHROME' in report
            assert '2.00%' in report
            assert 'Minimal differences' in report

    def test_report_visual_high_difference(self):
        """Test report with high visual difference."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)

            visual_results = {
                'firefox': {
                    'difference_ratio': 0.15,
                    'different_pixels': 15000,
                    'total_pixels': 100000,
                    'screenshot1': '',
                    'screenshot2': '',
                    'comparison': '',
                }
            }

            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                [], self._make_summary(total=0, high=0, medium=0, low=0),
                visual_results=visual_results
            )

            assert 'Significant differences detected' in report

    def test_report_visual_with_error(self):
        """Test report with visual comparison error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)

            visual_results = {
                'chrome': {
                    'error': 'Browser not found',
                }
            }

            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                [], self._make_summary(total=0, high=0, medium=0, low=0),
                visual_results=visual_results
            )

            assert 'Error' in report
            assert 'Browser not found' in report

    def test_report_visual_recommendations(self):
        """Test visual-specific recommendations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)

            visual_results = {
                'chrome': {
                    'difference_ratio': 0.20,
                    'different_pixels': 20000,
                    'total_pixels': 100000,
                    'screenshot1': '',
                    'screenshot2': '',
                    'comparison': '',
                }
            }

            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                [], self._make_summary(total=0, high=0, medium=0, low=0),
                visual_results=visual_results
            )

            assert 'Visual Differences' in report
            assert 'chrome' in report.lower()

    def test_report_visual_with_screenshots(self):
        """Test report with actual screenshot files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)

            # Create fake screenshot files
            screenshots_dir = os.path.join(tmpdir, "ss")
            os.makedirs(screenshots_dir, exist_ok=True)
            s1 = os.path.join(screenshots_dir, "s1.png")
            s2 = os.path.join(screenshots_dir, "s2.png")
            comp = os.path.join(screenshots_dir, "comp.png")
            for f in [s1, s2, comp]:
                with open(f, 'wb') as fh:
                    fh.write(b'\x89PNG\r\n')  # PNG header bytes

            visual_results = {
                'chrome': {
                    'difference_ratio': 0.05,
                    'different_pixels': 5000,
                    'total_pixels': 100000,
                    'screenshot1': s1,
                    'screenshot2': s2,
                    'comparison': comp,
                }
            }

            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                [], self._make_summary(total=0, high=0, medium=0, low=0),
                visual_results=visual_results
            )

            assert '![' in report  # Image references
            assert 'screenshots/' in report

    def test_report_with_traversal_results(self):
        """Test report with traversal results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)

            traversal_results = [
                {
                    'url1': 'https://a.com/',
                    'url2': 'https://b.com/',
                    'status': 'compared',
                    'high_significance': 3,
                    'changes_count': 10,
                },
                {
                    'url1': 'https://a.com/page2',
                    'url2': 'https://b.com/page2',
                    'status': 'error',
                    'error': 'Timeout',
                }
            ]

            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                [], self._make_summary(total=0, high=0, medium=0, low=0),
                traversal_results=traversal_results
            )

            assert '## Site-Wide Comparison' in report
            assert '**Pages Compared:** 1' in report
            assert '**Pages with Errors:** 1' in report
            assert 'High Significance Differences' in report

    def test_report_traversal_long_urls(self):
        """Test traversal report truncates long URLs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)

            long_url = 'https://example.com/' + 'a' * 100
            traversal_results = [
                {
                    'url1': long_url,
                    'url2': long_url,
                    'status': 'compared',
                    'high_significance': 0,
                    'changes_count': 0,
                }
            ]

            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                [], self._make_summary(total=0, high=0, medium=0, low=0),
                traversal_results=traversal_results
            )

            assert '...' in report  # URL should be truncated

    def test_report_footer(self):
        """Test report footer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                [], self._make_summary(total=0, high=0, medium=0, low=0)
            )

            assert 'Report generated by Wayback-Diff' in report

    def test_report_timestamp(self):
        """Test report contains generation timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            report = gen.generate_comparison_report(
                "https://a.com", "https://b.com",
                [], self._make_summary(total=0, high=0, medium=0, low=0)
            )

            assert '**Generated:**' in report


class TestSaveReport:
    """Test report saving."""

    def test_save_report_auto_filename(self):
        """Test saving report with auto-generated filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            path = gen.save_report("# Test Report")

            assert os.path.exists(path)
            assert path.endswith('.md')
            assert 'comparison_report_' in path

            with open(path) as f:
                assert f.read() == '# Test Report'

    def test_save_report_custom_filename(self):
        """Test saving report with custom filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            path = gen.save_report("# Custom", filename="custom.md")

            assert os.path.exists(path)
            assert path.endswith('custom.md')

    def test_save_report_returns_path(self):
        """Test that save_report returns the file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            path = gen.save_report("# Report")

            assert isinstance(path, str)
            assert tmpdir in path

    def test_save_report_unicode(self):
        """Test saving report with unicode content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = MarkdownReportGenerator(output_dir=tmpdir)
            path = gen.save_report("# Informe con acentos y tildes")

            with open(path, encoding='utf-8') as f:
                content = f.read()
                assert 'acentos' in content
