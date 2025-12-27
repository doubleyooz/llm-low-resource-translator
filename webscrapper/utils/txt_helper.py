import os
import re
from typing import Optional


def get_last_directory_alphabetic(folder_path):
    """
    Returns the name of the last subdirectory in the given folder_path
    when sorted alphabetically. Returns None if the path is not a directory
    or if there are no subdirectories.
    
    Parameters:
        folder_path (str): The path to the folder to scan.
    
    Returns:
        str or None: The name of the last subdirectory, or None if none found.
    """
    # Check if the path exists and is a directory
    if not os.path.isdir(folder_path):
        return None
    
    # Get all entries in the directory
    entries = os.listdir(folder_path)
    
    # Filter only directories (subdirectories)
    subdirs = [
        entry for entry in entries
        if os.path.isdir(os.path.join(folder_path, entry))
    ]
    
    # If no subdirectories, return None
    if not subdirs:
        return None
    
    # Sort alphabetically (case-sensitive: A-Z before a-z)
    subdirs.sort()
    
    # Return the last one
    return subdirs[-2]

def sanitize_txt(text: str, max_length: int = 80) -> str:
    """
    Very conservative sanitization - only allows alphanumeric, underscore, hyphen, and dot.
    """
    if not text:
        return "unnamed"
    
    # Only keep safe characters
    sanitized = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', text)
    
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # Remove leading/trailing dots and dashes
    sanitized = sanitized.strip('.-_')
    
    # Ensure not empty
    if not sanitized:
        return "unnamed"
    
    # Truncate
    if len(sanitized) > max_length:
        name, ext = os.path.splitext(sanitized)
        if len(ext) > 0 and len(ext) <= 10:  # Reasonable extension length
            return name[:max_length - len(ext)] + ext
        return sanitized[:max_length]
    
    return sanitized

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
    if text[0] == '[' and text[-1] == ']':
        text = text[1:-1].strip()   
    text = text.strip()

    # 5. Optional: collapse multiple spaces again (in case normalization created them)
    text = re.sub(r' +', ' ', text)

    return text