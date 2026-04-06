<p align="center">
  <img src="https://raw.githubusercontent.com/GeiserX/Wayback-Diff/main/docs/images/banner.svg" alt="Wayback-Diff Banner" width="900"/>
</p>

<p align="center">
  <strong>Detect meaningful differences between web pages -- with Wayback Machine artifact cleaning, visual comparison, and significance scoring.</strong>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11-blue?logo=python&logoColor=white" alt="Python Versions"/></a>
  <a href="https://pypi.org/project/wayback-diff/"><img src="https://img.shields.io/pypi/v/wayback-diff?style=flat-square" alt="PyPI"></a>
  <a href="https://github.com/GeiserX/Wayback-Diff/releases/latest"><img src="https://img.shields.io/github/v/release/GeiserX/Wayback-Diff?color=orange" alt="Version"/></a>
  <a href="https://github.com/GeiserX/Wayback-Diff/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-green" alt="License: GPL-3.0"/></a>
  <a href="https://hub.docker.com/"><img src="https://img.shields.io/badge/docker-ready-blue?logo=docker&logoColor=white" alt="Docker"/></a>
</p>

---

## Why Wayback-Diff?

Comparing web pages sounds simple until you deal with Wayback Machine injection artifacts, insignificant whitespace noise, and visual regressions invisible to the DOM. **Wayback-Diff** is a purpose-built CLI that solves all three:

- **Wayback Machine cleaning** -- automatically strips banners, analytics scripts, playback code, and URL rewrites so you compare *actual* content.
- **Significance scoring** -- every change is tagged High, Medium, or Low so you focus on what matters.
- **Multi-browser visual comparison** -- captures screenshots in Chrome, Firefox, Edge, and Opera, then generates pixel-diff images.
- **CI/CD-ready exit codes** -- integrate directly into pipelines (`0` = no changes, `1` = low/medium, `2` = high).

---

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Visual Comparison](#visual-comparison)
- [Markdown Reports](#markdown-reports)
- [CI/CD Integration](#cicd-integration)
- [How It Works](#how-it-works)
- [Output Formats](#output-formats)
- [Comparison with Similar Tools](#comparison-with-similar-tools)
- [Contributing](#contributing)
- [License](#license)

---

## Quick Start

```bash
pip install wayback-diff

# Compare two pages
wayback-diff https://example.com/old https://example.com/new

# Compare a Wayback snapshot with the live site
wayback-diff https://web.archive.org/web/20230101/https://example.com/ https://example.com/

# Full report: visual diff + markdown
wayback-diff https://old.example.com https://new.example.com --visual --markdown
```

---

## Installation

### From PyPI

```bash
pip install wayback-diff

# With visual comparison support
pip install wayback-diff[visual]
```

### From source

```bash
git clone https://github.com/GeiserX/Wayback-Diff.git
cd Wayback-Diff
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

For visual comparison support:

```bash
pip install -e ".[visual]"
```

### Docker

```bash
docker build -t wayback-diff .
docker run --rm wayback-diff https://example.com/a https://example.com/b
```

---

## Usage

### Basic comparison

```bash
wayback-diff https://example.com/page1 https://example.com/page2
```

### Wayback Machine support

The tool automatically detects Wayback Machine URLs and cleans injection artifacts before comparing:

```bash
# Archive vs. live site
wayback-diff https://web.archive.org/web/20230101/https://example.com/ https://example.com/

# Two archive snapshots
wayback-diff \
  https://web.archive.org/web/20230101/https://example.com/ \
  https://web.archive.org/web/20230601/https://example.com/
```

### Output formats

```bash
# Save to file
wayback-diff url1 url2 -o diff.txt

# JSON (for programmatic consumption)
wayback-diff url1 url2 --format json

# Unified diff
wayback-diff url1 url2 --format unified
```

### Site-wide traversal

```bash
# Crawl and compare across linked pages (depth-limited)
wayback-diff url1 url2 --traverse --depth 2
```

### Advanced options

| Flag | Description |
|------|-------------|
| `--no-clean-wayback` | Disable Wayback Machine artifact removal |
| `--no-ignore-whitespace` | Treat whitespace changes as significant |
| `--timeout N` | Set HTTP timeout in seconds (default: 30) |
| `--verbose` | Enable detailed logging |

---

## Visual Comparison

Take screenshots in one or more browsers and generate side-by-side difference images:

```bash
# Auto-detect all installed browsers
wayback-diff url1 url2 --visual

# Specific browsers
wayback-diff url1 url2 --visual --browsers chrome firefox edge opera

# Custom viewport
wayback-diff url1 url2 --visual --viewport-width 1280 --viewport-height 720

# Non-headless mode (for debugging)
wayback-diff url1 url2 --visual --no-headless

# Custom screenshot output
wayback-diff url1 url2 --visual --screenshot-dir ./my-screenshots
```

Visual comparison generates:
- Screenshots of both pages per browser
- Side-by-side comparison images
- Pixel-level difference highlighting (red overlay marks changes)

---

## Markdown Reports

Generate comprehensive Markdown reports that include everything in a single reviewable document:

```bash
wayback-diff url1 url2 --visual --markdown --report-dir ./reports
```

Each report contains:
- Executive summary with change statistics
- Visual comparison screenshots (when `--visual` is used)
- Changes grouped by significance (High / Medium / Low)
- Site-wide results (when `--traverse` is used)
- Actionable recommendations

---

## CI/CD Integration

Wayback-Diff returns meaningful exit codes designed for pipeline gates:

| Exit Code | Meaning |
|-----------|---------|
| `0` | No differences detected |
| `1` | Low or medium significance changes |
| `2` | High significance changes detected |

### GitHub Actions example

```yaml
name: Visual Regression Check
on:
  pull_request:

jobs:
  diff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Wayback-Diff
        run: |
          pip install -r requirements.txt
          pip install -e ".[visual]"

      - name: Compare staging vs production
        run: |
          wayback-diff \
            https://staging.example.com \
            https://production.example.com \
            --visual --markdown --format json -o diff.json

      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: diff-report
          path: reports/
```

### Shell script gate

```bash
wayback-diff "$OLD_URL" "$NEW_URL" --format json -o result.json
EXIT_CODE=$?

if [ $EXIT_CODE -eq 2 ]; then
  echo "BLOCKING: high-significance changes detected"
  exit 1
elif [ $EXIT_CODE -eq 1 ]; then
  echo "WARNING: minor changes detected"
fi
```

---

## How It Works

### Wayback Machine cleaning

When a Wayback Machine URL is detected, the tool automatically:

1. **Removes header artifacts** -- strips analytics scripts, playback scripts, and banner CSS injected by the Wayback Machine.
2. **Removes footer comments** -- removes archival metadata and copyright notices.
3. **Restores URLs** -- converts `web.archive.org/web/…/` prefixed URLs back to their originals.
4. **Normalizes content** -- handles whitespace and formatting differences introduced by archival.

### Significance scoring

Every detected change is categorized:

| Level | Examples |
|-------|----------|
| **High** | Structural changes, content text, meta tags, scripts, stylesheets |
| **Medium** | Attribute changes, inline styling, div/span modifications |
| **Low** | Whitespace, comments, minor formatting |

### Intelligent comparison

The diff engine:
- Focuses on meaningful content changes
- Ignores noise like timestamps and auto-generated IDs
- Provides context around each change
- Groups results by significance for fast review

---

## Output Formats

### Text (default)

Summary statistics, significance breakdown, and detailed changes with context lines.

### JSON

Structured output for programmatic processing:

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
      "significance": "high"
    }
  ]
}
```

### Unified diff

Standard unified diff format, compatible with `patch` and code review tools.

---

## Comparison with Similar Tools

| Feature | **Wayback-Diff** | [htmldiff](https://github.com/ian-ross/htmldiff) | [diff2html](https://github.com/rtfpessoa/diff2html) | [BackstopJS](https://github.com/garris/BackstopJS) | [Percy](https://percy.io) |
|---------|:-:|:-:|:-:|:-:|:-:|
| HTML-aware semantic diff | Yes | Yes | No | No | No |
| Wayback Machine artifact cleaning | **Yes** | No | No | No | No |
| Significance scoring | **Yes** | No | No | No | No |
| Visual (screenshot) comparison | Yes | No | No | Yes | Yes |
| Multi-browser support | Yes | N/A | N/A | Yes | Yes |
| Site-wide crawl and compare | Yes | No | No | Yes | No |
| Markdown report generation | Yes | No | No | No | No |
| CI/CD exit codes | Yes | No | No | Yes | Yes |
| Self-hosted / no SaaS | Yes | Yes | Yes | Yes | No |
| Free and open source | GPL-3.0 | MIT | MIT | MIT | Freemium |

---

## Testing

```bash
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=wayback_diff --cov-report=html
```

---

## Contributing

Contributions are welcome. To get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Add tests for new functionality
4. Ensure all tests pass: `pytest tests/ -v`
5. Submit a Pull Request

---

## Related Web Archiving Tools

- [Wayback-Archive](https://github.com/GeiserX/Wayback-Archive) — Download complete websites from the Wayback Machine
- [Way-CMS](https://github.com/GeiserX/Way-CMS) — Simple web CMS for editing archived HTML/CSS files
- [web-mirror](https://github.com/GeiserX/web-mirror) — Mirror any webpage for offline access
- [media-download](https://github.com/GeiserX/media-download) — Download all media files from any web page

## License

This project is licensed under the **GNU General Public License v3.0** (GPL-3.0). See the [LICENSE](LICENSE) file for details.

This software is **not** intended for commercial use.
