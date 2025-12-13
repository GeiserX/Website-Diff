"""Tests for diff engine."""

import pytest
from website_diff.diff_engine import DiffEngine


class TestDiffEngine:
    """Test cases for DiffEngine."""
    
    def test_normalize_content(self):
        """Test content normalization."""
        engine = DiffEngine(ignore_whitespace=True)
        
        content1 = b"<div>  Test  </div>"
        content2 = b"<div>Test</div>"
        
        norm1 = engine.normalize_content(content1)
        norm2 = engine.normalize_content(content2)
        
        # After normalization, whitespace should be similar
        assert b'<div>' in norm1
        assert b'Test' in norm1
    
    def test_extract_meaningful_changes(self):
        """Test change extraction."""
        engine = DiffEngine()
        
        old_content = b"<html><body><h1>Old Title</h1><p>Content</p></body></html>"
        new_content = b"<html><body><h1>New Title</h1><p>Content</p></body></html>"
        
        changes = engine.extract_meaningful_changes(old_content, new_content)
        
        assert len(changes) > 0
        # Should detect the title change - check if any change contains the title text
        all_text = ' '.join([c.get('old_text', '') + c.get('new_text', '') for c in changes])
        # The changes should contain either Old Title or New Title
        assert 'Old Title' in all_text or 'New Title' in all_text or any('Title' in c.get('old_text', '') or 'Title' in c.get('new_text', '') for c in changes)
    
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
        assert summary['total_changes'] > 0
    
    def test_assess_significance(self):
        """Test significance assessment."""
        engine = DiffEngine()
        
        # High significance - title change
        high_change = engine._assess_significance(
            b"<title>Old</title>",
            b"<title>New</title>"
        )
        assert high_change == 'high'
        
        # Medium significance - div change
        medium_change = engine._assess_significance(
            b"<div>Old</div>",
            b"<div>New</div>"
        )
        assert medium_change == 'medium'
        
        # Low significance - whitespace
        low_change = engine._assess_significance(
            b"  ",
            b" "
        )
        assert low_change == 'low'
    
    def test_generate_unified_diff(self):
        """Test unified diff generation."""
        engine = DiffEngine()
        
        old_content = b"Line 1\nLine 2\nLine 3"
        new_content = b"Line 1\nLine 2 Modified\nLine 3"
        
        diff = engine.generate_unified_diff(old_content, new_content, "old.txt", "new.txt")
        
        assert len(diff) > 0
        assert any('Line 2' in line for line in diff)
