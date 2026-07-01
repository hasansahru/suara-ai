from __future__ import annotations
from pathlib import Path

ALLOWED_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".srt", ".vtt"}
MAX_FILE_SIZE_MB = 10

def validate_upload(uploaded_file) -> tuple[bool, str]:
    if uploaded_file is None:
        return False, "Tidak ada file yang diupload"
    ext = Path(uploaded_file.name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Tipe file tidak didukung: {ext}"
    content = uploaded_file.read()
    uploaded_file.seek(0)
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        return False, f"File terlalu besar. Maks: {MAX_FILE_SIZE_MB}MB"
    return True, "OK"

def safe_read_file(uploaded_file) -> str | None:
    try:
        content = uploaded_file.read()
        uploaded_file.seek(0)
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1")
    except Exception:
        return None