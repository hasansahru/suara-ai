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
import re

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
                "processing",
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
    if run_btn:
        run_analysis(youtube_url)

    # --- Tampilkan hasil ---
    if st.session_state.analysis_result:
        render_results()


# ═══════════════════════════════════════════════════════════════
# ANALYSIS PIPELINE
# ═══════════════════════════════════════════════════════════════

def estimate_max_tokens(output_type_id: str, shot_count: int | None) -> int:
    """Mengestimasi kebutuhan max_tokens berdasarkan jenis output dan jumlah shot."""
    base_tokens = 4000
    if output_type_id == "shorts" and shot_count:
        return max(8000, base_tokens + (shot_count * 2000))
    elif output_type_id == "long":
        return 16000
    return 16000

def run_analysis(youtube_url: str):
    """Jalankan pipeline analisis lengkap."""
    if st.session_state.processing:
        return

    # Validasi input
    uploaded_file = st.session_state.get("uploaded_file")
    pasted_transcript = st.session_state.get("pasted_transcript", "")
    has_transcript = (
        uploaded_file is not None
        or (pasted_transcript and pasted_transcript.strip())
    )

    if not has_transcript and not youtube_url:
        st.session_state.last_error = (
            "Masukkan URL YouTube atau upload/paste transkrip terlebih dahulu."
        )
        st.session_state.processing = False
        st.rerun()
        return

    if not st.session_state.selected_channel:
        st.session_state.last_error = "Pilih channel DNA terlebih dahulu di sidebar."
        st.session_state.processing = False
        st.rerun()
        return

    if not st.session_state.selected_provider:
        st.session_state.last_error = "Pilih AI provider terlebih dahulu di sidebar."
        st.session_state.processing = False
        st.rerun()
        return

    if not st.session_state.selected_model:
        st.session_state.last_error = (
            "Pilih atau ketik model AI terlebih dahulu di sidebar."
        )
        st.session_state.processing = False
        st.rerun()
        return

    st.session_state.processing = True
    st.session_state.analysis_result = None
    st.session_state.generated_content = None

    progress_bar = st.progress(0, text="Memulai pipeline analisis...")
    total_steps = 5

    # --- Bangun proxy config ---
    proxy_mode = st.session_state.get("proxy_mode", "none")
    proxy_setting = youtube_utils.ProxySetting(
        mode=proxy_mode,
        http_url=st.session_state.get("sidebar_generic_http", ""),
        https_url=st.session_state.get("sidebar_generic_https", ""),
        webshare_username=st.session_state.get("sidebar_ws_user", ""),
        webshare_password=st.session_state.get("sidebar_ws_pass", ""),
    )

    try:
        proxy_config = youtube_utils.build_proxy_config(proxy_setting)
    except youtube_utils.YouTubeUtilsError as exc:
        st.session_state.last_error = str(exc)
        st.session_state.processing = False
        st.rerun()
        return

    try:
        video_title = ""
        transcript_text = ""

        # Step 1: Ambil metadata + transkrip
        ui.step_progress(1, total_steps, "Mengambil data video / transkrip...", progress_bar)

        if uploaded_file is not None:
            raw_bytes = uploaded_file.read()
            transcript_text = raw_bytes.decode("utf-8", errors="ignore")
            if youtube_url:
                try:
                    meta = youtube_utils.get_video_metadata(youtube_url)
                    video_title = meta.get("title", "")
                except youtube_utils.YouTubeUtilsError:
                    video_title = ""

        elif pasted_transcript and pasted_transcript.strip():
            transcript_text = pasted_transcript.strip()
            if youtube_url:
                try:
                    meta = youtube_utils.get_video_metadata(youtube_url)
                    video_title = meta.get("title", "")
                except youtube_utils.YouTubeUtilsError:
                    video_title = ""

        else:
            video_id = youtube_utils.extract_video_id(youtube_url)
            if not video_id:
                raise youtube_utils.YouTubeUtilsError(
                    "URL YouTube tidak valid. Pastikan formatnya benar, contoh: "
                    "https://www.youtube.com/watch?v=XXXXXXXXXXX"
                )

            try:
                meta = youtube_utils.get_video_metadata(youtube_url)
                video_title = meta.get("title", "")
            except youtube_utils.YouTubeUtilsError:
                video_title = ""

            transcript_obj = youtube_utils.get_video_transcript(
                video_id,
                proxy_config=proxy_config,
            )
            transcript_text = transcript_obj.full_text

        if not transcript_text or not transcript_text.strip():
            raise ValueError("Transkrip kosong. Pastikan video memiliki transkrip/subtitle.")

        # Step 2: Parse analytics (opsional)
        ui.step_progress(2, total_steps, "Menganalisis data channel...", progress_bar)
        channel_summary = None
        try:
            analytics_files = st.session_state.get("analytics_files") or []
            if analytics_files:
                channel_summary, analytics_warnings = analytics_parser.process_uploaded_analytics(
                    st.session_state.selected_channel, analytics_files
                )
                for w in analytics_warnings:
                    st.session_state.pending_warnings.append(w)
        except Exception:
            channel_summary = None

        # Step 3: Bangun system prompt
        ui.step_progress(3, total_steps, "Menyusun prompt AI...", progress_bar)

        channel_id = st.session_state.selected_channel
        system_prompt = prompt_loader.build_system_prompt(channel_id)

        # Injeksi analytics summary ke prompt jika ada
        if channel_summary:
            system_prompt += "\n\n---\n\n## ANALYTICS DATA CHANNEL\n"
            system_prompt += channel_summary.to_prompt_text()

        # Step 4: Kirim ke AI
        ui.step_progress(4, total_steps, "Mengirim ke AI & menunggu respons...", progress_bar)

        prov_config = _get_provider_config(st.session_state.selected_provider)
        if not prov_config:
            raise ValueError("Konfigurasi provider tidak ditemukan.")

        mode = prov_config.get("mode", "openai_compatible")
        base_url = prov_config.get("default_base_url", "")
        api_key_env = prov_config.get("api_key_env", "")
        api_key_input = st.session_state.get("sidebar_api_key", "")
        custom_endpoint = st.session_state.get("sidebar_base_url", "")

        if custom_endpoint:
            base_url = custom_endpoint

        output_type_conf = st.session_state.get("output_type_conf") or {}
        duration_conf = st.session_state.get("duration_conf") or {}
        shot_count = st.session_state.get("shot_count")
        segment_mode = st.session_state.get("segment_mode", "auto")
        manual_start = st.session_state.get("manual_start")
        manual_end = st.session_state.get("manual_end")
        extra_notes = st.session_state.get("extra_notes")

        target_min_seconds = duration_conf.get("min_seconds")
        target_max_seconds = duration_conf.get("max_seconds")

        # --- ESTIMASI TOKEN (KODE BARU) ---
        output_type_id = output_type_conf.get("id", "")
        estimated_tokens = estimate_max_tokens(output_type_id, shot_count)

        user_content = ai_client.build_user_content(
            video_title=video_title,
            transcript_text=transcript_text,
            output_type=output_type_conf.get("label", ""),
            duration_label=duration_conf.get("label", ""),
            segment_mode=segment_mode,
            manual_start=manual_start,
            manual_end=manual_end,
            extra_notes=extra_notes,
            shot_count=shot_count,
            target_min_seconds=target_min_seconds,
            target_max_seconds=target_max_seconds,
        )

        request = ai_client.AnalysisRequest(
            system_prompt=system_prompt,
            user_content=user_content,
            mode=mode,
            base_url=base_url,
            model=st.session_state.selected_model or "",
            max_tokens=estimated_tokens,
            enable_thinking=st.session_state.get("thinking_enabled", True),
            enable_code_execution=st.session_state.get("code_execution_enabled", False),
            enable_web_search=st.session_state.get("web_search_enabled", False),
        )

        full_text, sources = ai_client.run_analysis(
            request,
            api_key=api_key_input,
            api_key_env=api_key_env,
        )

        if not full_text:
            raise ValueError("AI mengembalikan respons kosong.")

        # Step 5: Parse hasil
        ui.step_progress(5, total_steps, "Mem-parsing hasil analisis...", progress_bar)

        try:
            result = ai_parser.parse_ai_response(full_text)
        except ai_parser.AIResponseParseError as exc:
            st.session_state.pending_warnings.append(
                f"⚠️ Respons AI tidak bisa di-parse sebagai JSON ({exc}). Menampilkan respons mentah."
            )
            result = {"raw_response": full_text}

        # Potong shots jika melebihi shot_count yang diminta, dan cek kesesuaian durasi
        if isinstance(result, dict) and shot_count:
            result = ai_parser.enforce_shot_count(result, shot_count)
            segments = ai_parser.get_shot_segment_list(result)
            duration_warnings = ai_parser.check_segment_duration_mismatch(
                segments, target_min_seconds, target_max_seconds
            )
            for w in duration_warnings:
                st.session_state.pending_warnings.append(f"⚠️ {w}")

        st.session_state.analysis_result = result
        st.session_state.generated_content = result
        st.session_state.analysis_sources = sources

        st.success("✅ Analisis selesai!")

    except Exception as e:
        st.session_state.last_error = f"Gagal menganalisis: {e}"

    finally:
        st.session_state.processing = False
        st.rerun()


# ═══════════════════════════════════════════════════════════════
# RENDER RESULTS
# ═══════════════════════════════════════════════════════════════

def render_results():
    """Render hasil analisis dalam tabs."""
    result = st.session_state.analysis_result
    if not result:
        return

    output_settings = _load_json("output_setting.json")
    sections = output_settings.get("sections", [])

    sources = st.session_state.get("analysis_sources") or []
    if sources:
        with st.expander(f"🔍 Sumber Web Search ({len(sources)})"):
            for src in sources:
                st.markdown(f"- [{src.get('title', src.get('url', ''))}]({src.get('url', '')})")

    # Tab names
    tab_names = [f"{s.get('emoji', '')} {s.get('label', s.get('key', ''))}" for s in sections]
    tab_names.append("📋 JSON Mentah")

    tabs = st.tabs(tab_names)

    for idx, section in enumerate(sections):
        with tabs[idx]:
            key = section.get("key", "")
            label = section.get("label", key)
            emoji = section.get("emoji", "")

            if key == "ringkasan":
                render_ringkasan(result)
            elif key == "strategi":
                render_strategi(result)
            elif key == "segmen":
                render_segmen(result)
            elif key == "judul":
                render_judul(result)
            elif key == "thumbnail":
                render_thumbnail(result)
            elif key == "deskripsi":
                render_deskripsi(result)
            elif key == "seo":
                render_seo(result)
            elif key == "editing":
                render_editing(result)
            elif key == "prediksi":
                render_prediksi(result)
            elif key == "checklist":
                render_checklist(result)
            else:
                # Generic render
                data = result.get(key, result.get("video_panjang", {}).get(key))
                if data:
                    st.markdown(f"### {emoji} {label}".strip())
                    ui.copy_block(json.dumps(data, ensure_ascii=False, indent=2), language="json")

    # Tab JSON mentah
    with tabs[-1]:
        st.code(json.dumps(result, ensure_ascii=False, indent=2), language="json")
        if st.button("📋 Salin JSON", key="copy_json_full"):
            try:
                import pyperclip
                pyperclip.copy(json.dumps(result, ensure_ascii=False, indent=2))
                st.toast("✅ JSON disalin ke clipboard!", icon="📋")
            except Exception:
                st.toast("⚠️ Salin manual dari kode di atas", icon="⚠️")


# ═══════════════════════════════════════════════════════════════
# RENDER PER SECTION (DIUBAH AGAR VISUAL LEBIH RAPI & PROFESIONAL)
# ═══════════════════════════════════════════════════════════════

def render_ringkasan(result: dict):
    """Render section Ringkasan."""
    ringkasan = result.get("ringkasan", {})
    psikologi = result.get("psikologi_audiens", {})

    if ringkasan:
        st.markdown("### 📊 Ringkasan Analisis")
        if isinstance(ringkasan, dict):
            for k, v in ringkasan.items():
                if isinstance(v, str):
                    st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")
        else:
            st.markdown(str(ringkasan))

    if psikologi:
        st.markdown("### 🧠 Psikologi Audiens")
        if isinstance(psikologi, dict):
            for k, v in psikologi.items():
                if isinstance(v, str):
                    st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")
        else:
            st.markdown(str(psikologi))


def render_strategi(result: dict):
    """Render section Strategi."""
    video_panjang = result.get("video_panjang", {})
    shots = result.get("shots", [])

    source = video_panjang if video_panjang else (shots[0] if shots else {})
    strategi = source.get("strategi_konten", {})
    skor = result.get("skor_growth", {})

    if strategi:
        st.markdown("### 🎯 Strategi Konten")
        for k, v in strategi.items():
            if isinstance(v, str):
                st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")

    if skor:
        st.markdown("### 📈 Skor Growth")
        ui.render_score_grid(skor)


def render_segmen(result: dict):
    """Render section Segmen dengan visualisasi bersih."""
    video_panjang = result.get("video_panjang", {})
    shots = result.get("shots", [])

    # Cek momen highlight di dalam video_panjang atau di root JSON
    momen = video_panjang.get("momen_highlight_sumber", [])
    if not momen and "momen_highlight_sumber" in result:
        momen = result.get("momen_highlight_sumber", [])

    if momen:
        st.markdown("### 🎬 Momen Highlight Sumber")
        # Jika AI mengembalikan dict bukan list, ubah jadi list
        if isinstance(momen, dict):
            momen = [momen]
            
        for m in momen:
            if isinstance(m, dict):
                # 1. Coba tangkap berbagai variasi nama 'kunci' (key) yang mungkin di-generate AI
                waktu = m.get('timestamp', m.get('waktu', m.get('time', m.get('durasi', ''))))
                deskripsi = m.get('deskripsi', m.get('keterangan', m.get('topik', m.get('isi', m.get('highlight', '')))))
                
                # 2. Jika key AI benar-benar berbeda, ambil nilai dari urutan 1 dan 2 secara paksa
                if not waktu and not deskripsi and len(m) > 0:
                    keys = list(m.keys())
                    if len(keys) >= 2:
                        waktu = m[keys[0]]
                        deskripsi = m[keys[1]]
                    else:
                        deskripsi = m[keys[0]]
                
                # 3. Format cetak yang rapi tanpa memunculkan bintang empat (****) jika kosong
                waktu_teks = f"**{waktu}**" if waktu else ""
                pemisah = " — " if waktu and deskripsi else ""
                st.markdown(f"⏱️ {waktu_teks}{pemisah}{deskripsi}")
                
            elif isinstance(m, str):
                # Jika AI hanya memberikan list berupa teks biasa (bukan format JSON terstruktur)
                st.markdown(f"⏱️ {m}")
            else:
                # Fallback terakhir jika datanya sangat aneh
                st.write(m)

    if shots:
        st.markdown("### 🎬 Daftar Susunan Shot / Segmen")
        for shot in shots:
            if isinstance(shot, dict):
                num = shot.get("shot_number", "?")
                segmen = shot.get("segmen", {})
                
                # Fallback key untuk start dan end time
                start = segmen.get('start_time', segmen.get('waktu_mulai', ''))
                end = segmen.get('end_time', segmen.get('waktu_selesai', ''))
                
                with st.expander(f"📌 Shot #{num} ({start} - {end})", expanded=True):
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        dur = str(segmen.get('durasi', '')).split(' ')[0]
                        st.metric(label="⏱️ Durasi", value=f"{dur} s")
                    with col2:
                        st.markdown("**Alasan Pemilihan Segmen:**")
                        st.write(segmen.get('alasan', segmen.get('keterangan', '-')))


def render_judul(result: dict):
    """Render section Judul dengan rekomendasi terbaik."""
    video_panjang = result.get("video_panjang", {})
    shots = result.get("shots", [])

    def display_judul_block(judul_data, label_prefix=""):
        if not judul_data:
            return
        if label_prefix:
            st.markdown(f"#### {label_prefix}")
        
        # Tampilkan opsi judul
        opsi = judul_data.get("opsi", [])
        if opsi:
            st.markdown("**Alternatif Variasi Judul:**")
            for i, o in enumerate(opsi):
                st.markdown(f"{i+1}. `{o}`")
        
        # Tampilkan best choice
        best = judul_data.get("best_choice", "")
        if best:
            st.success(f"🏆 **Rekomendasi Terbaik:** {best}")
            
        # Tampilkan alasan
        alasan = judul_data.get("alasan_best_choice", "")
        if alasan:
            st.info(f"💡 **Analisis Strategi:** {alasan}")

    if video_panjang:
        judul = video_panjang.get("judul", {})
        if judul:
            display_judul_block(judul, "Video Utama")

    for shot in shots:
        if isinstance(shot, dict):
            judul = shot.get("judul", {})
            num = shot.get("shot_number", "?")
            if judul:
                with st.expander(f"Shot #{num} — Judul", expanded=True):
                    display_judul_block(judul, "")


def render_thumbnail(result: dict):
    """Render section Thumbnail ke panduan visual."""
    video_panjang = result.get("video_panjang", {})
    shots = result.get("shots", [])

    def display_thumb_block(thumb_data, label_prefix=""):
        if not thumb_data:
            return
        if label_prefix:
            st.markdown(f"#### 🖼️ {label_prefix}")
        
        konsep = thumb_data.get('konsep', thumb_data.get('ide_visual', '-'))
        st.markdown(f"🧠 **Konsep Ide:** {konsep}")
        
        komposisi = thumb_data.get('komposisi', thumb_data.get('komposisi_objek', '-'))
        st.markdown(f"📐 **Komposisi Objek:** {komposisi}")
        
        teks_thumb = thumb_data.get('teks_thumbnail', thumb_data.get('teks', ''))
        if teks_thumb:
            st.markdown(f"💬 **Teks/Copy Thumbnail:** `{teks_thumb}`")
        
        # Tampilkan Palet Warna
        warna = thumb_data.get("warna", thumb_data.get("palet_warna", []))
        if warna:
            st.markdown("**🎨 Rekomendasi Palet Warna:**")
            hex_cols = st.columns(max(len(warna), 1))
            for idx, w_text in enumerate(warna):
                hex_match = re.search(r'#([A-Fa-f0-9]{6})', str(w_text))
                hex_code = hex_match.group(0) if hex_match else "#FFFFFF"
                with hex_cols[idx]:
                    try:
                        st.color_picker(str(w_text)[:15], value=hex_code, key=f"cp_{label_prefix}_{idx}", disabled=True)
                    except Exception:
                        st.write(str(w_text))
                    
        psikologi = thumb_data.get('psikologi_warna', thumb_data.get('psikologi', '-'))
        st.markdown(f"👁️ **Psikologi Warna & Kontras:** {psikologi}")
        
        prompt_ai = thumb_data.get("prompt_ai_image", thumb_data.get("prompt_midjourney", ""))
        if prompt_ai:
            st.code(prompt_ai, language="text")
            st.caption("☝️ *Salin kode prompt di atas ke AI Image Generator (Midjourney/Flux/DALL-E)*")

    if video_panjang:
        thumb = video_panjang.get("thumbnail", {})
        if thumb:
            display_thumb_block(thumb, "Video Utama")

    for shot in shots:
        if isinstance(shot, dict):
            thumb = shot.get("thumbnail", {})
            num = shot.get("shot_number", "?")
            if thumb:
                with st.expander(f"Shot #{num} — Thumbnail", expanded=True):
                    display_thumb_block(thumb, "")


def render_deskripsi(result: dict):
    """Render section Deskripsi YouTube."""
    video_panjang = result.get("video_panjang", {})
    shots = result.get("shots", [])

    if video_panjang:
        desc = video_panjang.get("deskripsi_youtube", "")
        if desc:
            st.markdown("### 📝 Deskripsi YouTube")
            st.text_area("Deskripsi", value=desc, height=200, disabled=True)

    for shot in shots:
        if isinstance(shot, dict):
            desc = shot.get("deskripsi_youtube", "")
            num = shot.get("shot_number", "?")
            if desc:
                with st.expander(f"Shot #{num} — Deskripsi", expanded=True):
                    st.text_area(
                        f"Deskripsi Shot #{num}",
                        value=desc,
                        height=200,
                        disabled=True,
                    )


def render_seo(result: dict):
    """Render section SEO dengan rapi."""
    video_panjang = result.get("video_panjang", {})
    shots = result.get("shots", [])

    def display_seo_block(seo_data):
        tags = seo_data.get("tags", seo_data.get("keywords", []))
        if tags:
            st.markdown("**🏷️ Tags / Keywords:**")
            st.markdown(" ".join([f"`{t}`" for t in tags]))
        
        hashtag = seo_data.get("hashtag", seo_data.get("hashtags", []))
        if hashtag:
            st.markdown("**#️⃣ Hashtags:**")
            st.markdown(" ".join([f"`{h}`" for h in hashtag]))
            
        pinned = seo_data.get("pinned_comment", "")
        if pinned:
            st.markdown("**📌 Pinned Comment:**")
            st.info(pinned)

    if video_panjang:
        seo = video_panjang.get("seo", {})
        if seo:
            st.markdown("### 🔍 SEO Video Utama")
            display_seo_block(seo)

    for shot in shots:
        if isinstance(shot, dict):
            seo = shot.get("seo", {})
            num = shot.get("shot_number", "?")
            if seo:
                with st.expander(f"Shot #{num} — SEO", expanded=True):
                    display_seo_block(seo)


def render_editing(result: dict):
    """Render section Editing List."""
    video_panjang = result.get("video_panjang", {})
    shots = result.get("shots", [])
    
    def display_editing(editing_data):
        for k, v in editing_data.items():
            if isinstance(v, list):
                st.markdown(f"**{k.replace('_', ' ').title()}:**")
                for item in v:
                    st.markdown(f"- {item}")
            elif isinstance(v, str):
                st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")
            else:
                st.json(v)

    if video_panjang:
        editing = video_panjang.get("editing", {})
        if editing:
            st.markdown("### 🎞 Editing Video Utama")
            display_editing(editing)

    for shot in shots:
        if isinstance(shot, dict):
            editing = shot.get("editing", {})
            num = shot.get("shot_number", "?")
            if editing:
                with st.expander(f"Shot #{num} — Editing", expanded=True):
                    display_editing(editing)


def render_prediksi(result: dict):
    """Render section Prediksi Performa."""
    video_panjang = result.get("video_panjang", {})
    shots = result.get("shots", [])

    if video_panjang:
        prediksi = video_panjang.get("prediksi_performa", {})
        if prediksi:
            st.markdown("### 📈 Prediksi Performa Video Utama")
            for k, v in prediksi.items():
                st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")

    for shot in shots:
        if isinstance(shot, dict):
            prediksi = shot.get("prediksi_performa", {})
            num = shot.get("shot_number", "?")
            if prediksi:
                with st.expander(f"Shot #{num} — Prediksi Performa", expanded=True):
                    skor = prediksi.get("skor_keseluruhan")
                    if skor:
                        st.metric(label="⭐ Skor Keseluruhan", value=f"{skor} / 10")
                    
                    for k, v in prediksi.items():
                        if k != "skor_keseluruhan":
                            st.markdown(f"**{k.replace('_', ' ').title()}:** {v}")


def render_checklist(result: dict):
    """Render section Checklist Produksi."""
    video_panjang = result.get("video_panjang", {})
    shots = result.get("shots", [])

    def display_checklist(checklist_data, prefix):
        if not checklist_data:
            return
        if isinstance(checklist_data, list):
            for idx, item in enumerate(checklist_data):
                if isinstance(item, str):
                    st.checkbox(item, key=f"check_{prefix}_{idx}")
                elif isinstance(item, dict):
                    label = item.get("task", item.get("item", str(item)))
                    wajib = item.get("wajib", False)
                    if wajib:
                        label = f"**[WAJIB]** {label}"
                    st.checkbox(label, key=f"check_{prefix}_{idx}")

    # Cek checklist di luar (untuk video utama)
    root_checklist = result.get("checklist_produksi", result.get("checklist", video_panjang.get("checklist", [])))
    if root_checklist:
        st.markdown("### ✅ Checklist Produksi Video Utama")
        display_checklist(root_checklist, "root")

    # Cek checklist di dalam setiap shot
    for shot in shots:
        if isinstance(shot, dict):
            checklist = shot.get("checklist_produksi", shot.get("checklist", []))
            num = shot.get("shot_number", "?")
            if checklist:
                with st.expander(f"Shot #{num} — Checklist Produksi", expanded=True):
                    display_checklist(checklist, f"shot_{num}")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    """Fungsi utama."""
    render_sidebar()
    render_main_content()


if __name__ == "__main__":
    main()
