"""Query processing module for CLIR-ly."""

from .detector import detect_language
from .translator import translate_query
from .processor import process_query

__all__ = ["detect_language", "translate_query", "process_query"]
