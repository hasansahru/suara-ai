"""
prompt_loader.py

Bertanggung jawab untuk memuat dan menggabungkan modul-modul prompt (.md)
secara berurutan sesuai arsitektur:

    system_prompt -> video_intelligence -> audience_psychology
    -> youtube_growth -> content_strategist -> channel (dipilih user)
    -> thumbnail_prompt -> seo_prompt -> output_format

Hanya channel yang dipilih pengguna yang dimuat agar AI tetap fokus.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")
SETTINGS_DIR = os.path.join(BASE_DIR, "settings")

# Urutan modul prompt umum (tanpa channel), sesuai spesifikasi project.
CORE_PROMPT_SEQUENCE_PRE_CHANNEL = [
    "system_prompt.md",
    "video_intelligence.md",
    "audience_psychology.md",
    "youtube_growth.md",
    "content_strategist.md",
]

CORE_PROMPT_SEQUENCE_POST_CHANNEL = [
    "thumbnail_prompt.md",
    "seo_prompt.md",
    "output_format.md",
]


class PromptLoadError(Exception):
    """Dilempar saat sebuah file prompt tidak ditemukan atau gagal dibaca."""


def _read_file(path: str) -> str:
    if not os.path.isfile(path):
        raise PromptLoadError(f"File prompt tidak ditemukan: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


@lru_cache(maxsize=1)
def load_channel_setting() -> dict:
    """Memuat settings/channel_setting.json (di-cache karena jarang berubah saat runtime)."""
    path = os.path.join(SETTINGS_DIR, "channel_setting.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_available_channels() -> List[dict]:
    """Mengembalikan daftar channel yang tersedia dari channel_setting.json."""
    data = load_channel_setting()
    return data.get("channels", [])


def get_channel_by_id(channel_id: str) -> dict:
    for ch in get_available_channels():
        if ch["id"] == channel_id:
            return ch
    raise PromptLoadError(f"Channel dengan id '{channel_id}' tidak ditemukan di channel_setting.json")


def load_prompt_file(relative_path: str) -> str:
    """Memuat satu file prompt berdasarkan path relatif terhadap folder prompts/."""
    full_path = os.path.join(PROMPTS_DIR, relative_path)
    return _read_file(full_path)


def build_system_prompt(channel_id: str) -> str:
    """
    Menggabungkan seluruh modul prompt secara berurutan menjadi satu system prompt,
    dengan HANYA memuat file channel yang dipilih pengguna.

    Args:
        channel_id: id channel, contoh: "suara_filsuf", "nalar_senyap", "tutur_kyai"

    Returns:
        String system prompt gabungan, siap dikirim ke Anthropic API sebagai `system`.
    """
    channel = get_channel_by_id(channel_id)

    sections: List[str] = []

    for filename in CORE_PROMPT_SEQUENCE_PRE_CHANNEL:
        sections.append(load_prompt_file(filename))

    # Muat HANYA DNA channel yang dipilih, jangan muat channel lain.
    sections.append(load_prompt_file(channel["file"]))

    for filename in CORE_PROMPT_SEQUENCE_POST_CHANNEL:
        sections.append(load_prompt_file(filename))

    separator = "\n\n---\n\n"
    return separator.join(sections)


def get_prompt_module_names(channel_id: str) -> List[str]:
    """Daftar nama modul (untuk ditampilkan di progress bar UI)."""
    channel = get_channel_by_id(channel_id)
    names = [
        "System Prompt",
        "Video Intelligence",
        "Audience Psychology",
        "YouTube Growth",
        "Content Strategist",
        f"Channel DNA: {channel['name']}",
        "Thumbnail Prompt",
        "SEO Prompt",
        "Output Format",
    ]
    return names
