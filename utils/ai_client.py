"""
ai_client.py

Wrapper tipis untuk memanggil AI provider menggunakan system prompt gabungan
dari prompt_loader.py, serta input pengguna (transkrip + setting).

Mendukung dua mode pemanggilan:

1. mode="anthropic"
   Memanggil Claude langsung lewat Anthropic SDK (client.messages.create).

2. mode="openai_compatible"
   Memanggil provider mana pun yang mengikuti format OpenAI Chat Completions
   (base_url + api_key + model). Mode ini dipakai untuk:
   - 9Router Proxy (proxy lokal self-hosted, lihat https://github.com/decolua/9router)
   - OpenAI (GPT) langsung
   - Google Gemini langsung (lewat endpoint OpenAI-compatible Google)
   - Provider/proxy custom lain apa pun (OpenRouter, Groq, DeepSeek, LiteLLM, dll)

Provider mana yang aktif & konfigurasinya (base_url default, env var API key,
daftar model) diatur lewat settings/ai_provider_setting.json, dibaca oleh app.py.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 16000

# Token yang cukup untuk respons test connection singkat ("OK" / satu kalimat).
_TEST_MAX_TOKENS = 64

# Timeout koneksi awal (detik) — hanya untuk handshake TCP/TLS, bukan untuk menunggu respons.
_CONNECT_TIMEOUT = 15.0

# Mode yang didukung oleh run_analysis().
MODE_ANTHROPIC = "anthropic"
MODE_OPENAI_COMPATIBLE = "openai_compatible"


class AIClientError(Exception):
    """Error umum untuk semua kegagalan pemanggilan AI provider."""


class _EmptyFenceResponseError(AIClientError):
    """
    Sub-kelas khusus untuk kasus "respons cuma blok kode kosong tanpa isi JSON".
    Dipisah dari AIClientError biasa supaya run_analysis() bisa mengenali pola
    kegagalan ini secara spesifik dan melakukan SATU KALI auto-retry — karena
    pola ini teramati bersifat transient (gangguan sesaat generasi model),
    bukan kesalahan input yang akan terus berulang jika dicoba lagi.
    """


@dataclass
class AnalysisRequest:
    system_prompt: str
    user_content: str
    model: str = DEFAULT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = 0.7
    mode: str = MODE_ANTHROPIC
    base_url: Optional[str] = None  # hanya dipakai jika mode == openai_compatible
    timeout: float = 180.0
    # --- Skill Claude tambahan (hanya berlaku untuk mode == anthropic) ---
    enable_web_search: bool = False   # aktifkan tool web_search bawaan Claude (riset tren/SEO real-time)
    web_search_max_uses: int = 5      # batas jumlah pencarian per request, agar latensi/biaya terkendali
    enable_thinking: bool = False     # aktifkan extended thinking Claude untuk reasoning lebih dalam
    thinking_budget_tokens: int = 4000
    enable_code_execution: bool = False  # aktifkan tool code_execution bawaan Claude (hitung durasi/timing presisi)


def get_api_key(env_var_name: str, explicit_key: Optional[str] = None) -> str:
    """
    Mengambil API key dengan urutan prioritas:
    1. Key yang diberikan langsung (misalnya dari input UI).
    2. Environment variable sesuai provider yang aktif (env_var_name).
    """
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()

    env_key = os.environ.get(env_var_name, "").strip()
    if env_key:
        return env_key

    raise AIClientError(
        f"API key belum diatur untuk provider ini. Masukkan API key di sidebar, "
        f"atau set environment variable {env_var_name} / gunakan file .env."
    )


def _make_httpx_timeout(request_timeout: float, is_test: bool = False):
    """
    Membuat httpx.Timeout dengan komponen yang tepat untuk request AI.

    Mengapa tidak pakai float tunggal:
    - Pada openai SDK v1.x, float tunggal hanya menjadi `httpx.Timeout(total=X)`,
      yang berarti setiap read-chunk dibatasi X detik, BUKAN keseluruhan request.
    - Untuk generate JSON panjang (bisa 60-180 detik), kita perlu:
        * connect  : singkat (15 detik cukup untuk handshake)
        * read     : = request_timeout (biarkan model berpikir sampai selesai)
        * write    : cukup untuk upload prompt (30 detik)
        * pool     : singkat
    """
    try:
        import httpx
        connect = 10.0 if is_test else _CONNECT_TIMEOUT
        return httpx.Timeout(
            connect=connect,
            read=request_timeout,
            write=30.0,
            pool=5.0,
        )
    except ImportError:
        # httpx tidak terinstall secara terpisah (biasanya di-bundle oleh openai/anthropic).
        # Kembalikan float saja sebagai fallback.
        return request_timeout


def _run_anthropic(request: AnalysisRequest, resolved_key: str, check_truncation: bool = True) -> tuple[str, list[dict]]:
    """
    Memanggil Anthropic API dan mengembalikan (teks respons, daftar sumber web search).

    Setiap item pada daftar sumber berbentuk {"title": str, "url": str},
    diambil dari hasil tool web_search bawaan Claude (jika enable_web_search
    aktif). Daftar ini kosong jika web search tidak diaktifkan atau Claude
    tidak melakukan pencarian apa pun untuk request ini.

    Args:
        check_truncation: Jika True, lempar error ketika stop_reason == "max_tokens"
                          (respons terpotong). Set False untuk test connection agar
                          tidak false-positive error saat max_tokens sengaja kecil.
    """
    try:
        import anthropic
    except ImportError as exc:
        raise AIClientError(
            "Paket 'anthropic' belum terinstal. Jalankan: pip install -r requirements.txt"
        ) from exc

    is_test = not check_truncation
    timeout_obj = _make_httpx_timeout(request.timeout, is_test=is_test)

    # --- Skill Claude: Web Search (riset real-time tren/SEO/judul kompetitor) ---
    # Tool ini dieksekusi otomatis oleh Anthropic di sisi server dalam satu call
    # yang sama (tidak perlu loop manual) — hasil pencarian disisipkan sebagai
    # content block tambahan (server_tool_use / web_search_tool_result) sebelum
    # blok teks final, yang sudah otomatis terfilter oleh `block.type == "text"` di bawah.
    tools: list = []
    if getattr(request, "enable_web_search", False) and not is_test:
        tools.append(
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": max(1, int(getattr(request, "web_search_max_uses", 5) or 5)),
            }
        )

    # --- Skill Claude: Code Execution (hitung durasi/timing/SEO secara presisi) ---
    # Tool ini menjalankan Python di sandbox milik Anthropic. Dipakai supaya
    # perhitungan seperti total durasi outline, start/end time tiap shot, atau
    # panjang judul/keyword density TIDAK ditebak oleh model, tapi benar-benar
    # dihitung — mengurangi kasus durasi shot melenceng dari target.
    effective_system_prompt = request.system_prompt
    if getattr(request, "enable_code_execution", False) and not is_test:
        tools.append({"type": "code_execution_20250825", "name": "code_execution"})
        effective_system_prompt = (
            request.system_prompt
            + "\n\n---\n\n"
            + "## SKILL TAMBAHAN: CODE EXECUTION\n"
            + "Anda memiliki akses ke tool `code_execution` (Python sandbox). WAJIB pakai tool "
            + "ini untuk setiap perhitungan numerik presisi sebelum menuliskan hasil akhirnya, "
            + "termasuk: (1) menjumlahkan durasi tiap babak di `outline` agar totalnya pas dengan "
            + "Durasi Target, (2) menghitung `start_estimate`/`end_estimate` tiap babak secara "
            + "kumulatif dari 00:00, (3) memverifikasi durasi tiap shot (end_time - start_time) "
            + "berada dalam rentang target yang diminta, (4) menghitung panjang karakter judul "
            + "dan kepadatan keyword SEO. JANGAN menebak angka-angka ini secara manual — jalankan "
            + "kode untuk memastikan akurat, lalu sisipkan hasilnya ke JSON output."
        )

    # --- Skill Claude: Extended Thinking (reasoning lebih dalam sebelum menjawab) ---
    # Saat thinking aktif: temperature WAJIB 1 (syarat API) dan max_tokens harus
    # lebih besar dari thinking budget (kita tambahkan otomatis agar JSON akhir
    # tidak ikut terpotong oleh budget thinking).
    thinking_param = None
    effective_max_tokens = request.max_tokens
    effective_temperature = request.temperature
    if getattr(request, "enable_thinking", False) and not is_test:
        budget = max(1024, int(getattr(request, "thinking_budget_tokens", 4000) or 4000))
        thinking_param = {"type": "enabled", "budget_tokens": budget}
        effective_max_tokens = request.max_tokens + budget
        effective_temperature = 1.0

    create_kwargs = dict(
        model=request.model,
        max_tokens=effective_max_tokens,
        temperature=effective_temperature,
        system=effective_system_prompt,
        messages=[
            {
                "role": "user",
                "content": request.user_content,
            }
        ],
    )
    if tools:
        create_kwargs["tools"] = tools
    if thinking_param:
        create_kwargs["thinking"] = thinking_param

    try:
        client = anthropic.Anthropic(api_key=resolved_key, timeout=timeout_obj)
        message = client.messages.create(**create_kwargs)
    except anthropic.APITimeoutError as exc:
        raise AIClientError(
            f"Anthropic API tidak merespons dalam {request.timeout:.0f} detik (timeout). "
            "Coba lagi, naikkan nilai Timeout API di sidebar, atau kurangi Jumlah Shots/Segmen."
        ) from exc
    except anthropic.AuthenticationError as exc:
        raise AIClientError(
            "API key tidak valid atau tidak punya akses. Periksa kembali ANTHROPIC_API_KEY Anda."
        ) from exc
    except anthropic.RateLimitError as exc:
        raise AIClientError(
            "Rate limit Anthropic API tercapai. Coba lagi beberapa saat lagi."
        ) from exc
    except anthropic.APIStatusError as exc:
        raise AIClientError(f"Anthropic API mengembalikan error: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise AIClientError(f"Gagal memanggil Anthropic API: {exc}") from exc

    text_parts = [block.text for block in message.content if getattr(block, "type", None) == "text"]
    full_text = "\n".join(text_parts).strip()

    # --- Ekstrak sumber web search (untuk ditampilkan ke user sebagai citation) ---
    # Setiap web_search_tool_result berisi daftar hasil pencarian (title + url)
    # yang dipakai Claude untuk menyusun jawabannya. Kita kumpulkan semua,
    # dedupe by url, dan kembalikan urutannya sesuai urutan dipakai.
    sources: list[dict] = []
    seen_urls: set[str] = set()
    for block in message.content:
        if getattr(block, "type", None) != "web_search_tool_result":
            continue
        block_content = getattr(block, "content", None)
        if not isinstance(block_content, list):
            continue
        for item in block_content:
            url = getattr(item, "url", None)
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            title = getattr(item, "title", None) or url
            sources.append({"title": title, "url": url})

    # FIX: sebelumnya, kasus respons yang secara efektif KOSONG (mis. Claude
    # hanya mengembalikan blok kode kosong ```json\n``` tanpa isi JSON —
    # observasi nyata: terjadi ketika Claude memakai skill tambahan seperti
    # Web Search/Code Execution/Extended Thinking lalu tidak sempat menulis
    # jawaban akhirnya) TIDAK terdeteksi di sini sama sekali, karena
    # full_text.strip() tetap non-empty (isinya "```json\n```"). Kasus ini lolos
    # ke parser.py dan baru gagal di sana dengan pesan yang keliru menuduh
    # "max_tokens terpotong" — padahal stop_reason di sini BUKAN "max_tokens".
    # Sekarang dideteksi di sini juga, dengan diagnosis yang jauh lebih akurat
    # karena kita tahu persis stop_reason & skill apa saja yang aktif.
    import re as _re
    _looks_empty = bool(_re.fullmatch(r"```(?:json)?\s*```", full_text.strip(), flags=_re.DOTALL))
    if check_truncation and _looks_empty:
        _active_skills = [
            name for name, on in (
                ("Web Search", getattr(request, "enable_web_search", False)),
                ("Code Execution", getattr(request, "enable_code_execution", False)),
                ("Extended Thinking", getattr(request, "enable_thinking", False)),
            ) if on
        ]
        _skill_note = (
            f" Skill tambahan yang aktif saat ini: {', '.join(_active_skills)}. "
            "Ini adalah penyebab paling umum untuk pola kegagalan ini — Claude memakai "
            "tool/reasoning lalu tidak menuliskan jawaban akhirnya."
            if _active_skills else
            " Tidak ada skill tambahan yang aktif, jadi kemungkinan ini masalah sesaat dari model/provider."
        )
        raise _EmptyFenceResponseError(
            f"Claude mengembalikan respons KOSONG (stop_reason={getattr(message, 'stop_reason', None)!r}, "
            "hanya berupa blok kode kosong tanpa isi JSON)." + _skill_note +
            " Coba jalankan ulang; jika terus terjadi pada kombinasi skill yang sama, "
            "nonaktifkan salah satu skill tambahan tersebut untuk isolasi penyebab."
        )

    # Hanya periksa truncation saat ini bukan test connection.
    # Saat test connection, max_tokens sengaja kecil sehingga stop_reason bisa
    # "max_tokens" walau respons "OK" sudah lengkap — bukan berarti JSON terpotong.
    if check_truncation and getattr(message, "stop_reason", None) == "max_tokens":
        raise AIClientError(
            "Respons AI TERPOTONG karena mencapai batas max_tokens "
            f"({request.max_tokens} token), sehingga JSON-nya tidak lengkap/tidak valid. "
            "Solusi: kurangi 'Jumlah Shots/Segmen' di sidebar, pilih durasi output yang lebih "
            "pendek, atau gunakan model dengan output lebih ringkas."
        )

    return full_text, sources


def _run_openai_compatible(request: AnalysisRequest, resolved_key: str, check_truncation: bool = True) -> tuple[str, list[dict]]:
    """
    Memanggil endpoint OpenAI-compatible dan mengembalikan (teks respons, []).

    Daftar sumber selalu kosong di mode ini karena skill web_search bawaan
    Claude (server tool Anthropic) hanya berlaku untuk mode "anthropic".

    Args:
        check_truncation: Jika True, lempar error ketika finish_reason == "length"
                          (respons terpotong). Set False untuk test connection.
    """
    try:
        import openai
    except ImportError as exc:
        raise AIClientError(
            "Paket 'openai' belum terinstal. Jalankan: pip install -r requirements.txt "
            "(paket ini dipakai untuk provider 9Router/OpenAI/Gemini/Custom)."
        ) from exc

    if not request.base_url or not request.base_url.strip():
        raise AIClientError(
            "Base URL belum diisi untuk provider ini. Contoh untuk 9Router lokal: "
            "http://localhost:20128/v1"
        )

    is_test = not check_truncation
    timeout_obj = _make_httpx_timeout(request.timeout, is_test=is_test)

    # Beberapa model (terutama "thinking" model seperti Kimi K2, Qwen3 Thinking)
    # tidak mendukung temperature selain 1.0, atau mengabaikannya.
    # Untuk keamanan, kita kirim temperature apa adanya — error-nya akan muncul
    # sebagai APIStatusError dan ditangkap di bawah.

    client = openai.OpenAI(
        api_key=resolved_key,
        base_url=request.base_url.strip(),
        timeout=timeout_obj,
    )

    # Retry otomatis untuk error sementara: 503 Service Unavailable, 529 Overloaded,
    # dan timeout. Maksimal 3 percobaan dengan jeda eksponensial (2s → 4s).
    _RETRY_STATUS = {503, 529}
    _MAX_RETRIES = 3

    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=False,   # eksplisit non-streaming agar respons dikembalikan sekaligus
                messages=[
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_content},
                ],
            )
            break  # sukses — keluar dari loop retry
        except openai.APIStatusError as exc:
            status = getattr(exc, "status_code", None)
            if status in _RETRY_STATUS and attempt < _MAX_RETRIES:
                wait = 2 ** attempt  # 2s, 4s
                last_exc = exc
                time.sleep(wait)
                continue
            raise AIClientError(f"Provider mengembalikan error: {exc}") from exc
        except openai.APITimeoutError as exc:
            if attempt < _MAX_RETRIES:
                last_exc = exc
                time.sleep(2 ** attempt)
                continue
            raise AIClientError(
                f"Provider tidak merespons dalam {request.timeout:.0f} detik (timeout). "
                "Kemungkinan model/upstream yang dipilih sedang lambat atau antrian panjang. "
                "Coba lagi, naikkan nilai Timeout API di sidebar, ganti ke model lain yang "
                "lebih cepat, atau kurangi Jumlah Shots/Segmen."
            ) from exc
    else:
        # Semua percobaan habis — lempar error terakhir
        raise AIClientError(
            f"Provider tidak tersedia setelah {_MAX_RETRIES} percobaan "
            f"(Service Unavailable). Coba beberapa saat lagi."
        ) from last_exc


    # Ambil teks dari respons — validasi lebih teliti agar pesan error lebih jelas.
    if not response.choices:
        raise AIClientError(
            "Provider mengembalikan respons tanpa pilihan (choices kosong). "
            "Kemungkinan model tidak menghasilkan output — coba jalankan ulang."
        )

    choice = response.choices[0]

    if choice.message is None:
        raise AIClientError(
            "Provider mengembalikan choice tanpa message. "
            "Kemungkinan respons tidak lengkap — coba jalankan ulang."
        )

    full_text = (choice.message.content or "").strip()

    if not full_text:
        # Cek finish_reason untuk pesan error yang lebih informatif.
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason == "content_filter":
            raise AIClientError(
                "Respons diblokir oleh content filter provider. Coba ubah prompt atau ganti model."
            )
        raise AIClientError(
            f"Provider mengembalikan teks kosong (finish_reason={finish_reason!r}). "
            "Coba jalankan ulang atau ganti model."
        )

    # FIX: paritas dengan _run_anthropic — deteksi kasus respons yang cuma
    # berupa blok kode kosong (```json\n```) tanpa isi JSON. Untuk provider
    # OpenAI-compatible (9Router/OpenAI/Gemini/Custom) ini juga cukup umum
    # terjadi pada model "thinking" (mis. Kimi K2, Qwen3 Thinking, DeepSeek-R1)
    # yang menaruh reasoning-nya di field terpisah dan kadang tidak menuliskan
    # jawaban akhir ke field `content` biasa.
    import re as _re
    if check_truncation and _re.fullmatch(r"```(?:json)?\s*```", full_text.strip(), flags=_re.DOTALL):
        raise _EmptyFenceResponseError(
            f"Model '{request.model}' mengembalikan respons KOSONG "
            f"(finish_reason={getattr(choice, 'finish_reason', None)!r}, hanya blok kode kosong "
            "tanpa isi JSON). Ini sering terjadi pada model 'thinking/reasoning' yang menaruh "
            "penalarannya di tempat terpisah dan lupa menulis jawaban akhir. Coba jalankan ulang, "
            "atau ganti ke model non-thinking jika terus berulang."
        )

    # Hanya periksa truncation saat ini bukan test connection.
    if check_truncation and getattr(choice, "finish_reason", None) == "length":
        raise AIClientError(
            "Respons AI TERPOTONG karena mencapai batas max_tokens "
            f"({request.max_tokens} token), sehingga JSON-nya tidak lengkap/tidak valid. "
            "Solusi: kurangi 'Jumlah Shots/Segmen' di sidebar, pilih durasi output yang lebih "
            "pendek, atau gunakan model dengan output lebih ringkas."
        )

    return full_text, []


def run_analysis(request: AnalysisRequest, api_key: Optional[str] = None, api_key_env: str = "ANTHROPIC_API_KEY") -> tuple[str, list[dict]]:
    """
    Memanggil AI provider (sesuai request.mode) dengan system prompt + user content,
    mengembalikan (teks mentah respons, daftar sumber web search).

    Teks mentah diharapkan berupa JSON sesuai output_format.md. Daftar sumber
    berbentuk list of {"title": str, "url": str} — kosong jika web search
    tidak aktif, atau provider yang dipakai bukan mode "anthropic".

    Args:
        request: AnalysisRequest, termasuk mode ("anthropic" / "openai_compatible") dan
                  base_url (wajib diisi jika mode == "openai_compatible").
        api_key: API key eksplisit dari input UI (opsional, prioritas tertinggi).
        api_key_env: nama environment variable fallback untuk provider yang aktif.

    Raises:
        AIClientError jika library yang dibutuhkan tidak tersedia, API key tidak valid,
        endpoint tidak bisa dihubungi, atau terjadi error pada sisi provider.
    """
    resolved_key = get_api_key(api_key_env, api_key)

    def _call_once() -> tuple[str, list[dict]]:
        if request.mode == MODE_ANTHROPIC:
            return _run_anthropic(request, resolved_key, check_truncation=True)
        elif request.mode == MODE_OPENAI_COMPATIBLE:
            return _run_openai_compatible(request, resolved_key, check_truncation=True)
        else:
            raise AIClientError(f"Mode provider tidak dikenal: '{request.mode}'")

    # FIX: kasus "respons cuma blok kode kosong tanpa JSON" (_EmptyFenceResponseError)
    # teramati bersifat transient — bukan kesalahan input yang pasti berulang. Daripada
    # langsung menyerahkan kegagalan itu ke pengguna, coba SATU KALI lagi secara otomatis
    # (silent retry) sebelum benar-benar melempar error. Ini mengurangi laporan "output AI
    # kadang rusak" untuk kasus yang sebenarnya cukup diatasi dengan mencoba ulang.
    try:
        full_text, sources = _call_once()
    except _EmptyFenceResponseError as first_exc:
        try:
            full_text, sources = _call_once()
        except _EmptyFenceResponseError as second_exc:
            raise AIClientError(
                f"{second_exc} (Sudah dicoba otomatis 2x, tetap gagal — ini bukan kegagalan "
                "sesaat biasa, mohon periksa skill tambahan yang aktif atau ganti model.)"
            ) from second_exc

    if not full_text:
        raise AIClientError("AI provider mengembalikan respons kosong.")

    return full_text, sources


def test_connection(
    mode: str,
    model: str,
    api_key: Optional[str],
    api_key_env: str,
    base_url: Optional[str] = None,
    timeout: float = 30.0,
) -> str:
    """
    Mengirim permintaan minimal ke provider untuk mengecek apakah API key, base_url,
    dan model yang dipilih benar-benar bisa terhubung & merespons.

    Returns:
        String singkat berisi info sukses (misalnya nama model yang merespons).

    Raises:
        AIClientError jika koneksi/autentikasi/model gagal — pesan errornya sama dengan
        yang dipakai run_analysis(), jadi penyebabnya jelas (auth salah, base_url salah,
        model tidak ditemukan, timeout, dll).
    """
    resolved_key = get_api_key(api_key_env, api_key)

    test_request = AnalysisRequest(
        system_prompt="Anda hanya perlu membalas dengan satu kata: OK.",
        user_content="Balas dengan kata 'OK' saja, tanpa tambahan apa pun.",
        model=model,
        mode=mode,
        base_url=base_url,
        max_tokens=_TEST_MAX_TOKENS,  # cukup untuk respons singkat, tidak false-positive truncation
        temperature=1.0,              # gunakan 1.0 agar kompatibel dengan semua model termasuk "thinking" model
        timeout=timeout,
    )

    # check_truncation=False: jangan error hanya karena max_tokens kecil pada test request.
    # Yang penting adalah apakah API bisa dihubungi & merespons sama sekali.
    if mode == MODE_ANTHROPIC:
        _run_anthropic(test_request, resolved_key, check_truncation=False)
    elif mode == MODE_OPENAI_COMPATIBLE:
        _run_openai_compatible(test_request, resolved_key, check_truncation=False)
    else:
        raise AIClientError(f"Mode provider tidak dikenal: '{mode}'")

    return f"Berhasil terhubung ke model '{model}'."


# ============================================================
# SKILL CLAUDE: VISION — REVIEW THUMBNAIL
# ============================================================
# Fitur independen dari pipeline analisis utama (tidak terikat skema JSON
# output_format.md), supaya tidak mengganggu kontrak JSON yang sudah ketat.
# Memanggil Anthropic API langsung dengan image input (Claude Vision) untuk
# mengkritik thumbnail yang diupload user secara visual nyata.

THUMBNAIL_REVIEW_SYSTEM_PROMPT = """Anda adalah ahli desain thumbnail YouTube & spesialis CTR (click-through rate)
dengan pengalaman menganalisis ribuan thumbnail video yang viral maupun yang gagal.

Tugas Anda: memberi kritik visual yang JUJUR, SPESIFIK, dan BISA DITINDAKLANJUTI atas
gambar thumbnail yang dilampirkan pengguna — bukan sekadar opini umum.

Jika ada lebih dari satu gambar, anggap gambar pertama sebagai thumbnail UTAMA yang
dinilai, dan gambar berikutnya sebagai pembanding/kompetitor — bandingkan secara eksplisit.

Strukturkan jawaban Anda dengan format Markdown berikut (gunakan heading level 3 `###`):

### Kesan Pertama (< 1 detik)
Apa yang langsung terlihat & dirasakan dalam waktu sepersekian detik, terutama dalam
ukuran kecil seperti di feed mobile.

### Kekuatan
Poin-poin (bullet list) yang sudah bekerja dengan baik — komposisi, kontras, ekspresi/emosi,
keterbacaan teks, kesesuaian warna, dll.

### Kelemahan
Poin-poin (bullet list) yang berisiko menurunkan CTR — teks terlalu kecil/berdesakan,
kontras kurang, elemen penting tertutup progress bar YouTube, terlalu ramai/membingungkan,
tidak ada fokus mata yang jelas, dll.

### Rekomendasi Perbaikan
Langkah konkret & spesifik untuk memperbaiki kelemahan di atas (bukan saran generik).

### Skor CTR Estimasi
Satu angka 1-10 dengan alasan singkat (1-2 kalimat) mengapa skor itu diberikan.

Tulis semua dalam Bahasa Indonesia. JANGAN mengembalikan JSON — cukup teks Markdown biasa."""


def analyze_thumbnail(
    images: list[dict],
    notes: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    api_key_env: str = "ANTHROPIC_API_KEY",
    timeout: float = 90.0,
) -> str:
    """
    Mengirim satu atau beberapa gambar thumbnail ke Claude (lewat Anthropic API
    langsung — fitur Vision) untuk dikritik secara visual: komposisi, kontras,
    keterbacaan teks, kesesuaian emosi, dan estimasi dampaknya ke CTR.

    Args:
        images: list of {"media_type": "image/png" | "image/jpeg" | "image/webp",
                 "data": "<base64 string tanpa prefix data:...>"}.
                 Gambar pertama dianggap thumbnail utama yang dinilai; gambar
                 selanjutnya (jika ada) dianggap pembanding/kompetitor.
        notes: konteks tambahan dari user (opsional) — misalnya judul video,
               target audiens, atau pertanyaan spesifik soal thumbnail ini.
        model: model Claude yang dipakai (harus model yang mendukung vision —
               semua model Claude saat ini mendukung image input).
        api_key / api_key_env: sama seperti run_analysis().
        timeout: detik, default lebih pendek dari analisis utama karena ini
                 permintaan ringan (cuma kritik teks, bukan JSON kompleks).

    Returns:
        String Markdown berisi kritik thumbnail (Kesan Pertama, Kekuatan,
        Kelemahan, Rekomendasi Perbaikan, Skor CTR Estimasi).

    Raises:
        AIClientError jika tidak ada gambar, library tidak tersedia, API key
        tidak valid, atau provider gagal merespons.
    """
    if not images:
        raise AIClientError("Tidak ada gambar thumbnail yang diberikan untuk dianalisis.")

    try:
        import anthropic
    except ImportError as exc:
        raise AIClientError(
            "Paket 'anthropic' belum terinstal. Jalankan: pip install -r requirements.txt"
        ) from exc

    resolved_key = get_api_key(api_key_env, api_key)
    timeout_obj = _make_httpx_timeout(timeout, is_test=False)

    content: list[dict] = []
    for img in images:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img["media_type"],
                    "data": img["data"],
                },
            }
        )

    user_text = (
        "Kritik thumbnail di atas sesuai instruksi pada system prompt."
        + (f"\n\nKonteks tambahan dari pengguna: {notes.strip()}" if notes and notes.strip() else "")
    )
    content.append({"type": "text", "text": user_text})

    try:
        client = anthropic.Anthropic(api_key=resolved_key, timeout=timeout_obj)
        message = client.messages.create(
            model=model,
            max_tokens=2048,
            temperature=0.7,
            system=THUMBNAIL_REVIEW_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
    except anthropic.APITimeoutError as exc:
        raise AIClientError(
            f"Anthropic API tidak merespons dalam {timeout:.0f} detik (timeout) saat menganalisis thumbnail."
        ) from exc
    except anthropic.AuthenticationError as exc:
        raise AIClientError(
            "API key tidak valid atau tidak punya akses. Periksa kembali ANTHROPIC_API_KEY Anda."
        ) from exc
    except anthropic.RateLimitError as exc:
        raise AIClientError("Rate limit Anthropic API tercapai. Coba lagi beberapa saat lagi.") from exc
    except anthropic.APIStatusError as exc:
        raise AIClientError(f"Anthropic API mengembalikan error: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise AIClientError(f"Gagal memanggil Anthropic API untuk analisis thumbnail: {exc}") from exc

    text_parts = [block.text for block in message.content if getattr(block, "type", None) == "text"]
    full_text = "\n".join(text_parts).strip()

    if not full_text:
        raise AIClientError("AI mengembalikan respons kosong untuk analisis thumbnail.")

    return full_text


def build_user_content(
    video_title: str,
    transcript_text: str,
    output_type: str,
    duration_label: str,
    segment_mode: str,
    manual_start: Optional[str],
    manual_end: Optional[str],
    extra_notes: Optional[str] = None,
    shot_count: Optional[int] = None,
    target_min_seconds: Optional[int] = None,
    target_max_seconds: Optional[int] = None,
    analytics_text: Optional[str] = None,
) -> str:
    """Menyusun isi pesan user (konteks + transkrip + setting) untuk dikirim ke AI."""

    out = [
        "## INPUT UNTUK ANALISIS",
        "",
        f"- Judul Video Sumber: {video_title or '(tidak diketahui)'}",
        f"- Output Type yang Diinginkan: {output_type}",
        f"- Durasi Target: {duration_label}",
        f"- Segment Mode: {segment_mode}",
    ]

    if target_min_seconds or target_max_seconds:
        lo = target_min_seconds or target_max_seconds
        hi = target_max_seconds or target_min_seconds
        out.append(
            f"- Durasi Target dalam DETIK (untuk perhitungan presisi): {lo}-{hi} detik. "
            f"WAJIB: untuk SETIAP shot di `shots[].segmen` (Output Type = Shorts), "
            f"(end_time - start_time) harus berada dalam rentang {max(lo - 10, 1)}-{hi + 10} detik "
            f"(toleransi \u00b110 detik). Jika satu topik di transkrip lebih panjang dari itu, potong ke "
            f"sub-bagian tersempit yang paling kuat \u2014 JANGAN ambil seluruh blok topik."
        )

    if shot_count:
        out.append(
            f"- Jumlah Shots/Segmen yang Diminta: TEPAT {shot_count} shot. Hasilkan persis "
            f"{shot_count} elemen pada array `shots` di output JSON, tidak lebih dan tidak kurang, "
            f"diurutkan dari yang paling kuat/berpotensi viral. SETIAP elemen `shots[i]` WAJIB berisi "
            f"paket produksi LENGKAP dan BERBEDA-BEDA (judul, thumbnail, deskripsi, SEO, editing, "
            f"prediksi performa, checklist masing-masing spesifik untuk shot itu) \u2014 JANGAN membuat "
            f"satu paket generik yang dipakai ulang untuk semua shot. Biarkan object `video_panjang` "
            f"kosong (`{{}}`)."
        )
    elif output_type and "panjang" in output_type.lower():
        out.append(
            "- Output Type = Video Panjang: isi HANYA object `video_panjang` (satu paket utuh). "
            "WAJIB sertakan `video_panjang.strategi_konten.opening_60_detik` (rancangan menit "
            "pertama video baru) dan `start_estimate`/`end_estimate` (mm:ss, kumulatif dari 00:00) "
            "pada setiap babak di `video_panjang.strategi_konten.outline`, sehingga totalnya pas "
            "dengan Durasi Target. Biarkan array `shots` kosong (`[]`)."
        )

    if segment_mode.lower().startswith("manual") and (manual_start or manual_end):
        out.append(f"- Rentang Waktu Manual: {manual_start or '00:00'} - {manual_end or '?'}")

    if extra_notes:
        out.append(f"- Catatan Tambahan dari Pengguna: {extra_notes}")

    out.extend([
        "",
        "## TRANSKRIP VIDEO SUMBER",
        "",
        transcript_text.strip() if transcript_text else "(transkrip tidak tersedia)",
        "",
        "---",
    ])

    # Sisipkan data analytics channel (real data) jika tersedia
    if analytics_text and analytics_text.strip():
        out.append("")
        out.append(analytics_text.strip())
        out.append("")

    out.extend([
        "",
        "Lakukan seluruh pipeline analisis sesuai instruksi system prompt, "
        "lalu kembalikan HANYA satu objek JSON sesuai skema pada output_format.md.",
    ])

    return "\n".join(out)
