"""Tests for CLI."""

import pytest
import sys
from unittest.mock import patch, Mock
from wayback_diff.cli import format_output


class TestCLI:
    """Test cases for CLI."""
    
    def test_format_output_text(self):
        """Test text output formatting."""
        summary = {
            'total_changes': 5,
            'added': 2,
            'removed': 1,
            'modified': 2,
            'high_significance': 1,
            'medium_significance': 2,
            'low_significance': 2,
        }
        
        changes = [
            {
                'type': 'modified',
                'old_text': 'Old',
                'new_text': 'New',
                'significance': 'high'
            }
        ]
        
        output = format_output(changes, summary, 'text')
        
        assert 'WAYBACK DIFF SUMMARY' in output
        assert 'Total changes: 5' in output
        assert 'HIGH SIGNIFICANCE CHANGES' in output
    
    def test_format_output_json(self):
        """Test JSON output formatting."""
        summary = {
            'total_changes': 1,
            'added': 0,
            'removed': 0,
            'modified': 1,
            'high_significance': 1,
            'medium_significance': 0,
            'low_significance': 0,
        }
        
        changes = [
            {
                'type': 'modified',
                'old_text': 'Old',
                'new_text': 'New',
                'significance': 'high'
            }
        ]
        
        output = format_output(changes, summary, 'json')
        
        import json
        data = json.loads(output)
        assert 'summary' in data
        assert 'changes' in data
        assert data['summary']['total_changes'] == 1
