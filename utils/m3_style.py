"""
m3_style_enhanced.py — Material Design 3 Modern Theme v2
======================================================
AI YouTube Content Intelligence Pro · Modern Light/Dark Mode

Fitur:
  ✓ Light & Dark mode otomatis dari sistem
  ✓ Professional Material Design 3 tokens
  ✓ Modern animations & hover effects
  ✓ Responsive layout & typography
  ✓ All features preserved, enhanced UI

Cara pakai:
  from utils.m3_style_enhanced import inject_m3_css, add_dark_mode_toggle

  dark_mode = add_dark_mode_toggle()
  inject_m3_css(dark_mode=dark_mode)
"""

import streamlit as st

# ============================================================
# MATERIAL DESIGN 3 COLOR TOKENS
# ============================================================

LIGHT = {
    # Backgrounds & Surfaces
    "bg_0":        "#FAFAFA",   # Canvas/page background
    "bg_1":        "#FFFFFF",   # Cards, elevated surfaces
    "bg_2":        "#F3F4F6",   # Input fields, secondary bg
    "bg_3":        "#E5E7EB",   # Hover state

    # Primary (Modern Blue)
    "primary":     "#2563EB",   # Main action color
    "primary_dk":  "#1D4ED8",   # Hover/pressed
    "primary_ct":  "#EFF6FF",   # Container bg (light)
    "primary_br":  "#BFDBFE",   # Border

    # Text Colors
    "text_0":      "#0F172A",   # Headings, high emphasis
    "text_1":      "#1E293B",   # Body text, default
    "text_2":      "#64748B",   # Secondary/muted
    "text_3":      "#94A3B8",   # Placeholder/disabled

    # Borders
    "border_0":    "#F1F5F9",   # Subtle dividers
    "border_1":    "#E2E8F0",   # Default
    "border_2":    "#CBD5E1",   # Emphasis

    # Semantic Colors
    "success":     "#16A34A",
    "success_ct":  "#F0FDF4",
    "success_br":  "#86EFAC",
    "success_tx":  "#15803D",

    "warning":     "#DC2626",
    "warning_ct":  "#FEF2F2",
    "warning_br":  "#FCA5A5",
    "warning_tx":  "#991B1B",

    "info":        "#2563EB",
    "info_ct":     "#EFF6FF",
    "info_br":     "#BFDBFE",
    "info_tx":     "#1D4ED8",

    # Shadows
    "shadow_sm":   "0 1px 2px rgba(0,0,0,0.05)",
    "shadow_md":   "0 4px 6px rgba(0,0,0,0.08)",
    "shadow_lg":   "0 10px 15px rgba(0,0,0,0.10)",
}

DARK = {
    # Backgrounds & Surfaces (M3 elegant grays, not pure black)
    "bg_0":        "#0F172A",   # Canvas/page
    "bg_1":        "#1A202C",   # Cards
    "bg_2":        "#2D3748",   # Input fields
    "bg_3":        "#4A5568",   # Hover state

    # Primary (Lighter blue for dark mode)
    "primary":     "#60A5FA",   # Brighter for contrast
    "primary_dk":  "#93C5FD",   # Hover
    "primary_ct":  "#1E3A5F",   # Container (dark)
    "primary_br":  "#2A4E80",   # Border

    # Text Colors
    "text_0":      "#F8FAFC",   # Headings
    "text_1":      "#E2E8F0",   # Body
    "text_2":      "#94A3B8",   # Secondary
    "text_3":      "#64748B",   # Placeholder

    # Borders
    "border_0":    "rgba(255,255,255,0.05)",
    "border_1":    "rgba(255,255,255,0.10)",
    "border_2":    "rgba(255,255,255,0.15)",

    # Semantic Colors
    "success":     "#4ADE80",
    "success_ct":  "#1B4D2F",
    "success_br":  "#22863A",
    "success_tx":  "#4ADE80",

    "warning":     "#FCA5A5",
    "warning_ct":  "#4B1818",
    "warning_br":  "#7F1D1D",
    "warning_tx":  "#FCA5A5",

    "info":        "#60A5FA",
    "info_ct":     "#1E3A5F",
    "info_br":     "#2A4E80",
    "info_tx":     "#60A5FA",

    # Shadows
    "shadow_sm":   "0 1px 2px rgba(0,0,0,0.3)",
    "shadow_md":   "0 4px 12px rgba(0,0,0,0.4)",
    "shadow_lg":   "0 10px 25px rgba(0,0,0,0.5)",
}


def inject_m3_css(dark_mode: bool = False) -> None:
    """
    Inject Material Design 3 modern styling ke Streamlit.

    Args:
        dark_mode: True = dark mode, False = light mode
    """
    c = DARK if dark_mode else LIGHT

    css = f"""
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ═════════════════════════════════════════════════════════════
       MATERIAL DESIGN 3 — MODERN UI
       Mode: {'Dark' if dark_mode else 'Light'} · v2
    ═════════════════════════════════════════════════════════════ */

    :root {{
        --md3-bg-0: {c['bg_0']};
        --md3-bg-1: {c['bg_1']};
        --md3-bg-2: {c['bg_2']};
        --md3-bg-3: {c['bg_3']};
        --md3-primary: {c['primary']};
        --md3-primary-dk: {c['primary_dk']};
        --md3-primary-ct: {c['primary_ct']};
        --md3-primary-br: {c['primary_br']};
        --md3-text-0: {c['text_0']};
        --md3-text-1: {c['text_1']};
        --md3-text-2: {c['text_2']};
        --md3-text-3: {c['text_3']};
        --md3-border-0: {c['border_0']};
        --md3-border-1: {c['border_1']};
        --md3-border-2: {c['border_2']};
        --md3-success: {c['success']};
        --md3-success-ct: {c['success_ct']};
        --md3-success-br: {c['success_br']};
        --md3-warning: {c['warning']};
        --md3-warning-ct: {c['warning_ct']};
        --md3-info: {c['info']};
        --md3-info-ct: {c['info_ct']};
        --md3-shadow-sm: {c['shadow_sm']};
        --md3-shadow-md: {c['shadow_md']};
        --md3-shadow-lg: {c['shadow_lg']};
    }}

    /* ── FONT & BASE ── */
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }}

    /* ── APP BACKGROUND ── */
    .stApp {{
        background-color: var(--md3-bg-0) !important;
    }}
    .main .block-container {{
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
        max-width: 1400px;
    }}

    /* ── SIDEBAR ── */
    [data-testid="stSidebar"] {{
        background: var(--md3-bg-1) !important;
        border-right: 1px solid var(--md3-border-1) !important;
    }}
    [data-testid="stSidebar"] > div:first-child {{ padding-top: 1rem; }}

    /* ── APP HEADER ── */
    .app-header {{
        padding: 2rem;
        margin-bottom: 2rem;
        border-radius: 16px;
        background: var(--md3-bg-1);
        border: 1px solid var(--md3-border-1);
        box-shadow: var(--md3-shadow-md);
        overflow: hidden;
        position: relative;
    }}
    .app-header::before {{
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(135deg, var(--md3-primary-ct) 0%, transparent 50%);
        opacity: 0.5;
        pointer-events: none;
    }}
    .app-header-inner {{ position: relative; z-index: 1; }}
    .app-header h1 {{
        margin: 0 0 0.5rem 0;
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: var(--md3-text-0) !important;
    }}
    .app-header h1 span {{
        color: var(--md3-primary) !important;
    }}
    .app-subtitle {{
        font-size: 0.95rem;
        color: var(--md3-text-2) !important;
        line-height: 1.6;
        margin: 0.5rem 0 1rem 0;
    }}

    /* ── INPUTS ── */
    .stTextInput input,
    .stTextArea textarea,
    div[data-baseweb="input"] input {{
        background: var(--md3-bg-2) !important;
        border: 1.5px solid var(--md3-border-1) !important;
        border-radius: 10px !important;
        color: var(--md3-text-1) !important;
        font-size: 0.9rem !important;
        padding: 11px 14px !important;
        transition: all 0.2s ease !important;
    }}
    .stTextInput input:focus,
    .stTextArea textarea:focus {{
        border-color: var(--md3-primary) !important;
        box-shadow: 0 0 0 3px var(--md3-primary-ct) !important;
        outline: none !important;
    }}
    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {{
        color: var(--md3-text-3) !important;
    }}

    /* ── SELECTBOX / DROPDOWN ── */
    div[data-baseweb="select"] > div {{
        background: var(--md3-bg-2) !important;
        border: 1.5px solid var(--md3-border-1) !important;
        border-radius: 10px !important;
        min-height: 44px !important;
        transition: all 0.2s !important;
    }}
    div[data-baseweb="select"] > div:hover {{
        border-color: var(--md3-border-2) !important;
    }}
    div[data-baseweb="select"] > div:focus-within {{
        border-color: var(--md3-primary) !important;
        box-shadow: 0 0 0 3px var(--md3-primary-ct) !important;
    }}
    ul[role="listbox"] {{
        background: var(--md3-bg-1) !important;
        border: 1px solid var(--md3-border-1) !important;
        border-radius: 12px !important;
        box-shadow: var(--md3-shadow-lg) !important;
        padding: 6px !important;
    }}
    li[role="option"]:hover {{
        background: var(--md3-bg-2) !important;
        color: var(--md3-text-0) !important;
    }}
    li[role="option"][aria-selected="true"] {{
        background: var(--md3-primary-ct) !important;
        color: var(--md3-primary) !important;
        font-weight: 600 !important;
    }}

    /* ── BUTTONS ── */
    .stButton > button {{
        border-radius: 10px !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        padding: 10px 20px !important;
        border: 1.5px solid var(--md3-border-2) !important;
        background: var(--md3-bg-2) !important;
        color: var(--md3-text-1) !important;
        transition: all 0.2s ease !important;
    }}
    .stButton > button:hover {{
        background: var(--md3-bg-3) !important;
        border-color: var(--md3-primary-br) !important;
        transform: translateY(-1px) !important;
    }}
    .stButton > button[kind="primary"] {{
        background: var(--md3-primary) !important;
        border-color: var(--md3-primary-dk) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        box-shadow: var(--md3-shadow-md) !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: var(--md3-primary-dk) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 16px rgba(37, 99, 235, 0.3) !important;
    }}

    /* ── TABS ── */
    [data-testid="stTabs"] [role="tablist"] {{
        background: var(--md3-bg-1) !important;
        border: 1px solid var(--md3-border-1) !important;
        border-radius: 12px !important;
        padding: 6px !important;
        gap: 4px !important;
    }}
    [data-testid="stTabs"] button[role="tab"] {{
        border-radius: 8px !important;
        color: var(--md3-text-2) !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        padding: 8px 16px !important;
        transition: all 0.2s ease !important;
    }}
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
        background: var(--md3-primary-ct) !important;
        color: var(--md3-primary) !important;
        font-weight: 600 !important;
        box-shadow: var(--md3-shadow-sm) !important;
    }}

    /* ── EXPANDERS ── */
    details[data-testid="stExpander"] {{
        background: var(--md3-bg-1) !important;
        border: 1px solid var(--md3-border-1) !important;
        border-radius: 12px !important;
        box-shadow: none;
        transition: all 0.2s ease !important;
    }}
    details[data-testid="stExpander"]:hover {{
        border-color: var(--md3-primary-br) !important;
        box-shadow: var(--md3-shadow-sm) !important;
    }}
    details[data-testid="stExpander"] summary {{
        padding: 14px 18px !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        color: var(--md3-text-1) !important;
    }}
    details[data-testid="stExpander"] > div {{
        padding: 0 18px 14px 18px !important;
    }}

    /* ── METRICS ── */
    .stMetric {{
        background: var(--md3-bg-1) !important;
        border: 1px solid var(--md3-border-1) !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: var(--md3-shadow-sm) !important;
        transition: all 0.2s ease !important;
    }}
    .stMetric:hover {{
        border-color: var(--md3-primary-br) !important;
        box-shadow: var(--md3-shadow-md) !important;
        transform: translateY(-2px) !important;
    }}
    .stMetric [data-testid="stMetricValue"] {{
        color: var(--md3-text-0) !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }}
    .stMetric [data-testid="stMetricLabel"] {{
        color: var(--md3-text-2) !important;
        font-size: 0.75rem !important;
    }}

    /* ── ALERTS ── */
    [data-testid="stSuccessMessage"] {{
        background: var(--md3-success-ct) !important;
        border: 1px solid var(--md3-success-br) !important;
        border-radius: 10px !important;
        color: var(--md3-success) !important;
    }}
    [data-testid="stWarningMessage"] {{
        background: var(--md3-warning-ct) !important;
        border: 1px solid var(--md3-warning) !important;
        border-radius: 10px !important;
        color: var(--md3-warning-tx) !important;
    }}
    [data-testid="stInfoMessage"] {{
        background: var(--md3-info-ct) !important;
        border: 1px solid var(--md3-info-br) !important;
        border-radius: 10px !important;
        color: var(--md3-info-tx) !important;
    }}

    /* ── CONTAINERS ── */
    [data-testid="stVerticalBlockBorderWrapper"] > div {{
        background: var(--md3-bg-1) !important;
        border: 1px solid var(--md3-border-1) !important;
        border-radius: 12px !important;
    }}

    /* ── FILE UPLOADER ── */
    [data-testid="stFileUploader"] > div {{
        background: var(--md3-bg-2) !important;
        border: 2px dashed var(--md3-border-2) !important;
        border-radius: 12px !important;
        transition: all 0.2s ease !important;
    }}
    [data-testid="stFileUploader"] > div:hover {{
        border-color: var(--md3-primary) !important;
        background: var(--md3-primary-ct) !important;
    }}

    /* ── PROGRESS BAR ── */
    [data-testid="stProgressBar"] > div {{
        background: var(--md3-bg-2) !important;
        border-radius: 999px;
        height: 8px !important;
    }}
    [data-testid="stProgressBar"] > div > div {{
        background: var(--md3-primary) !important;
        border-radius: 999px;
    }}

    /* ── CODE BLOCKS ── */
    .stCodeBlock pre {{
        background: var(--md3-bg-2) !important;
        border: 1px solid var(--md3-border-1) !important;
        border-radius: 10px !important;
        font-size: 0.85rem !important;
    }}

    /* ── TYPOGRAPHY ── */
    h1, h2, h3, h4 {{
        color: var(--md3-text-0) !important;
        font-weight: 700 !important;
        letter-spacing: -0.015em;
    }}
    h2 {{ font-size: 1.4rem !important; }}
    h3 {{ font-size: 1.1rem !important; }}
    p, span, li {{ color: var(--md3-text-1); }}
    .stMarkdown p {{
        color: var(--md3-text-1) !important;
        line-height: 1.7;
        font-size: 0.95rem;
    }}
    a {{
        color: var(--md3-primary) !important;
        text-decoration: none;
        transition: color 0.2s ease !important;
    }}
    a:hover {{ text-decoration: underline; }}
    .stCaption {{
        color: var(--md3-text-2) !important;
        font-size: 0.8rem !important;
    }}

    /* ── SCROLLBAR ── */
    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{
        background: var(--md3-border-2);
        border-radius: 999px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: var(--md3-text-2);
    }}

    /* ── DIVIDERS ── */
    hr {{
        border: none !important;
        border-top: 1px solid var(--md3-border-0) !important;
        margin: 1.5rem 0 !important;
    }}

    /* ── FOOTER ── */
    footer.app-footer {{
        margin-top: 3rem;
        padding: 1rem 0 0.5rem 0;
        text-align: center;
        font-size: 0.75rem;
        color: var(--md3-text-3);
        border-top: 1px solid var(--md3-border-0);
    }}

    /* ── SPINNER ── */
    [data-testid="stSpinner"] {{ color: var(--md3-primary) !important; }}
    """

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def add_dark_mode_toggle() -> bool:
    """
    Tambahkan toggle Dark Mode ke sidebar.
    Return True jika dark mode aktif.

    FIX: implementasi lama mendeteksi preferensi OS lewat JavaScript
    (`matchMedia`) lalu memaksa `window.parent.location.replace(...)` untuk
    menambahkan query param `m3_theme` dan me-reload SELURUH halaman. Ini
    menyebabkan masalah nyata yang dilaporkan sebagai "UI error mode nya":
      1. Flash-of-wrong-theme: render pertama SELALU light mode (session_state
         di-set False dulu) sebelum JS sempat jalan & me-reload halaman.
      2. `window.parent.location.replace` bisa diblokir oleh sandbox iframe di
         beberapa environment hosting Streamlit, sehingga reload tidak pernah
         terjadi dan toggle macet di light mode terus walau OS memakai dark mode.
      3. Reload paksa di tengah render pertama bisa memicu re-render
         ganda/flicker pada widget lain di halaman yang sama.

    Sekarang: tidak ada reload paksa sama sekali. Default awal = light mode,
    pengguna sepenuhnya mengontrol lewat toggle manual di sidebar — jauh
    lebih stabil di semua environment hosting.
    """
    if "md3_dark_mode" not in st.session_state:
        st.session_state.md3_dark_mode = False

    with st.sidebar:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption("🎨 Tema")
        with col2:
            dark = st.toggle(
                "🌙",
                value=st.session_state.md3_dark_mode,
                key="md3_dark_toggle",
                help="Dark/Light Mode",
                label_visibility="collapsed",
            )
        st.session_state.md3_dark_mode = dark

    return dark
