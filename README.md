# Website-Diff

A comprehensive Python tool for detecting meaningful differences between two web pages, with special support for cleaning Wayback Machine artifacts. Perfect for developers migrating websites or verifying changes.

## Features

- **Intelligent Diff Engine**: Focuses on meaningful changes (content, structure, scripts) while ignoring noise
- **Wayback Machine Support**: Automatically detects and removes Wayback Machine banners, scripts, and URL rewrites
- **Significance Scoring**: Categorizes changes as high, medium, or low significance
- **Multiple Output Formats**: Text, JSON, and unified diff formats
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

# Install dependencies
pip install -r requirements.txt

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

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).

**Note**: This software is NOT for commercial use.

See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

Inspired by discussions on software testing tools for comparing websites, particularly for migration scenarios.
