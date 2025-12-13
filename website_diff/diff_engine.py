"""Intelligent diff engine for comparing web pages."""

import re
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher, unified_diff
from html.parser import HTMLParser
from collections import defaultdict


class HTMLStructureParser(HTMLParser):
    """Parser to extract HTML structure and meaningful content."""
    
    def __init__(self):
        super().__init__()
        self.structure = []
        self.text_content = []
        self.current_tag = None
        self.current_attrs = {}
        self.depth = 0
        
    def handle_starttag(self, tag, attrs):
        self.depth += 1
        self.current_tag = tag
        self.current_attrs = dict(attrs)
        
        # Store important structural elements
        if tag in ['div', 'section', 'article', 'header', 'footer', 'nav', 'main', 
                   'aside', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a', 'img',
                   'script', 'style', 'link', 'meta', 'title']:
            self.structure.append({
                'type': 'start',
                'tag': tag,
                'attrs': self.current_attrs,
                'depth': self.depth
            })
    
    def handle_endtag(self, tag):
        if self.current_tag == tag:
            self.structure.append({
                'type': 'end',
                'tag': tag,
                'depth': self.depth
            })
        self.depth -= 1
        self.current_tag = None
    
    def handle_data(self, data):
        # Store non-whitespace text content
        text = data.strip()
        if text:
            self.text_content.append(text)


class DiffEngine:
    """Intelligent diff engine for web page comparison."""
    
    # Patterns to ignore in comparison (timestamps, IDs, etc.)
    IGNORE_PATTERNS = [
        r'id="[^"]*"',
        r'class="[^"]*"',
        r'data-[^=]*="[^"]*"',
        r'timestamp[^>]*>.*?</[^>]*>',
        r'<!--.*?-->',  # Comments
    ]
    
    # Attributes that often change but aren't meaningful
    IGNORE_ATTRIBUTES = [
        'data-timestamp',
        'data-id',
        'data-random',
        'aria-label',  # Sometimes auto-generated
    ]
    
    def __init__(self, ignore_whitespace: bool = True, ignore_case: bool = False):
        """Initialize diff engine.
        
        Args:
            ignore_whitespace: Ignore whitespace differences
            ignore_case: Ignore case differences
        """
        self.ignore_whitespace = ignore_whitespace
        self.ignore_case = ignore_case
    
    def normalize_content(self, content: bytes) -> bytes:
        """Normalize content for comparison."""
        if self.ignore_whitespace:
            # Normalize whitespace
            content = re.sub(rb'\s+', rb' ', content)
            content = re.sub(rb'>\s+<', rb'><', content)
        
        if self.ignore_case:
            content = content.lower()
        
        return content
    
    def extract_meaningful_changes(self, old_content: bytes, new_content: bytes) -> List[Dict]:
        """Extract meaningful changes between two HTML contents.
        
        Returns a list of change dictionaries with:
        - type: 'added', 'removed', 'modified'
        - old_text: Original text (if applicable)
        - new_text: New text (if applicable)
        - context: Surrounding context
        - significance: 'high', 'medium', 'low'
        """
        changes = []
        
        # Normalize content
        old_normalized = self.normalize_content(old_content)
        new_normalized = self.normalize_content(new_content)
        
        # Use SequenceMatcher for intelligent diff
        matcher = SequenceMatcher(
            isjunk=None,
            a=old_normalized,
            b=new_normalized,
            autojunk=False
        )
        
        # Context window for changes
        context_size = 200
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
            
            # Extract the actual change
            old_chunk = old_content[i1:i2] if i1 < len(old_content) and i2 <= len(old_content) else b''
            new_chunk = new_content[j1:j2] if j1 < len(new_content) and j2 <= len(new_content) else b''
            
            # Get context
            context_start = max(0, i1 - context_size)
            context_end = min(len(old_content), i2 + context_size)
            old_context = old_content[context_start:context_end]
            
            context_start = max(0, j1 - context_size)
            context_end = min(len(new_content), j2 + context_size)
            new_context = new_content[context_start:context_end]
            
            # Determine significance
            significance = self._assess_significance(old_chunk, new_chunk)
            
            # Determine change type
            if tag == 'delete':
                change_type = 'removed'
            elif tag == 'insert':
                change_type = 'added'
            else:
                change_type = 'modified'
            
            changes.append({
                'type': change_type,
                'old_text': old_chunk.decode('utf-8', errors='replace'),
                'new_text': new_chunk.decode('utf-8', errors='replace'),
                'old_context': old_context.decode('utf-8', errors='replace'),
                'new_context': new_context.decode('utf-8', errors='replace'),
                'significance': significance,
                'old_position': (i1, i2),
                'new_position': (j1, j2),
            })
        
        return changes
    
    def _assess_significance(self, old_chunk: bytes, new_chunk: bytes) -> str:
        """Assess the significance of a change.
        
        Returns 'high', 'medium', or 'low'.
        """
        old_str = old_chunk.decode('utf-8', errors='replace').lower()
        new_str = new_chunk.decode('utf-8', errors='replace').lower()
        
        # High significance: structural changes, content changes
        high_significance_patterns = [
            r'<h[1-6]',
            r'<title',
            r'<meta\s+name=["\'](description|keywords|og:)',
            r'<script\s+src=',
            r'<link\s+rel=["\']stylesheet',
            r'<body',
            r'<main',
            r'<article',
            r'<section',
        ]
        
        for pattern in high_significance_patterns:
            if re.search(pattern, old_str) or re.search(pattern, new_str):
                return 'high'
        
        # Medium significance: attributes, styling
        medium_significance_patterns = [
            r'class=',
            r'style=',
            r'id=',
            r'<div',
            r'<span',
        ]
        
        for pattern in medium_significance_patterns:
            if re.search(pattern, old_str) or re.search(pattern, new_str):
                return 'medium'
        
        # Low significance: whitespace, comments, minor formatting
        return 'low'
    
    def generate_unified_diff(self, old_content: bytes, new_content: bytes, 
                              old_label: str = "old", new_label: str = "new",
                              n: int = 3) -> List[str]:
        """Generate unified diff format output.
        
        Args:
            old_content: Original content
            new_content: New content
            old_label: Label for old file
            new_label: Label for new file
            n: Number of context lines
            
        Returns:
            List of diff lines
        """
        old_lines = old_content.decode('utf-8', errors='replace').splitlines(keepends=True)
        new_lines = new_content.decode('utf-8', errors='replace').splitlines(keepends=True)
        
        diff = unified_diff(
            old_lines,
            new_lines,
            fromfile=old_label,
            tofile=new_label,
            lineterm='',
            n=n
        )
        
        return list(diff)
    
    def compare_structures(self, old_html: bytes, new_html: bytes) -> Dict:
        """Compare HTML structures to identify structural differences.
        
        Returns a dictionary with structural comparison results.
        """
        old_parser = HTMLStructureParser()
        new_parser = HTMLStructureParser()
        
        try:
            old_parser.feed(old_html.decode('utf-8', errors='replace'))
            new_parser.feed(new_html.decode('utf-8', errors='replace'))
        except Exception:
            # If parsing fails, return basic comparison
            return {
                'structural_changes': [],
                'old_structure': [],
                'new_structure': [],
                'similarity': 0.0
            }
        
        # Compare structures
        old_structure = old_parser.structure
        new_structure = new_parser.structure
        
        # Calculate similarity
        matcher = SequenceMatcher(None, old_structure, new_structure)
        similarity = matcher.ratio()
        
        # Find structural differences
        structural_changes = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != 'equal':
                structural_changes.append({
                    'type': tag,
                    'old_elements': old_structure[i1:i2] if i1 < len(old_structure) else [],
                    'new_elements': new_structure[j1:j2] if j1 < len(new_structure) else [],
                })
        
        return {
            'structural_changes': structural_changes,
            'old_structure': old_structure,
            'new_structure': new_structure,
            'similarity': similarity
        }
    
    def get_summary(self, changes: List[Dict]) -> Dict:
        """Generate a summary of changes.
        
        Returns statistics about the changes.
        """
        summary = {
            'total_changes': len(changes),
            'added': sum(1 for c in changes if c['type'] == 'added'),
            'removed': sum(1 for c in changes if c['type'] == 'removed'),
            'modified': sum(1 for c in changes if c['type'] == 'modified'),
            'high_significance': sum(1 for c in changes if c['significance'] == 'high'),
            'medium_significance': sum(1 for c in changes if c['significance'] == 'medium'),
            'low_significance': sum(1 for c in changes if c['significance'] == 'low'),
        }
        
        return summary
