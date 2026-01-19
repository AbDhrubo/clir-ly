"""
Text cleaning utilities for article preprocessing.

Handles:
- Boilerplate/footer removal (source-specific)
- Whitespace normalization
- Date standardization
- Header/footer stripping
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


# Source-specific boilerplate patterns to remove
BOILERPLATE_PATTERNS = {
    'newage': [
        r'Editor:\s*Nurul Kabir.*?Email:\[email protected\]',
        r'Editor:\s*Nurul Kabir.*$',
        r'For Advertisement.*?Email:\[email protected\]',
    ],
    'daily_star': [
        r'Copyright\s*©.*?Daily Star',
        r'The Daily Star\s*©.*$',
    ],
    'dhaka_tribune': [
        r'©\s*\d{4}\s*Dhaka Tribune.*$',
        r'Published by.*?Dhaka Tribune.*$',
    ],
    'daily_sun': [
        r'©\s*Daily Sun.*$',
        r'Published by.*?Daily Sun.*$',
    ],
    'new_nation': [
        r'©\s*The New Nation.*$',
    ],
    'prothomalo': [
        r'©\s*প্রথম আলো.*$',
        r'সর্বস্বত্ব সংরক্ষিত.*$',
    ],
    'bangla_tribune': [
        r'©\s*বাংলা ট্রিবিউন.*$',
    ],
    'dhaka_post': [
        r'©\s*ঢাকা পোস্ট.*$',
    ],
    'bdnews24': [
        r'©\s*bdnews24\.com.*$',
    ],
    'kaler_kantho': [
        r'©\s*কালের কণ্ঠ.*$',
    ],
}

# Common patterns across all sources
COMMON_BOILERPLATE = [
    r'\[email\s*protected\]',
    r'\s*Email:\s*\S+@\S+',
    r'\s*Cell:\s*\+?\d[\d\s-]+',
    r'Advertisement\s*$',
    r'Also Read:.*$',
    r'READ MORE:.*$',
    r'Related Articles?:.*$',
]


class TextCleaner:
    """Text cleaning utility for article content."""
    
    def __init__(self):
        # Compile common patterns once
        self.common_patterns = [re.compile(p, re.IGNORECASE | re.MULTILINE) 
                                for p in COMMON_BOILERPLATE]
        
        # Compile source-specific patterns
        self.source_patterns = {}
        for source, patterns in BOILERPLATE_PATTERNS.items():
            self.source_patterns[source] = [
                re.compile(p, re.IGNORECASE | re.MULTILINE | re.DOTALL) 
                for p in patterns
            ]
    
    def clean_text(self, text: str, source: Optional[str] = None) -> str:
        """
        Clean article text by removing boilerplate and normalizing whitespace.
        
        Args:
            text: Raw article text
            source: Source identifier for source-specific cleaning
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove source-specific boilerplate
        if source and source in self.source_patterns:
            for pattern in self.source_patterns[source]:
                text = pattern.sub('', text)
        
        # Remove common boilerplate
        for pattern in self.common_patterns:
            text = pattern.sub('', text)
        
        # Normalize whitespace
        text = self.normalize_whitespace(text)
        
        return text.strip()
    
    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Replace tabs with spaces
        text = text.replace('\t', ' ')
        
        # Replace multiple spaces with single space
        text = re.sub(r' {2,}', ' ', text)
        
        # Clean up spaces around newlines
        text = re.sub(r' *\n *', '\n', text)
        
        # Remove carriage returns
        text = text.replace('\r', '')
        
        return text
    
    def clean_title(self, title: str) -> str:
        """Clean article title."""
        if not title:
            return ""
        
        # Remove leading/trailing whitespace
        title = title.strip()
        
        # Normalize whitespace
        title = re.sub(r'\s+', ' ', title)
        
        # Remove common prefixes/suffixes
        title = re.sub(r'^(BREAKING|UPDATE|EXCLUSIVE):\s*', '', title, flags=re.IGNORECASE)
        
        return title
    
    def normalize_date(self, date_str: str) -> Optional[str]:
        """
        Normalize date to YYYY-MM-DD format.
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Normalized date string or None if parsing fails
        """
        if not date_str:
            return None
        
        # Try various date formats
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%Y/%m/%d',
        ]
        
        # Handle timezone suffix like +06:00
        date_clean = date_str.strip()
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_clean, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Try extracting just the date part if it has timezone
        if 'T' in date_clean:
            date_part = date_clean.split('T')[0]
            try:
                dt = datetime.strptime(date_part, '%Y-%m-%d')
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                pass
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def count_tokens(self, text: str) -> int:
        """
        Count approximate tokens in text.
        Simple whitespace-based tokenization.
        """
        if not text:
            return 0
        return len(text.split())


def clean_article(article: Dict[str, Any], cleaner: Optional[TextCleaner] = None) -> Dict[str, Any]:
    """
    Clean a single article dictionary.
    
    Args:
        article: Raw article dictionary
        cleaner: TextCleaner instance (creates new one if not provided)
        
    Returns:
        Cleaned article dictionary
    """
    if cleaner is None:
        cleaner = TextCleaner()
    
    source = article.get('source', '')
    
    # Create cleaned copy
    cleaned = article.copy()
    
    # Clean title
    if 'title' in cleaned:
        cleaned['title'] = cleaner.clean_title(cleaned['title'])
    
    # Clean body
    if 'body' in cleaned:
        cleaned['body'] = cleaner.clean_text(cleaned['body'], source)
    
    # Normalize date
    if 'date' in cleaned:
        normalized_date = cleaner.normalize_date(cleaned['date'])
        if normalized_date:
            cleaned['date'] = normalized_date
    
    # Recalculate tokens
    if 'body' in cleaned:
        cleaned['tokens'] = cleaner.count_tokens(cleaned['body'])
    
    # Add cleaned flag
    cleaned['cleaned'] = True
    
    return cleaned
