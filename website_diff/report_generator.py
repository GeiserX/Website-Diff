"""Generate markdown reports with image references."""

import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class MarkdownReportGenerator:
    """Generate markdown reports for website comparisons."""
    
    def __init__(self, output_dir: str = "./reports"):
        """Initialize report generator.
        
        Args:
            output_dir: Directory to save reports and reference images
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_comparison_report(self, 
                                  url1: str,
                                  url2: str,
                                  changes: List[Dict],
                                  summary: Dict,
                                  visual_results: Optional[Dict] = None,
                                  traversal_results: Optional[List[Dict]] = None) -> str:
        """Generate a comprehensive markdown report.
        
        Args:
            url1: First URL
            url2: Second URL
            changes: List of change dictionaries
            summary: Summary dictionary
            visual_results: Optional visual comparison results
            traversal_results: Optional link traversal results
            
        Returns:
            Markdown report as string
        """
        lines = []
        
        # Header
        lines.append("# Website Comparison Report")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("## URLs Compared")
        lines.append("")
        lines.append(f"- **URL 1:** [{url1}]({url1})")
        lines.append(f"- **URL 2:** [{url2}]({url2})")
        lines.append("")
        
        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(f"- **Total Changes:** {summary.get('total_changes', 0)}")
        lines.append(f"- **Added:** {summary.get('added', 0)}")
        lines.append(f"- **Removed:** {summary.get('removed', 0)}")
        lines.append(f"- **Modified:** {summary.get('modified', 0)}")
        lines.append("")
        lines.append("### Significance Breakdown")
        lines.append("")
        lines.append(f"- **High Significance:** {summary.get('high_significance', 0)}")
        lines.append(f"- **Medium Significance:** {summary.get('medium_significance', 0)}")
        lines.append(f"- **Low Significance:** {summary.get('low_significance', 0)}")
        lines.append("")
        
        # Visual Comparison Section
        if visual_results:
            lines.append("## Visual Comparison")
            lines.append("")
            lines.append("Screenshots have been captured for visual inspection. The images below show side-by-side comparisons with differences highlighted.")
            lines.append("")
            
            for browser, result in visual_results.items():
                if 'error' in result:
                    lines.append(f"### {browser.upper()} Browser")
                    lines.append("")
                    lines.append(f"❌ **Error:** {result['error']}")
                    lines.append("")
                else:
                    diff_ratio = result.get('difference_ratio', 0) * 100
                    diff_pixels = result.get('different_pixels', 0)
                    total_pixels = result.get('total_pixels', 0)
                    
                    lines.append(f"### {browser.upper()} Browser")
                    lines.append("")
                    lines.append(f"- **Visual Difference:** {diff_ratio:.2f}%")
                    lines.append(f"- **Different Pixels:** {diff_pixels:,} / {total_pixels:,}")
                    lines.append(f"- **Status:** {'⚠️ Significant differences detected' if diff_ratio > 5 else '✅ Minimal differences'}")
                    lines.append("")
                    
                    # Image references
                    screenshot1 = result.get('screenshot1', '')
                    screenshot2 = result.get('screenshot2', '')
                    comparison = result.get('comparison', '')
                    
                    # Copy screenshots to report directory for easier access
                    if screenshot1 or screenshot2 or comparison:
                        import shutil
                        report_screenshots_dir = self.output_dir / "screenshots"
                        report_screenshots_dir.mkdir(exist_ok=True)
                        
                        if screenshot1 and os.path.exists(screenshot1):
                            screenshot1_name = f"{browser}_url1.png"
                            report_screenshot1 = report_screenshots_dir / screenshot1_name
                            if not report_screenshot1.exists() or os.path.getmtime(screenshot1) > os.path.getmtime(report_screenshot1):
                                shutil.copy2(screenshot1, report_screenshot1)
                            rel_path1 = f"screenshots/{screenshot1_name}"
                            lines.append(f"#### Original (URL 1)")
                            lines.append("")
                            lines.append(f"![Original Screenshot]({rel_path1})")
                            lines.append("")
                            lines.append(f"*Full screenshot of the original page*")
                            lines.append("")
                        
                        if screenshot2 and os.path.exists(screenshot2):
                            screenshot2_name = f"{browser}_url2.png"
                            report_screenshot2 = report_screenshots_dir / screenshot2_name
                            if not report_screenshot2.exists() or os.path.getmtime(screenshot2) > os.path.getmtime(report_screenshot2):
                                shutil.copy2(screenshot2, report_screenshot2)
                            rel_path2 = f"screenshots/{screenshot2_name}"
                            lines.append(f"#### New (URL 2)")
                            lines.append("")
                            lines.append(f"![New Screenshot]({rel_path2})")
                            lines.append("")
                            lines.append(f"*Full screenshot of the new page*")
                            lines.append("")
                        
                        if comparison and os.path.exists(comparison):
                            comparison_name = f"{browser}_comparison.png"
                            report_comparison = report_screenshots_dir / comparison_name
                            if not report_comparison.exists() or os.path.getmtime(comparison) > os.path.getmtime(report_comparison):
                                shutil.copy2(comparison, report_comparison)
                            rel_path_comp = f"screenshots/{comparison_name}"
                            lines.append(f"#### Difference Highlight")
                            lines.append("")
                            lines.append(f"![Comparison with Differences Highlighted]({rel_path_comp})")
                            lines.append("")
                            lines.append("*Red pixels indicate differences between the two pages. This side-by-side comparison shows the original page, the new page, and a visual diff highlighting all pixel differences.*")
                            lines.append("")
            
            lines.append("---")
            lines.append("")
        
        # High Significance Changes
        high_changes = [c for c in changes if c.get('significance') == 'high']
        if high_changes:
            lines.append("## High Significance Changes")
            lines.append("")
            lines.append("These changes affect structure, content, or critical functionality.")
            lines.append("")
            
            for i, change in enumerate(high_changes[:50], 1):  # Limit to 50
                lines.append(f"### Change {i}: {change.get('type', 'unknown').upper()}")
                lines.append("")
                
                if change.get('old_text'):
                    old_preview = change['old_text'][:300].replace('\n', ' ')
                    lines.append("**Removed/Changed:**")
                    lines.append("```")
                    lines.append(old_preview + ("..." if len(change['old_text']) > 300 else ""))
                    lines.append("```")
                    lines.append("")
                
                if change.get('new_text'):
                    new_preview = change['new_text'][:300].replace('\n', ' ')
                    lines.append("**Added/New:**")
                    lines.append("```")
                    lines.append(new_preview + ("..." if len(change['new_text']) > 300 else ""))
                    lines.append("```")
                    lines.append("")
                
                if len(high_changes) > 50 and i == 50:
                    lines.append(f"*... and {len(high_changes) - 50} more high significance changes*")
                    lines.append("")
                    break
                
                lines.append("---")
                lines.append("")
        
        # Medium Significance Changes Summary
        medium_changes = [c for c in changes if c.get('significance') == 'medium']
        if medium_changes:
            lines.append("## Medium Significance Changes")
            lines.append("")
            lines.append(f"**Total:** {len(medium_changes)} changes")
            lines.append("")
            lines.append("These changes affect attributes, styling, or layout elements.")
            lines.append("")
            
            # Show first 10 as examples
            for i, change in enumerate(medium_changes[:10], 1):
                lines.append(f"{i}. **{change.get('type', 'unknown')}** - {change.get('old_text', '')[:100]}...")
            
            if len(medium_changes) > 10:
                lines.append("")
                lines.append(f"*... and {len(medium_changes) - 10} more medium significance changes*")
            lines.append("")
        
        # Link Traversal Results
        if traversal_results:
            lines.append("## Site-Wide Comparison")
            lines.append("")
            compared = [r for r in traversal_results if r.get('status') == 'compared']
            errors = [r for r in traversal_results if r.get('status') == 'error']
            
            lines.append(f"- **Pages Compared:** {len(compared)}")
            lines.append(f"- **Pages with Errors:** {len(errors)}")
            lines.append("")
            
            # High significance differences across site
            high_diff_pages = [r for r in compared if r.get('high_significance', 0) > 0]
            if high_diff_pages:
                lines.append("### Pages with High Significance Differences")
                lines.append("")
                for result in high_diff_pages:
                    lines.append(f"- **{result.get('url1', 'Unknown')}**")
                    lines.append(f"  - High significance changes: {result.get('high_significance', 0)}")
                    lines.append(f"  - Total changes: {result.get('changes_count', 0)}")
                    lines.append("")
            
            # All pages summary
            lines.append("### All Pages Summary")
            lines.append("")
            lines.append("| URL | Status | High Sig | Total Changes |")
            lines.append("|-----|--------|----------|---------------|")
            for result in traversal_results:
                url = result.get('url1', 'Unknown')
                if len(url) > 50:
                    url = url[:47] + "..."
                status = "✅ Compared" if result.get('status') == 'compared' else "❌ Error"
                high_sig = result.get('high_significance', 0)
                total = result.get('changes_count', 0)
                lines.append(f"| {url} | {status} | {high_sig} | {total} |")
            lines.append("")
        
        # Recommendations
        lines.append("## Recommendations")
        lines.append("")
        if summary.get('high_significance', 0) > 0:
            lines.append("⚠️ **Action Required:** High significance changes detected. Review these changes carefully as they may affect:")
            lines.append("- Page structure and layout")
            lines.append("- Content and messaging")
            lines.append("- Script and stylesheet references")
            lines.append("- Meta tags and SEO elements")
            lines.append("")
        
        if visual_results:
            for browser, result in visual_results.items():
                if 'error' not in result:
                    diff_ratio = result.get('difference_ratio', 0) * 100
                    if diff_ratio > 10:
                        lines.append(f"⚠️ **Visual Differences ({browser}):** Significant visual differences ({diff_ratio:.1f}%) detected. Review screenshots above.")
                        lines.append("")
        
        if summary.get('high_significance', 0) == 0 and summary.get('medium_significance', 0) < 10:
            lines.append("✅ **Migration Status:** Changes appear to be minimal. The migration looks successful!")
            lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*Report generated by Website-Diff*")
        lines.append("")
        
        return "\n".join(lines)
    
    def save_report(self, report: str, filename: str = None) -> str:
        """Save report to file.
        
        Args:
            report: Markdown report content
            filename: Optional filename (default: auto-generated)
            
        Returns:
            Path to saved report
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"comparison_report_{timestamp}.md"
        
        report_path = self.output_dir / filename
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return str(report_path)
