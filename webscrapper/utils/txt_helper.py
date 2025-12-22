import re
from typing import Optional

def clean_text(text: str, normalize_quotes: bool = True) -> str:
    """
    Clean and normalize text by removing excessive whitespace, normalizing quotes,
    and performing common cleanup operations.

    Args:
        text: Input string to clean
        normalize_quotes: Whether to convert all quotation marks to single quotes (default: True)

    Returns:
        Cleaned and normalized string
    """
    if not isinstance(text, str):
        return ""

    if not text.strip():
        return ""

    # 1. Replace all types of whitespace (including non-breaking spaces, tabs, newlines) with single space
    text = re.sub(r'\s+', ' ', text)

    # 2. Normalize different types of quotation marks (optional)
    if normalize_quotes:
        text = text.replace('"', "'").replace('“', "'").replace('”', "'").replace('‘', "'").replace('’', "'")

    # 3. Remove zero-width spaces, byte order marks, and other invisible chars
    text = re.sub(r'[\u200B\u200C\u200D\uFEFF\u2028\u2029]', '', text)

    # 4. Remove leading/trailing whitespace (again, just to be sure)
    text = text.strip()

    # 5. Optional: collapse multiple spaces again (in case normalization created them)
    text = re.sub(r' +', ' ', text)

    return text