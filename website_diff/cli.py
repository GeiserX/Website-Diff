"""Command-line interface for Website-Diff."""

import argparse
import sys
from typing import Optional
from pathlib import Path

from website_diff.fetcher import WebFetcher
from website_diff.wayback_cleaner import WaybackCleaner
from website_diff.diff_engine import DiffEngine


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
    
    # Compare
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
    
    # Write output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output)
        if args.verbose:
            print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(output)
    
    # Exit code based on changes
    if summary['total_changes'] == 0:
        sys.exit(0)
    elif summary['high_significance'] > 0:
        sys.exit(2)  # High significance changes
    else:
        sys.exit(1)  # Low/medium significance changes


if __name__ == "__main__":
    main()
