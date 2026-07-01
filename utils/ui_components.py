"""
ui_components_enhanced.py — Modern UI Components
================================================
Reusable, professional UI elements for Suara AI.

Enhanced from ui_components.py with:
  ✓ Modern badge styling
  ✓ Professional score grid
  ✓ Interactive checklist
  ✓ Better step progress
  ✓ Copy-able blocks
"""

from __future__ import annotations
from typing import Any, Dict, Optional

import streamlit as st


def badge(text: str, color: str = "#3B82F6", variant: str = "filled") -> None:
    """
    Render badge pill with modern styling.

    Args:
        text: Badge text
        color: Color hex (primary blue default)
        variant: 'filled' or 'outline'
    """
    if variant == "outline":
        st.markdown(
            f"""
            <span style="
                background: transparent;
                color: {color};
                border: 1.5px solid {color};
                padding: 3px 12px;
                border-radius: 999px;
                font-size: 0.78rem;
                font-weight: 600;
                display: inline-block;
                margin: 2px 6px 2px 0;
            ">{text}</span>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <span style="
                background: {color}20;
                color: {color};
                border: 1px solid {color}40;
                padding: 3px 12px;
                border-radius: 999px;
                font-size: 0.78rem;
                font-weight: 600;
                display: inline-block;
                margin: 2px 6px 2px 0;
            ">{text}</span>
            """,
            unsafe_allow_html=True,
        )


def score_badge(score: Any, label: str) -> None:
    """Badge for score 1-10 with color coding."""
    try:
        numeric = float(score)
    except (TypeError, ValueError):
        numeric = 0.0

    if numeric >= 8:
        color = "#16A34A"  # Green
    elif numeric >= 6:
        color = "#2563EB"  # Blue
    elif numeric >= 5:
        color = "#DC2626"  # Orange/Red
    else:
        color = "#991B1B"  # Deep red

    badge(f"⭐ {label}: {score}/10", color)


def copy_block(content: str, language: Optional[str] = None) -> None:
    """
    Render content in code block for easy copy.

    Args:
        content: Text to display
        language: Syntax highlighting (default: None for plain text)
    """
    if language:
        st.code(content, language=language)
    else:
        st.code(content, language="text")


def render_score_grid(skor_growth: Dict[str, Any]) -> None:
    """
    Render score grid with modern cards and expander for explanations.

    Args:
        skor_growth: Dict with keys like 'ctr', 'retention', etc.
    """
    label_map = {
        "ctr": ("CTR", "📊 Click-through rate"),
        "retention": ("Retention", "👀 Penonton bertahan"),
        "watch_time": ("Watch Time", "⏱ Durasi tonton"),
        "seo": ("SEO", "🔍 Pencarian YouTube"),
        "viral_potential": ("Viral Potential", "🔥 Potensi viral"),
        "evergreen": ("Evergreen", "🌿 Konten jangka panjang"),
        "emotional_impact": ("Emotional Impact", "💡 Dampak emosi"),
    }

    cols = st.columns(3)

    for idx, (key, (label, description)) in enumerate(label_map.items()):
        item = skor_growth.get(key, {}) if isinstance(skor_growth, dict) else {}
        score = item.get("score", "-") if isinstance(item, dict) else "-"

        with cols[idx % 3]:
            with st.container(border=True):
                st.caption(f"{label} — {description}")
                try:
                    numeric = float(score)
                    if numeric >= 7:
                        st.success(f"**{score}/10**")
                    elif numeric >= 5:
                        st.warning(f"**{score}/10**")
                    else:
                        st.error(f"**{score}/10**")
                except:
                    st.info(f"**{score}/10**")

    with st.expander("📋 Alasan Skor (detail)"):
        for key, (label, description) in label_map.items():
            item = skor_growth.get(key, {}) if isinstance(skor_growth, dict) else {}
            if not isinstance(item, dict):
                continue
            st.markdown(f"**{label}** — {item.get('score', '-')}/10")
            st.info(item.get("alasan", "-"))


def render_checklist(checklist: list) -> None:
    """
    Render interactive checklist for pre-upload verification.

    Args:
        checklist: List of dicts with keys 'item', 'wajib', 'auto'
                   or simple strings
    """
    if not checklist:
        st.info("Tidak ada checklist.")
        return

    st.subheader("✅ Checklist")

    total = len(checklist)
    checked = 0

    for idx, item in enumerate(checklist):
        if isinstance(item, dict):
            label = item.get("item", "")
            wajib = item.get("wajib", True)
            is_auto = item.get("auto", False)
        else:
            label = str(item)
            wajib = True
            is_auto = False

        # Build display text
        suffix_parts = []
        if wajib:
            suffix_parts.append("🔴 WAJIB")
        else:
            suffix_parts.append("⬜ OPSIONAL")

        if is_auto:
            suffix_parts.append("🤖 otomatis")

        suffix = " · ".join(suffix_parts)

        # Render checkbox with Streamlit
        key_name = f"check_{idx}"
        if key_name not in st.session_state:
            st.session_state[key_name] = False

        st.checkbox(
            f"{label}  `{suffix}`",
            key=key_name,
        )
        if st.session_state[key_name]:
            checked += 1

    # Progress
    if total > 0:
        progress = checked / total
        if progress >= 0.8:
            st.success(f"✅ {checked}/{total} item selesai")
        else:
            st.info(f"📋 {checked}/{total} item selesai")
        st.progress(progress)


def step_progress(current_step: int, total_steps: int, label: str, progress_bar) -> None:
    """
    Update progress bar with step indicator.

    Args:
        current_step: Current step (1-indexed)
        total_steps: Total number of steps
        label: Description of current step
        progress_bar: Streamlit progress bar object
    """
    fraction = min(max(current_step / max(total_steps, 1), 0.0), 1.0)
    display_label = f"[{current_step}/{total_steps}] {label}"
    progress_bar.progress(fraction, text=display_label)
