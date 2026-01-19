"""
Data models for crawled articles.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime
import json
import re


@dataclass
class Article:
    """
    Represents a crawled news article with required CLIR metadata.
    
    Required fields (per assignment):
    - title: Article headline
    - body: Full article text
    - url: Source URL (unique identifier)
    - date: Publication date
    - language: 'en' for English, 'bn' for Bangla
    
    Recommended fields:
    - tokens: Word count
    - named_entities: Extracted NEs (optional, populated later)
    """
    # Required fields
    url: str
    title: str
    body: str
    date: Optional[str]  # ISO format when available
    language: str  # 'en' or 'bn'
    
    # Source metadata
    source: str  # 'thedailystar' or 'prothomalo'
    category: str
    
    # Recommended fields
    tokens: int = 0  # Word/token count
    
    # Optional fields (can be populated later)
    named_entities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Crawl metadata
    crawled_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def __post_init__(self):
        """Calculate token count if not provided."""
        if self.tokens == 0 and self.body:
            # Simple tokenization by whitespace
            # For Bangla, this is approximate but sufficient for counting
            self.tokens = len(self.body.split())
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        """Create Article from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Article":
        """Create Article from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def clean_body(self) -> str:
        """Return cleaned body text (remove extra whitespace)."""
        if not self.body:
            return ""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', self.body)
        return text.strip()
    
    def is_valid(self) -> bool:
        """Check if article has minimum required fields."""
        return bool(
            self.url and 
            self.title and 
            self.body and 
            len(self.body) > 100  # Minimum content length
        )
    
    def __hash__(self):
        """Hash by URL for deduplication."""
        return hash(self.url)
    
    def __eq__(self, other):
        """Equality by URL."""
        if isinstance(other, Article):
            return self.url == other.url
        return False
