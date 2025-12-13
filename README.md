# Website-Diff

A comprehensive Python tool for detecting meaningful differences between two web pages, with special support for cleaning Wayback Machine artifacts. Perfect for developers migrating websites or verifying changes.

## Features

- **Intelligent Diff Engine**: Focuses on meaningful changes (content, structure, scripts) while ignoring noise
- **Wayback Machine Support**: Automatically detects and removes Wayback Machine banners, scripts, and URL rewrites
- **Significance Scoring**: Categorizes changes as high, medium, or low significance
- **Multiple Output Formats**: Text, JSON, and unified diff formats
- **Visual Comparison**: Take screenshots in multiple browsers and generate side-by-side comparison images
- **Developer-Focused**: Highlights changes that matter for migrations and development

## Installation

```bash
# Clone the repository
git clone https://github.com/sergio/Website-Diff.git
cd Website-Diff

# Create virtual environment (recommended)
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install basic dependencies
pip install -r requirements.txt

# For visual comparison (optional but recommended)
pip install selenium Pillow webdriver-manager

# Install in development mode
pip install -e .
```

## Usage

### Basic Comparison

Compare two URLs:

```bash
website-diff https://example.com/page1 https://example.com/page2
```

### Wayback Machine Support

The tool automatically detects Wayback Machine URLs and cleans artifacts:

```bash
# Compare a Wayback archive with current page
website-diff https://web.archive.org/web/20230101/https://example.com/ https://example.com/

# Compare two Wayback archives
website-diff https://web.archive.org/web/20230101/https://example.com/ \
              https://web.archive.org/web/20230201/https://example.com/
```

### Output Options

Save output to a file:

```bash
website-diff url1 url2 -o diff.txt
```

Output as JSON:

```bash
website-diff url1 url2 --format json
```

Unified diff format:

```bash
website-diff url1 url2 --format unified
```

Generate markdown report (includes visual comparison images):

```bash
website-diff url1 url2 --markdown
```

The markdown report includes:
- Executive summary with change statistics
- Visual comparison screenshots (if `--visual` is used)
- High/medium/low significance changes
- Site-wide comparison results (if `--traverse` is used)
- Recommendations based on findings

Reports are saved to `./reports/` by default (configurable with `--report-dir`).

### Visual Comparison

Take screenshots and compare them visually:

```bash
# Enable visual comparison (screenshots)
website-diff url1 url2 --visual

# Auto-detect and use all available browsers (default)
website-diff url1 url2 --visual --markdown

# Compare in specific browsers
website-diff url1 url2 --visual --browsers chrome firefox edge

# Generate markdown report with images
website-diff url1 url2 --visual --markdown

# Custom screenshot directory
website-diff url1 url2 --visual --screenshot-dir ./my-screenshots

# Custom viewport size
website-diff url1 url2 --visual --viewport-width 1280 --viewport-height 720

# Run browser in visible mode (for debugging)
website-diff url1 url2 --visual --no-headless
```

Visual comparison generates:
- Screenshots of both pages in each browser
- Side-by-side comparison images
- Difference highlighting (red pixels show differences)
- Markdown report with embedded image references (when using `--markdown`)

### Advanced Options

```bash
# Don't clean Wayback Machine artifacts
website-diff url1 url2 --no-clean-wayback

# Don't ignore whitespace differences
website-diff url1 url2 --no-ignore-whitespace

# Set custom timeout
website-diff url1 url2 --timeout 60

# Verbose output
website-diff url1 url2 --verbose
```

## How It Works

### Wayback Machine Cleaning

When a Wayback Machine URL is detected, the tool automatically:

1. **Removes Header Artifacts**: Strips analytics scripts, playback scripts, and banner CSS
2. **Removes Footer Comments**: Removes archival metadata and copyright notices
3. **Restores URLs**: Converts Wayback-prefixed URLs back to original URLs
4. **Normalizes Content**: Handles whitespace and formatting differences

### Significance Scoring

Changes are categorized by significance:

- **High Significance**: Structural changes, content changes, meta tags, scripts, stylesheets
- **Medium Significance**: Attribute changes, styling, div/span modifications
- **Low Significance**: Whitespace, comments, minor formatting

### Intelligent Comparison

The diff engine:

- Focuses on meaningful content changes
- Ignores noise like timestamps, auto-generated IDs
- Provides context around changes
- Groups changes by significance for easy review

## Use Cases

### Website Migration Verification

After migrating a website from Wayback Machine archives, verify that the migration was successful:

```bash
website-diff https://web.archive.org/web/20230101/https://oldsite.com/ https://newsite.com/
```

### Change Detection

Monitor a website for meaningful changes:

```bash
website-diff https://example.com/page1 https://example.com/page2 -o changes.txt

# With markdown report
website-diff https://example.com/page1 https://example.com/page2 --markdown
```

### Development Testing

Compare development and production versions:

```bash
website-diff https://dev.example.com/page https://prod.example.com/page
```

## Output Format

### Text Output

The default text output includes:

- Summary statistics (total changes, added/removed/modified)
- Significance breakdown
- Detailed changes grouped by significance
- Context around each change

### JSON Output

Structured JSON output for programmatic processing:

```json
{
  "summary": {
    "total_changes": 15,
    "added": 5,
    "removed": 3,
    "modified": 7,
    "high_significance": 2,
    "medium_significance": 8,
    "low_significance": 5
  },
  "changes": [
    {
      "type": "modified",
      "old_text": "...",
      "new_text": "...",
      "significance": "high",
      ...
    }
  ]
}
```

## Exit Codes

- `0`: No changes detected
- `1`: Low or medium significance changes
- `2`: High significance changes detected

## Requirements

- Python 3.8+
- requests library
- For visual comparison:
  - selenium
  - Pillow (PIL)
  - webdriver-manager (optional, for automatic driver management)
  - Chrome or Firefox browser installed

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).

**Note**: This software is NOT for commercial use.

See the [LICENSE](LICENSE) file for details.

## Testing

Run tests locally:

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=website_diff --cov-report=html
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Ensure all tests pass: `pytest tests/ -v`
6. Submit a Pull Request

## CI/CD

The project uses GitHub Actions for:
- **CI**: Runs tests on push/PR across Python 3.8-3.11
- **Release**: Automatically creates GitHub releases when version tags are pushed

To create a release:
```bash
git tag v1.0.0
git push origin v1.0.0
```

This will:
1. Run all tests
2. Build the package
3. Create a GitHub release with distribution files

## Acknowledgments

Inspired by discussions on software testing tools for comparing websites, particularly for migration scenarios.
