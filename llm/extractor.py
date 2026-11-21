"""Extracts clean Python code from raw LLM output (handles markdown)."""
from __future__ import annotations
import re

def extract_python_code(text: str) -> str:
    """Finds code inside ```python ... ``` or ``` ... ``` blocks."""
    # Look for ```python ... ```
    match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
        
    # Look for ``` ... ```
    match = re.search(r"```\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
        
    # If no markdown, assume the whole text is code
    return text.strip()
