"""Command-line interface for Website-Diff."""

import argparse
import sys
from typing import Optional
from pathlib import Path

from website_diff.fetcher import WebFetcher
from website_diff.wayback_cleaner import WaybackCleaner
from website_diff.diff_engine import DiffEngine
from website_diff.link_traverser import LinkTraverser
from website_diff.report_generator import MarkdownReportGenerator

# Optional visual comparison import
try:
    from website_diff.visual_comparison import VisualComparison
    VISUAL_COMPARISON_AVAILABLE = True
except ImportError:
    VISUAL_COMPARISON_AVAILABLE = False


def format_output(changes: list, summary: dict, output_format: str = "text") -> str:
    """Format diff output.
    
    Args:
        changes: List of change dictionaries
        summary: Summary dictionary
        output_format: Output format ('text', 'json', 'unified')
        
    Returns:
        Formatted output string
    """
    if output_format == "json":
        import json
        return json.dumps({
            'summary': summary,
            'changes': changes
        }, indent=2, ensure_ascii=False)
    
    elif output_format == "unified":
        # This would be generated separately
        return ""
    
    else:  # text format
        lines = []
        lines.append("=" * 80)
        lines.append("WEBSITE DIFF SUMMARY")
        lines.append("=" * 80)
        lines.append(f"Total changes: {summary['total_changes']}")
        lines.append(f"  Added: {summary['added']}")
        lines.append(f"  Removed: {summary['removed']}")
        lines.append(f"  Modified: {summary['modified']}")
        lines.append("")
        lines.append("Significance breakdown:")
        lines.append(f"  High: {summary['high_significance']}")
        lines.append(f"  Medium: {summary['medium_significance']}")
        lines.append(f"  Low: {summary['low_significance']}")
        lines.append("")
        lines.append("=" * 80)
        lines.append("DETAILED CHANGES")
        lines.append("=" * 80)
        lines.append("")
        
        # Group changes by significance
        high_changes = [c for c in changes if c['significance'] == 'high']
        medium_changes = [c for c in changes if c['significance'] == 'medium']
        low_changes = [c for c in changes if c['significance'] == 'low']
        
        if high_changes:
            lines.append("HIGH SIGNIFICANCE CHANGES:")
            lines.append("-" * 80)
            for i, change in enumerate(high_changes[:20], 1):  # Limit to 20
                lines.append(f"\nChange {i} ({change['type']}):")
                if change['old_text']:
                    lines.append(f"  OLD: {change['old_text'][:200]}...")
                if change['new_text']:
                    lines.append(f"  NEW: {change['new_text'][:200]}...")
            if len(high_changes) > 20:
                lines.append(f"\n... and {len(high_changes) - 20} more high significance changes")
            lines.append("")
        
        if medium_changes:
            lines.append("MEDIUM SIGNIFICANCE CHANGES:")
            lines.append("-" * 80)
            for i, change in enumerate(medium_changes[:10], 1):  # Limit to 10
                lines.append(f"\nChange {i} ({change['type']}):")
                if change['old_text']:
                    lines.append(f"  OLD: {change['old_text'][:150]}...")
                if change['new_text']:
                    lines.append(f"  NEW: {change['new_text'][:150]}...")
            if len(medium_changes) > 10:
                lines.append(f"\n... and {len(medium_changes) - 10} more medium significance changes")
            lines.append("")
        
        if low_changes and len(low_changes) <= 50:
            lines.append("LOW SIGNIFICANCE CHANGES:")
            lines.append("-" * 80)
            lines.append(f"({len(low_changes)} low significance changes - mostly formatting/whitespace)")
            lines.append("")
        
        return "\n".join(lines)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Compare two web pages and detect meaningful differences",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two URLs
  website-diff https://example.com/page1 https://example.com/page2
  
  # Compare with Wayback Machine URLs (auto-cleans artifacts)
  website-diff https://web.archive.org/web/20230101/https://example.com/ https://example.com/
  
  # Save output to file
  website-diff url1 url2 -o diff.txt
  
  # Output as JSON
  website-diff url1 url2 --format json
        """
    )
    
    parser.add_argument(
        "url1",
        help="First URL to compare"
    )
    
    parser.add_argument(
        "url2",
        help="Second URL to compare"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file path (default: stdout)"
    )
    
    parser.add_argument(
        "-f", "--format",
        choices=["text", "json", "unified"],
        default="text",
        help="Output format (default: text)"
    )
    
    parser.add_argument(
        "--no-clean-wayback",
        action="store_true",
        help="Don't automatically clean Wayback Machine artifacts"
    )
    
    parser.add_argument(
        "--ignore-whitespace",
        action="store_true",
        default=True,
        help="Ignore whitespace differences (default: True)"
    )
    
    parser.add_argument(
        "--no-ignore-whitespace",
        dest="ignore_whitespace",
        action="store_false",
        help="Don't ignore whitespace differences"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--visual",
        action="store_true",
        help="Enable visual comparison (screenshots)"
    )
    
    parser.add_argument(
        "--browsers",
        nargs="+",
        choices=["chrome", "chromium", "firefox", "opera", "edge", "auto"],
        default=["auto"],
        help="Browsers to use for visual comparison (default: auto-detect available)"
    )
    
    parser.add_argument(
        "--screenshot-dir",
        type=str,
        default=None,  # Will be set to {report_dir}/screenshots if not specified
        help="Directory to save screenshots (default: {report-dir}/screenshots)"
    )
    
    parser.add_argument(
        "--viewport-width",
        type=int,
        default=1920,
        help="Browser viewport width for screenshots (default: 1920)"
    )
    
    parser.add_argument(
        "--viewport-height",
        type=int,
        default=1080,
        help="Browser viewport height for screenshots (default: 1080)"
    )
    
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in non-headless mode (for debugging)"
    )
    
    parser.add_argument(
        "--traverse",
        action="store_true",
        help="Traverse all links and compare entire site"
    )
    
    parser.add_argument(
        "--max-depth",
        type=int,
        default=2,
        help="Maximum depth for link traversal (default: 2)"
    )
    
    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Maximum number of pages to compare (default: 50)"
    )
    
    parser.add_argument(
        "--report-dir",
        type=str,
        default="./reports",
        help="Directory to save markdown reports (default: ./reports)"
    )
    
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Generate markdown report in addition to text output"
    )
    
    args = parser.parse_args()
    
    # Fetch content
    fetcher = WebFetcher(timeout=args.timeout)
    
    if args.verbose:
        print(f"Fetching {args.url1}...", file=sys.stderr)
    
    content1, content_type1, metadata1 = fetcher.fetch(args.url1)
    if content1 is None:
        print(f"Error: Failed to fetch {args.url1}", file=sys.stderr)
        if metadata1 and metadata1.get("error"):
            print(f"  Error: {metadata1['error']}", file=sys.stderr)
        sys.exit(1)
    
    if args.verbose:
        print(f"Fetching {args.url2}...", file=sys.stderr)
    
    content2, content_type2, metadata2 = fetcher.fetch(args.url2)
    if content2 is None:
        print(f"Error: Failed to fetch {args.url2}", file=sys.stderr)
        if metadata2 and metadata2.get("error"):
            print(f"  Error: {metadata2['error']}", file=sys.stderr)
        sys.exit(1)
    
    # Check if content is HTML
    if not fetcher.is_html(content_type1) or not fetcher.is_html(content_type2):
        print("Warning: One or both URLs may not be HTML content", file=sys.stderr)
    
    # Clean Wayback Machine artifacts if needed
    if not args.no_clean_wayback:
        if WaybackCleaner.is_wayback_url(args.url1):
            if args.verbose:
                print("Cleaning Wayback Machine artifacts from URL1...", file=sys.stderr)
            content1 = WaybackCleaner.clean_wayback_html(content1, args.url1)
        
        if WaybackCleaner.is_wayback_url(args.url2):
            if args.verbose:
                print("Cleaning Wayback Machine artifacts from URL2...", file=sys.stderr)
            content2 = WaybackCleaner.clean_wayback_html(content2, args.url2)
    
    # Check if we should traverse links
    traversal_results = None
    if args.traverse:
        if args.verbose:
            print("Starting link traversal comparison...", file=sys.stderr)
        
        traverser = LinkTraverser(
            args.url1,
            args.url2,
            max_depth=args.max_depth,
            max_pages=args.max_pages
        )
        
        traversal_results = traverser.traverse_and_compare()
        report = traverser.generate_report()
        
        # Generate markdown report for traversal if requested
        markdown_report_path = None
        if args.markdown or args.visual:
            report_gen = MarkdownReportGenerator(output_dir=args.report_dir)
            markdown_report = report_gen.generate_comparison_report(
                args.url1,
                args.url2,
                [],  # Changes from individual pages not aggregated
                {'total_changes': 0},  # Summary from traversal
                visual_results=None,
                traversal_results=traversal_results
            )
            markdown_report_path = report_gen.save_report(markdown_report)
            if args.verbose:
                print(f"Markdown report saved to: {markdown_report_path}", file=sys.stderr)
        
        # Print markdown report location
        if markdown_report_path:
            print(f"\n📄 Markdown report: {markdown_report_path}", file=sys.stderr)
        
        # Write text report
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            if args.verbose:
                print(f"Text report written to {args.output}", file=sys.stderr)
        else:
            print(report)
        
        # Exit code based on results
        high_diff_count = sum(1 for r in traversal_results if r.get('high_significance', 0) > 0)
        if high_diff_count > 0:
            sys.exit(2)
        elif len([r for r in traversal_results if r.get('status') == 'compared']) > 0:
            sys.exit(1)
        else:
            sys.exit(0)
    
    # Compare single pages
    if args.verbose:
        print("Comparing pages...", file=sys.stderr)
    
    diff_engine = DiffEngine(ignore_whitespace=args.ignore_whitespace)
    changes = diff_engine.extract_meaningful_changes(content1, content2)
    summary = diff_engine.get_summary(changes)
    
    # Generate output
    if args.format == "unified":
        output_lines = diff_engine.generate_unified_diff(
            content1, content2,
            old_label=args.url1,
            new_label=args.url2
        )
        output = "\n".join(output_lines)
    else:
        output = format_output(changes, summary, args.format)
    
    # Visual comparison results (will be populated if --visual is used)
    visual_results = None
    
    # Determine screenshot directory (use report_dir/screenshots if not specified)
    screenshot_dir = args.screenshot_dir
    if screenshot_dir is None:
        screenshot_dir = str(Path(args.report_dir) / "screenshots")
    
    # Visual comparison if requested
    if args.visual:
        if not VISUAL_COMPARISON_AVAILABLE:
            print("\nError: Visual comparison requires additional dependencies.", file=sys.stderr)
            print("Install with: pip install selenium Pillow webdriver-manager", file=sys.stderr)
            sys.exit(1)
        
        if args.verbose:
            print("\nStarting visual comparison...", file=sys.stderr)
        
        try:
            # Handle auto-detect
            browsers_to_use = args.browsers
            if browsers_to_use == ["auto"] or (len(browsers_to_use) == 1 and browsers_to_use[0] == "auto"):
                browsers_to_use = None  # Will auto-detect
            
            visual = VisualComparison(
                browser='chrome',  # Default, will be overridden in compare_urls
                headless=not args.no_headless,
                viewport_width=args.viewport_width,
                viewport_height=args.viewport_height
            )
            
            visual_results = visual.compare_urls(
                args.url1,
                args.url2,
                screenshot_dir,
                browsers=browsers_to_use
            )
            
            # Print visual comparison results
            print("\n" + "=" * 80, file=sys.stderr)
            print("VISUAL COMPARISON RESULTS", file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            
            for browser, result in visual_results.items():
                if 'error' in result:
                    print(f"\n{browser.upper()}: Error - {result['error']}", file=sys.stderr)
                else:
                    diff_ratio = result.get('difference_ratio', 0) * 100
                    print(f"\n{browser.upper()}:", file=sys.stderr)
                    print(f"  Difference: {diff_ratio:.2f}%", file=sys.stderr)
                    print(f"  Different pixels: {result.get('different_pixels', 0):,}", file=sys.stderr)
                    print(f"  Screenshot 1: {result.get('screenshot1', 'N/A')}", file=sys.stderr)
                    print(f"  Screenshot 2: {result.get('screenshot2', 'N/A')}", file=sys.stderr)
                    print(f"  Comparison: {result.get('comparison', 'N/A')}", file=sys.stderr)
            
            print("\n" + "=" * 80, file=sys.stderr)
            print(f"Screenshots saved to: {screenshot_dir}", file=sys.stderr)
            
        except ImportError as e:
            print(f"\nWarning: Visual comparison not available: {e}", file=sys.stderr)
            print("Install required packages: pip install selenium Pillow webdriver-manager", file=sys.stderr)
        except Exception as e:
            print(f"\nError during visual comparison: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
    
    # Generate markdown report if requested
    markdown_report_path = None
    if args.markdown or args.visual:
        if args.verbose:
            print("\nGenerating markdown report...", file=sys.stderr)
        
        report_gen = MarkdownReportGenerator(output_dir=args.report_dir)
        markdown_report = report_gen.generate_comparison_report(
            args.url1,
            args.url2,
            changes,
            summary,
            visual_results=visual_results,
            traversal_results=None  # Will be set if traverse is used
        )
        
        markdown_report_path = report_gen.save_report(markdown_report)
        if args.verbose:
            print(f"Markdown report saved to: {markdown_report_path}", file=sys.stderr)
    
    # Write text output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output)
        if args.verbose:
            print(f"Text output written to {args.output}", file=sys.stderr)
    else:
        print(output)
    
    # Print markdown report location
    if markdown_report_path:
        print(f"\n📄 Markdown report: {markdown_report_path}", file=sys.stderr)
    
    # Exit code based on changes
    if summary['total_changes'] == 0:
        sys.exit(0)
    elif summary['high_significance'] > 0:
        sys.exit(2)  # High significance changes
    else:
        sys.exit(1)  # Low/medium significance changes


if __name__ == "__main__":
    main()
