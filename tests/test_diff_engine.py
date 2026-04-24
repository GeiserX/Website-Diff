"""Tests for diff engine."""

import pytest
from wayback_diff.diff_engine import DiffEngine, HTMLStructureParser


class TestHTMLStructureParser:
    """Test cases for HTMLStructureParser."""

    def test_parse_basic_html(self):
        """Test parsing basic HTML structure."""
        parser = HTMLStructureParser()
        parser.feed("<html><body><h1>Title</h1><p>Text</p></body></html>")

        assert len(parser.structure) > 0
        tags = [s['tag'] for s in parser.structure if s['type'] == 'start']
        assert 'h1' in tags
        assert 'p' in tags

    def test_parse_text_content(self):
        """Test extracting text content."""
        parser = HTMLStructureParser()
        parser.feed("<div><p>Hello World</p></div>")

        assert 'Hello World' in parser.text_content

    def test_parse_ignores_whitespace_text(self):
        """Test that whitespace-only text is ignored."""
        parser = HTMLStructureParser()
        parser.feed("<div>   </div><p>Real text</p>")

        assert 'Real text' in parser.text_content
        assert '   ' not in parser.text_content

    def test_parse_attributes(self):
        """Test parsing element attributes."""
        parser = HTMLStructureParser()
        parser.feed('<a href="https://example.com">Link</a>')

        start_tags = [s for s in parser.structure if s['type'] == 'start' and s['tag'] == 'a']
        assert len(start_tags) == 1
        assert start_tags[0]['attrs']['href'] == 'https://example.com'

    def test_parse_depth_tracking(self):
        """Test depth tracking."""
        parser = HTMLStructureParser()
        parser.feed("<div><section><p>Deep</p></section></div>")

        start_tags = [s for s in parser.structure if s['type'] == 'start']
        depths = [s['depth'] for s in start_tags]
        assert len(depths) >= 2
        # Deeper elements should have higher depth
        assert max(depths) >= 2

    def test_parse_important_tags(self):
        """Test that important tags are captured."""
        important_tags = ['div', 'section', 'article', 'header', 'footer',
                          'nav', 'main', 'aside', 'h1', 'h2', 'h3', 'h4',
                          'h5', 'h6', 'p', 'a', 'img', 'script', 'style',
                          'link', 'meta', 'title']
        for tag in important_tags:
            parser = HTMLStructureParser()
            if tag in ('img', 'link', 'meta'):
                parser.feed(f'<{tag} src="x">')
            else:
                parser.feed(f'<{tag}>content</{tag}>')
            start_tags = [s['tag'] for s in parser.structure if s['type'] == 'start']
            assert tag in start_tags, f"Tag {tag} should be captured"

    def test_parse_non_important_tags_ignored(self):
        """Test that non-important tags are not captured in structure."""
        parser = HTMLStructureParser()
        parser.feed("<span>text</span><b>bold</b><em>emphasis</em>")

        start_tags = [s['tag'] for s in parser.structure if s['type'] == 'start']
        assert 'span' not in start_tags
        assert 'b' not in start_tags
        assert 'em' not in start_tags

    def test_parse_end_tags(self):
        """Test end tag handling."""
        parser = HTMLStructureParser()
        parser.feed("<h1>Title</h1>")

        end_tags = [s for s in parser.structure if s['type'] == 'end']
        assert len(end_tags) >= 1
        assert end_tags[0]['tag'] == 'h1'

    def test_parse_nested_text(self):
        """Test multiple text nodes."""
        parser = HTMLStructureParser()
        parser.feed("<div>First</div><p>Second</p>")

        assert 'First' in parser.text_content
        assert 'Second' in parser.text_content


class TestDiffEngine:
    """Test cases for DiffEngine."""

    def test_init_defaults(self):
        """Test default initialization."""
        engine = DiffEngine()
        assert engine.ignore_whitespace is True
        assert engine.ignore_case is False

    def test_init_custom(self):
        """Test custom initialization."""
        engine = DiffEngine(ignore_whitespace=False, ignore_case=True)
        assert engine.ignore_whitespace is False
        assert engine.ignore_case is True

    def test_normalize_content_whitespace(self):
        """Test content normalization with whitespace."""
        engine = DiffEngine(ignore_whitespace=True)

        content1 = b"<div>  Test  </div>"
        content2 = b"<div>Test</div>"

        norm1 = engine.normalize_content(content1)
        norm2 = engine.normalize_content(content2)

        assert b'<div>' in norm1
        assert b'Test' in norm1

    def test_normalize_content_no_whitespace(self):
        """Test normalization with whitespace handling disabled."""
        engine = DiffEngine(ignore_whitespace=False)
        content = b"<div>  Test  </div>"
        normalized = engine.normalize_content(content)
        assert b'  Test  ' in normalized

    def test_normalize_content_case(self):
        """Test case normalization."""
        engine = DiffEngine(ignore_case=True)
        content = b"<DIV>Test</DIV>"
        normalized = engine.normalize_content(content)
        assert b'<div>' in normalized
        assert b'test' in normalized

    def test_normalize_content_tag_whitespace(self):
        """Test whitespace between tags is normalized."""
        engine = DiffEngine(ignore_whitespace=True)
        content = b"<div>  \n  </div>  <p>Text</p>"
        normalized = engine.normalize_content(content)
        assert b'><' in normalized or b'> <' in normalized

    def test_extract_meaningful_changes(self):
        """Test change extraction."""
        engine = DiffEngine()

        old_content = b"<html><body><h1>Old Title</h1><p>Content</p></body></html>"
        new_content = b"<html><body><h1>New Title</h1><p>Content</p></body></html>"

        changes = engine.extract_meaningful_changes(old_content, new_content)

        assert len(changes) > 0
        all_text = ' '.join([c.get('old_text', '') + c.get('new_text', '') for c in changes])
        all_context = ' '.join([c.get('old_context', '') + c.get('new_context', '') for c in changes])
        assert ('Old' in all_text and 'New' in all_text) or 'Title' in all_context

    def test_extract_meaningful_changes_identical(self):
        """Test no changes for identical content."""
        engine = DiffEngine()
        content = b"<html><body><p>Same content</p></body></html>"
        changes = engine.extract_meaningful_changes(content, content)
        assert len(changes) == 0

    def test_extract_meaningful_changes_added(self):
        """Test detecting added content."""
        engine = DiffEngine()
        old = b"<html><body></body></html>"
        new = b"<html><body><p>New paragraph</p></body></html>"
        changes = engine.extract_meaningful_changes(old, new)
        assert len(changes) > 0
        types = [c['type'] for c in changes]
        assert 'added' in types or 'modified' in types

    def test_extract_meaningful_changes_removed(self):
        """Test detecting removed content."""
        engine = DiffEngine()
        old = b"<html><body><p>Old paragraph</p></body></html>"
        new = b"<html><body></body></html>"
        changes = engine.extract_meaningful_changes(old, new)
        assert len(changes) > 0
        types = [c['type'] for c in changes]
        assert 'removed' in types or 'modified' in types

    def test_extract_meaningful_changes_large_content(self):
        """Test autojunk for large content (> 100000 bytes)."""
        engine = DiffEngine()
        old = b"<html><body>" + b"<p>Content paragraph</p>\n" * 10000 + b"</body></html>"
        new = b"<html><body>" + b"<p>Content paragraph</p>\n" * 9999 + b"<p>Different</p></body></html>"
        changes = engine.extract_meaningful_changes(old, new)
        # Should complete without error
        assert isinstance(changes, list)

    def test_extract_meaningful_changes_has_positions(self):
        """Test that changes have position information."""
        engine = DiffEngine()
        old = b"<html>Old</html>"
        new = b"<html>New</html>"
        changes = engine.extract_meaningful_changes(old, new)
        assert len(changes) > 0
        for change in changes:
            assert 'old_position' in change
            assert 'new_position' in change
            assert 'old_context' in change
            assert 'new_context' in change

    def test_extract_meaningful_changes_has_significance(self):
        """Test that changes have significance levels."""
        engine = DiffEngine()
        old = b"<html><head><title>Old</title></head></html>"
        new = b"<html><head><title>New</title></head></html>"
        changes = engine.extract_meaningful_changes(old, new)
        for change in changes:
            assert change['significance'] in ('high', 'medium', 'low')

    def test_get_summary(self):
        """Test summary generation."""
        engine = DiffEngine()

        old_content = b"<html><body><h1>Old</h1></body></html>"
        new_content = b"<html><body><h1>New</h1><p>Added</p></body></html>"

        changes = engine.extract_meaningful_changes(old_content, new_content)
        summary = engine.get_summary(changes)

        assert 'total_changes' in summary
        assert 'added' in summary
        assert 'removed' in summary
        assert 'modified' in summary
        assert 'high_significance' in summary
        assert 'medium_significance' in summary
        assert 'low_significance' in summary
        assert summary['total_changes'] > 0

    def test_get_summary_empty(self):
        """Test summary for empty changes list."""
        engine = DiffEngine()
        summary = engine.get_summary([])
        assert summary['total_changes'] == 0
        assert summary['added'] == 0
        assert summary['removed'] == 0
        assert summary['modified'] == 0

    def test_assess_significance_high_title(self):
        """Test high significance for title changes."""
        engine = DiffEngine()
        result = engine._assess_significance(
            b"<title>Old</title>",
            b"<title>New</title>"
        )
        assert result == 'high'

    def test_assess_significance_high_heading(self):
        """Test high significance for heading changes."""
        engine = DiffEngine()
        for i in range(1, 7):
            result = engine._assess_significance(
                f"<h{i}>Old</h{i}>".encode(),
                f"<h{i}>New</h{i}>".encode()
            )
            assert result == 'high', f"h{i} should be high significance"

    def test_assess_significance_high_meta(self):
        """Test high significance for meta tag changes."""
        engine = DiffEngine()
        result = engine._assess_significance(
            b'<meta name="description" content="old">',
            b'<meta name="description" content="new">'
        )
        assert result == 'high'

    def test_assess_significance_high_script(self):
        """Test high significance for script changes."""
        engine = DiffEngine()
        result = engine._assess_significance(
            b'<script src="old.js"></script>',
            b'<script src="new.js"></script>'
        )
        assert result == 'high'

    def test_assess_significance_high_stylesheet(self):
        """Test high significance for stylesheet changes."""
        engine = DiffEngine()
        result = engine._assess_significance(
            b'<link rel="stylesheet" href="old.css">',
            b'<link rel="stylesheet" href="new.css">'
        )
        assert result == 'high'

    def test_assess_significance_high_body(self):
        """Test high significance for body tag changes."""
        engine = DiffEngine()
        result = engine._assess_significance(b'<body class="old">', b'<body class="new">')
        assert result == 'high'

    def test_assess_significance_high_main(self):
        """Test high significance for main/article/section changes."""
        engine = DiffEngine()
        for tag in ['main', 'article', 'section']:
            result = engine._assess_significance(
                f'<{tag}>old</{tag}>'.encode(),
                f'<{tag}>new</{tag}>'.encode()
            )
            assert result == 'high', f"{tag} should be high significance"

    def test_assess_significance_medium_class(self):
        """Test medium significance for class changes."""
        engine = DiffEngine()
        result = engine._assess_significance(
            b'class="old-style"',
            b'class="new-style"'
        )
        assert result == 'medium'

    def test_assess_significance_medium_div(self):
        """Test medium significance for div changes."""
        engine = DiffEngine()
        result = engine._assess_significance(
            b"<div>Old</div>",
            b"<div>New</div>"
        )
        assert result == 'medium'

    def test_assess_significance_medium_style(self):
        """Test medium significance for style attribute changes."""
        engine = DiffEngine()
        result = engine._assess_significance(
            b'style="color: red"',
            b'style="color: blue"'
        )
        assert result == 'medium'

    def test_assess_significance_medium_span(self):
        """Test medium significance for span changes."""
        engine = DiffEngine()
        result = engine._assess_significance(
            b'<span>old</span>',
            b'<span>new</span>'
        )
        assert result == 'medium'

    def test_assess_significance_medium_id(self):
        """Test medium significance for id changes."""
        engine = DiffEngine()
        result = engine._assess_significance(b'id="old"', b'id="new"')
        assert result == 'medium'

    def test_assess_significance_low(self):
        """Test low significance for whitespace/minor changes."""
        engine = DiffEngine()
        result = engine._assess_significance(b"  ", b" ")
        assert result == 'low'

    def test_assess_significance_low_plain_text(self):
        """Test low significance for plain text without structural markers."""
        engine = DiffEngine()
        result = engine._assess_significance(b"old text", b"new text")
        assert result == 'low'

    def test_generate_unified_diff(self):
        """Test unified diff generation."""
        engine = DiffEngine()

        old_content = b"Line 1\nLine 2\nLine 3"
        new_content = b"Line 1\nLine 2 Modified\nLine 3"

        diff = engine.generate_unified_diff(old_content, new_content, "old.txt", "new.txt")

        assert len(diff) > 0
        assert any('Line 2' in line for line in diff)

    def test_generate_unified_diff_identical(self):
        """Test unified diff for identical content."""
        engine = DiffEngine()
        content = b"Line 1\nLine 2\nLine 3"
        diff = engine.generate_unified_diff(content, content)
        assert len(diff) == 0

    def test_generate_unified_diff_custom_context(self):
        """Test unified diff with custom context lines."""
        engine = DiffEngine()
        old = b"A\nB\nC\nD\nE\nF\nG"
        new = b"A\nB\nC\nX\nE\nF\nG"
        diff = engine.generate_unified_diff(old, new, n=1)
        assert len(diff) > 0

    def test_generate_unified_diff_labels(self):
        """Test unified diff labels."""
        engine = DiffEngine()
        old = b"old line"
        new = b"new line"
        diff = engine.generate_unified_diff(old, new, old_label="file1.html", new_label="file2.html")
        joined = '\n'.join(diff)
        assert 'file1.html' in joined
        assert 'file2.html' in joined

    def test_compare_structures(self):
        """Test HTML structure comparison returns expected keys."""
        engine = DiffEngine()
        old = b"<html><body><h1>Title</h1><p>Text</p></body></html>"
        new = b"<html><body><h2>Title</h2><p>Text</p><div>New</div></body></html>"

        result = engine.compare_structures(old, new)

        assert 'structural_changes' in result
        assert 'old_structure' in result
        assert 'new_structure' in result
        assert 'similarity' in result
        assert 0.0 <= result['similarity'] <= 1.0
        # Different structures should have some changes
        assert len(result['structural_changes']) > 0

    def test_compare_structures_identical(self):
        """Test structure comparison for identical HTML."""
        engine = DiffEngine()
        html = b"<html><body><h1>Title</h1></body></html>"
        result = engine.compare_structures(html, html)
        assert result['similarity'] == 1.0
        assert len(result['structural_changes']) == 0

    def test_compare_structures_unicode(self):
        """Test structure comparison with unicode content."""
        engine = DiffEngine()
        old = '<html><body><p>Texto en espanol</p></body></html>'.encode('utf-8')
        new = '<html><body><p>Texto en ingles</p></body></html>'.encode('utf-8')
        result = engine.compare_structures(old, new)
        assert 'similarity' in result
        # Same structure, different text content (text is not in structure)
        assert result['similarity'] == 1.0

    def test_compare_structures_empty(self):
        """Test structure comparison with empty content."""
        engine = DiffEngine()
        result = engine.compare_structures(b"", b"")
        # Empty content produces no structure elements, so SequenceMatcher
        # works fine on empty lists
        assert 'similarity' in result
        assert isinstance(result['structural_changes'], list)

    def test_compare_structures_no_important_tags(self):
        """Test structure comparison with no important tags (empty structures)."""
        engine = DiffEngine()
        # span/b/em are not captured, so structures are empty lists
        old = b"<span>text1</span>"
        new = b"<span>text2</span>"
        result = engine.compare_structures(old, new)
        assert result['similarity'] == 1.0
        assert len(result['structural_changes']) == 0

    def test_compare_structures_returns_dict(self):
        """Test compare_structures always returns a dict."""
        engine = DiffEngine()
        result = engine.compare_structures(b"<p>a</p>", b"<p>b</p>")
        assert isinstance(result, dict)
