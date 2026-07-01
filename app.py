"""
AI YouTube Content Intelligence Pro
=====================================
Aplikasi web untuk menganalisis video YouTube (reverse engineering strategi
konten) dan menghasilkan paket produksi YouTube baru yang orisinal, sesuai
DNA channel yang dipilih pengguna.

Jalankan dengan:
    streamlit run app.py
"""
from __future__ import annotations

import json
import os
import base64
import tempfile

import streamlit as st

from utils import prompt_loader
from utils import youtube_utils
from utils import ai_client
from utils import parser as ai_parser
from utils import ui_components as ui
from utils import analytics_parser
from utils.m3_style import inject_m3_css, add_dark_mode_toggle

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_DIR = os.path.join(BASE_DIR, "settings")


# ═══════════════════════════════════════════════════════════════
# PAGE CONFIG & THEME
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="🎬 AI YouTube Content Intelligence Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

dark_mode = add_dark_mode_toggle()
inject_m3_css(dark_mode=dark_mode)


# ═══════════════════════════════════════════════════════════════
# SESSION STATE DEFAULTS
# ═══════════════════════════════════════════════════════════════

def init_session():
    """Inisialisasi session state dengan default."""
    defaults = {
        "analysis_result": None,
        "generated_content": None,
        "analysis_sources": [],
        "processing": False,
        "last_error": None,
        "pending_warnings": [],
        "selected_channel": None,
        "selected_provider": None,
        "selected_model": None,
        "custom_endpoint": "",
        "uploaded_text": "",
        "show_channel_form": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session()


# ═══════════════════════════════════════════════════════════════
# HELPER: Load settings
# ═══════════════════════════════════════════════════════════════

def _load_json(filename: str) -> dict:
    """Muat file JSON dari folder settings."""
    path = os.path.join(SETTINGS_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _get_ai_settings() -> dict:
    """Ambil pengaturan AI provider dari session atau file."""
    settings = _load_json("ai_provider_setting.json")
    return settings


def _get_provider_config(provider_id: str) -> dict | None:
    """Cari konfigurasi provider berdasarkan ID."""
    settings = _get_ai_settings()
    for p in settings.get("providers", []):
        if p.get("id") == provider_id:
            return p
    return None


# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════

def render_sidebar():
    """Render sidebar: channel selection, provider, proxy, upload."""
    with st.sidebar:
        st.markdown("## 🎬 Channel & Provider")

        # --- Channel selection ---
        channels = prompt_loader.get_available_channels()
        channel_options = {c["emoji"] + " " + c["name"]: c["id"] for c in channels}
        selected_label = st.selectbox(
            "Pilih Channel DNA",
            options=list(channel_options.keys()),
            key="sidebar_channel",
        )
        if selected_label:
            st.session_state.selected_channel = channel_options[selected_label]

        st.divider()

        # --- Provider selection ---
        ai_settings = _get_ai_settings()
        providers = ai_settings.get("providers", [])
        PROVIDER_PLACEHOLDER = "— Pilih AI Provider —"
        provider_options = {p["label"]: p["id"] for p in providers}
        prov_config = None

        if provider_options:
            prov_choices = [PROVIDER_PLACEHOLDER] + list(provider_options.keys())
            prov_label = st.selectbox(
                "Pilih AI Provider",
                options=prov_choices,
                key="sidebar_provider",
            )
            if prov_label and prov_label != PROVIDER_PLACEHOLDER:
                st.session_state.selected_provider = provider_options[prov_label]
            else:
                st.session_state.selected_provider = None
                st.caption("⚠️ Pilih provider AI terlebih dahulu untuk melanjutkan.")

        # --- Model, API key & cek koneksi ---
        if st.session_state.selected_provider:
            prov_config = _get_provider_config(st.session_state.selected_provider)

        if prov_config:
            with st.container(border=True):
                models = prov_config.get("models", [])
                allow_custom = prov_config.get("allow_custom_model", False)
                requires_base_url = prov_config.get("requires_base_url", False)
                api_key_env = prov_config.get("api_key_env", "")
                provider_mode = prov_config.get("mode", "openai_compatible")
                default_base_url = prov_config.get("default_base_url", "")

                model_list = models or []
                model_id_options = [m["id"] for m in model_list]
                model_label_by_id = {m["id"]: m["label"] for m in model_list}

                if model_id_options or allow_custom:
                    prior_model = st.session_state.get("selected_model")
                    if prior_model and prior_model not in model_id_options:
                        model_id_options = model_id_options + [prior_model]

                    selected_model_id = st.selectbox(
                        "Pilih Model",
                        options=model_id_options,
                        index=(
                            model_id_options.index(prior_model)
                            if prior_model in model_id_options
                            else None
                        ),
                        format_func=lambda mid: model_label_by_id.get(mid, mid),
                        placeholder=(
                            "Pilih dari daftar atau ketik ID model manual..."
                            if allow_custom
                            else "— Pilih Model —"
                        ),
                        accept_new_options=allow_custom,
                        key=f"sidebar_model_{st.session_state.selected_provider}",
                    )
                    st.session_state.selected_model = selected_model_id
                else:
                    st.session_state.selected_model = None

                base_url_value = default_base_url
                if requires_base_url:
                    base_url_value = st.text_input(
                        "Base URL",
                        value=default_base_url,
                        key="sidebar_base_url",
                    )

                api_key = st.text_input(
                    f"API Key ({api_key_env})",
                    type="password",
                    key="sidebar_api_key",
                    help=(
                        f"Kosongkan jika API key sudah diatur lewat environment "
                        f"variable {api_key_env} / file .env."
                    ),
                )

                if not st.session_state.selected_model:
                    st.caption("⚠️ Pilih atau ketik model AI sebelum cek koneksi / analisis.")

                effective_model = st.session_state.selected_model or ""
                effective_base_url = st.session_state.get("sidebar_base_url", base_url_value)
                current_sig = (
                    st.session_state.selected_provider,
                    effective_model,
                    st.session_state.get("sidebar_api_key", ""),
                    effective_base_url,
                )

                check_clicked = st.button(
                    "🔌 Cek Koneksi",
                    key="sidebar_check_conn",
                    use_container_width=True,
                    disabled=not effective_model,
                )
                if check_clicked:
                    with st.spinner("Menghubungi provider..."):
                        try:
                            msg = ai_client.test_connection(
                                mode=provider_mode,
                                model=effective_model,
                                api_key=st.session_state.get("sidebar_api_key", ""),
                                api_key_env=api_key_env,
                                base_url=effective_base_url,
                            )
                            st.session_state["conn_check_result"] = {
                                "sig": current_sig, "status": "success", "msg": msg,
                            }
                        except ai_client.AIClientError as exc:
                            st.session_state["conn_check_result"] = {
                                "sig": current_sig, "status": "error", "msg": str(exc),
                            }
                        except Exception as exc:  # noqa: BLE001
                            st.session_state["conn_check_result"] = {
                                "sig": current_sig, "status": "error", "msg": f"Gagal cek koneksi: {exc}",
                            }

                conn_result = st.session_state.get("conn_check_result")
                if conn_result and conn_result.get("sig") == current_sig:
                    if conn_result["status"] == "success":
                        st.success(f"✅ {conn_result['msg']}")
                    else:
                        st.error(f"❌ {conn_result['msg']}")
                elif conn_result:
                    st.caption("ℹ️ Pengaturan berubah — klik 'Cek Koneksi' lagi untuk memverifikasi.")
        else:
            st.session_state.selected_model = None

        st.divider()

        # --- Proxy settings ---
        st.markdown("### 🌐 Proxy YouTube")
        proxy_mode = st.selectbox(
            "Mode Proxy",
            ["none", "generic", "webshare"],
            key="sidebar_proxy_mode",
        )
        if proxy_mode == "generic":
            st.text_input("HTTP Proxy URL", key="sidebar_generic_http")
            st.text_input("HTTPS Proxy URL", key="sidebar_generic_https")
        elif proxy_mode == "webshare":
            st.text_input("Webshare Username", key="sidebar_ws_user")
            st.text_input("Webshare Password", type="password", key="sidebar_ws_pass")

        st.divider()

        # --- Upload transcript ---
        st.markdown("### 📄 Upload Transkrip")
        uploaded_file = st.file_uploader(
            "Upload .txt transkrip YouTube",
            type=["txt"],
            key="sidebar_upload",
        )
        pasted = st.text_area(
            "Atau paste transkrip di sini",
            height=150,
            key="sidebar_paste",
        )

        # --- Upload Analytics CSV (opsional) ---
        st.markdown("### 📊 Analytics Channel (opsional)")
        analytics_uploads = st.file_uploader(
            "Upload CSV export dari YouTube Studio Analytics (boleh lebih dari satu)",
            type=["csv"],
            accept_multiple_files=True,
            key="sidebar_analytics_upload",
        )
        analytics_files = []
        if analytics_uploads:
            for f in analytics_uploads:
                analytics_files.append((f.name, f.read()))
        st.session_state["analytics_files"] = analytics_files

        # --- Thinking & Code Execution ---
        st.markdown("### ⚙️ Opsi Lanjutan")
        thinking = st.checkbox("🧠 Thinking Mode", value=True, key="sidebar_thinking")
        code_exec = st.checkbox("💻 Code Execution", value=False, key="sidebar_code_exec")
        web_search = st.checkbox("🔍 Web Search", value=False, key="sidebar_web_search")

        st.session_state["uploaded_file"] = uploaded_file
        st.session_state["pasted_transcript"] = pasted
        st.session_state["proxy_mode"] = proxy_mode
        st.session_state["thinking_enabled"] = thinking
        st.session_state["code_execution_enabled"] = code_exec
        st.session_state["web_search_enabled"] = web_search


# ═══════════════════════════════════════════════════════════════
# MAIN CONTENT
# ═══════════════════════════════════════════════════════════════

def render_main_content():
    """Render area konten utama."""
    st.markdown("# 🎬 AI YouTube Content Intelligence Pro")
    st.caption(
        "Reverse-engineer strategi video YouTube & hasilkan paket produksi orisinal siap upload."
    )

    # --- Input section ---
    youtube_url = st.text_input(
        "🔗 URL Video YouTube (opsional)",
        placeholder="https://www.youtube.com/watch?v=XXXXXXXXXXX",
        key="main_url",
    )

    # --- Pengaturan Output (tipe konten, durasi, jumlah shot, mode segmen) ---
    duration_settings = _load_json("duration_setting.json")
    output_types = duration_settings.get("output_types", [])
    segment_modes = duration_settings.get("segment_modes", [])

    st.markdown("### ⚙️ Pengaturan Output")

    selected_output_type: dict = {}
    selected_duration: dict = {}

    col_a, col_b = st.columns(2)
    with col_a:
        if output_types:
            type_labels = {f"{t.get('emoji', '')} {t.get('label', t.get('id', ''))}": t for t in output_types}
            type_label = st.selectbox(
                "Tipe Output",
                options=list(type_labels.keys()),
                key="main_output_type_label",
            )
            selected_output_type = type_labels[type_label]

    with col_b:
        durations = selected_output_type.get("durations", [])
        if durations:
            duration_labels = {d["label"]: d for d in durations}
            duration_label_sel = st.selectbox(
                "Durasi Target",
                options=list(duration_labels.keys()),
                key="main_duration_label",
            )
            selected_duration = duration_labels[duration_label_sel]

    shot_count = None
    shot_conf = selected_output_type.get("shot_count", {})
    if shot_conf.get("enabled"):
        shot_count = st.slider(
            shot_conf.get("label", "Jumlah Shots/Segmen"),
            min_value=int(shot_conf.get("min", 1)),
            max_value=int(shot_conf.get("max", 10)),
            value=int(shot_conf.get("default", 3)),
            help=shot_conf.get("help", ""),
            key="main_shot_count",
        )

    segment_mode = "auto"
    if segment_modes:
        seg_mode_labels = {m["label"]: m["id"] for m in segment_modes}
        seg_mode_label = st.selectbox(
            "Mode Segmen",
            options=list(seg_mode_labels.keys()),
            key="main_segment_mode_label",
        )
        segment_mode = seg_mode_labels[seg_mode_label]

    manual_start = manual_end = None
    if segment_mode == "manual":
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            manual_start = st.text_input("Waktu Mulai (mm:ss)", key="main_manual_start")
        with col_m2:
            manual_end = st.text_input("Waktu Selesai (mm:ss)", key="main_manual_end")

    extra_notes = st.text_area(
        "Catatan Tambahan untuk AI (opsional)", key="main_extra_notes", height=80
    )

    st.session_state["output_type_conf"] = selected_output_type
    st.session_state["duration_conf"] = selected_duration
    st.session_state["shot_count"] = shot_count
    st.session_state["segment_mode"] = segment_mode
    st.session_state["manual_start"] = manual_start
    st.session_state["manual_end"] = manual_end
    st.session_state["extra_notes"] = extra_notes

    # --- Tombol Analisis ---
    col1, col2 = st.columns([3, 1])
    with col1:
        run_btn = st.button(
            "🚀 Jalankan Analisis",
            type="primary",
            use_container_width=True,
            key="main_run",
        )
    with col2:
        if st.button("🗑️ Reset", use_container_width=True, key="main_reset"):
            for k in [
                "analysis_result",
                "generated_content",
                "last_error",
                "pending_warnings",
            ]:
                st.session_state.pop(k, None)
            st.rerun()

    # --- Tampilkan error jika ada ---
    if st.session_state.last_error:
        st.error(f"❌ {st.session_state.last_error}")
        st.session_state.last_error = None

    # --- Tampilkan warning yang tertunda (selamat dari st.rerun()) ---
    if st.session_state.get("pending_warnings"):
        for w in st.session_state.pending_warnings:
            st.warning(w)
        st.session_state.pending_warnings = []

    # --- Jalankan analisis ---
    if run
