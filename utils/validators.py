from __future__ import annotations
import re

def validate_youtube_url(url: str) -> tuple[bool, str]:
    if not url or not url.strip():
        return False, "URL tidak boleh kosong"
    url = url.strip()
    patterns = [
        r'(?:youtube\.com/watch\?.*v=)([\w-]{11})',
        r'(?:youtu\.be/)([\w-]{11})',
        r'(?:youtube\.com/shorts/)([\w-]{11})',
        r'(?:youtube\.com/embed/)([\w-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return True, match.group(1)
    return False, "URL YouTube tidak valid"

def sanitize_text_input(text: str, max_length: int = 100_000) -> str:
    if not text:
        return ""
    return text.replace('\x00', '')[:max_length].strip()

def validate_api_key(api_key: str) -> bool:
    if not api_key:
        return False
    return len(api_key.strip()) >= 10