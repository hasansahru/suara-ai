"""
youtube_utils.py

Helper untuk mengekstrak video ID dari URL YouTube, mengambil metadata dasar
(via endpoint oEmbed publik, tanpa API key), dan mengambil transkrip video
(via youtube-transcript-api, tanpa API key).

Semua fungsi di sini didesain "best effort": jika YouTube memblokir/membatasi
pengambilan transkrip otomatis (sering terjadi karena rate limiting/region),
fungsi akan melempar YouTubeUtilsError dengan pesan yang jelas, dan UI akan
menyarankan pengguna untuk mengunggah transkrip manual sebagai fallback.

## Mengatasi Error 429 / IP Block YouTube

YouTube secara aktif memblokir request otomatis, terutama dari:
- IP yang terlalu sering request dalam waktu singkat (rate limiting)
- IP VPS/cloud provider (AWS, GCP, Azure, Render, Railway, dsb.)
- IP residensial yang request terlalu cepat berulang kali

Solusi yang tersedia (urutan dari termudah ke terkuat):

1. **Cookie browser** (GRATIS, paling efektif untuk IP residensial):
   - Login ke YouTube di browser
   - Export cookies sebagai file Netscape/Mozilla (ekstensi "Get cookies.txt LOCALLY")
   - Upload file tersebut di sidebar aplikasi → opsi "Cookie YouTube"
   - Library akan menggunakan session browser kamu → YouTube menganggap ini request normal

2. **Proxy Generic** (butuh proxy HTTP/HTTPS yang bisa akses YouTube):
   - Bisa pakai proxy gratis (kurang stabil) atau berbayar
   - Isi HTTP/HTTPS proxy URL di sidebar

3. **Webshare Rotating Residential Proxy** (paling stabil untuk production):
   - Daftar di https://www.webshare.io/ (ada free tier terbatas)
   - Isi username & password di sidebar
   - Rotating IP otomatis, didukung resmi oleh youtube-transcript-api

4. **Upload transkrip manual**:
   - Buka video di YouTube → klik "..." → "Show transcript"
   - Copy-paste teks transkrip ke kolom upload di sidebar
"""

from __future__ import annotations

import re
import time
import random
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

import requests

logger = logging.getLogger(__name__)

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
        RequestBlocked,
        IpBlocked,
    )
    _YTT_AVAILABLE = True
except ImportError:
    YouTubeTranscriptApi = None
    TranscriptsDisabled = NoTranscriptFound = VideoUnavailable = Exception
    RequestBlocked = IpBlocked = Exception
    _YTT_AVAILABLE = False

try:
    from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig
    _PROXY_CLASSES_AVAILABLE = True
except ImportError:
    GenericProxyConfig = None
    WebshareProxyConfig = None
    _PROXY_CLASSES_AVAILABLE = False

# ── Pesan panduan solusi yang ditampilkan ke user saat 429 / IP block ────────

_BLOCKED_HELP = """
**YouTube memblokir pengambilan transkrip dari IP ini (error 429/IP block).**

Ini sangat umum terjadi, terutama jika:
- Kamu request terlalu sering dalam waktu singkat
- Aplikasi berjalan di server cloud (VPS, Railway, Render, dsb.)

**Solusi (pilih salah satu):**

① **Cookie YouTube** *(gratis, paling mudah)*
   - Login ke YouTube di Chrome/Firefox
   - Install ekstensi **"Get cookies.txt LOCALLY"**
   - Kunjungi youtube.com → klik ikon ekstensi → Export cookies
   - Upload file `.txt` tersebut di sidebar → bagian "🍪 Cookie YouTube"
   - Aplikasi akan menggunakan sesi browser kamu

② **Tunggu beberapa menit** lalu coba lagi
   *(YouTube biasanya mencabut block sementara setelah ~5-15 menit)*

③ **Upload transkrip manual**
   - Buka video di YouTube → klik ikon `...` → "Show transcript"
   - Salin semua teks → paste ke kolom upload transkrip di sidebar

④ **Proxy** *(untuk server cloud / IP yang diblokir permanen)*
   - Aktifkan opsi Proxy YouTube di sidebar
   - Webshare Residential Proxy paling stabil (ada free tier di webshare.io)
""".strip()


class YouTubeUtilsError(Exception):
    """Error umum untuk semua operasi terkait YouTube di file ini."""


@dataclass
class TranscriptSegment:
    start: float
    duration: float
    text: str

    @property
    def end(self) -> float:
        return self.start + self.duration


@dataclass
class VideoTranscript:
    video_id: str
    language: str
    segments: List[TranscriptSegment] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return " ".join(seg.text.strip() for seg in self.segments if seg.text.strip())

    def slice_by_time(self, start_seconds: float, end_seconds: float) -> "VideoTranscript":
        """Mengembalikan transkrip baru yang hanya berisi segmen di rentang waktu tertentu."""
        sliced = [
            seg for seg in self.segments
            if seg.start < end_seconds and seg.end > start_seconds
        ]
        return VideoTranscript(video_id=self.video_id, language=self.language, segments=sliced)


YOUTUBE_URL_PATTERNS = [
    re.compile(r"(?:youtube\.com/watch\?v=)([\w-]{11})"),
    re.compile(r"(?:youtu\.be/)([\w-]{11})"),
    re.compile(r"(?:youtube\.com/shorts/)([\w-]{11})"),
    re.compile(r"(?:youtube\.com/embed/)([\w-]{11})"),
    re.compile(r"(?:youtube\.com/live/)([\w-]{11})"),
]


def extract_video_id(url: str) -> Optional[str]:
    """Mengekstrak 11-karakter video ID dari berbagai format URL YouTube."""
    if not url:
        return None

    url = url.strip()

    # Coba parse query string ?v= secara eksplisit dahulu (lebih robust untuk URL dengan param tambahan).
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if "v" in qs and len(qs["v"][0]) == 11:
            return qs["v"][0]
    except Exception:
        pass

    for pattern in YOUTUBE_URL_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)

    # Jika user hanya menempel video ID mentah (11 karakter, tanpa spasi/slash).
    if re.fullmatch(r"[\w-]{11}", url):
        return url

    return None


def format_seconds(total_seconds: float) -> str:
    """Format detik menjadi mm:ss atau hh:mm:ss."""
    total_seconds = int(round(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def parse_time_to_seconds(time_str: str) -> Optional[float]:
    """Parse string 'mm:ss' atau 'hh:mm:ss' menjadi total detik. Mengembalikan None jika gagal."""
    if not time_str:
        return None
    parts = time_str.strip().split(":")
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        return None

    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    return None


def get_video_metadata(url: str, timeout: int = 8) -> dict:
    """
    Mengambil metadata dasar video (judul, author, thumbnail) via endpoint oEmbed
    publik YouTube. Tidak memerlukan API key.
    """
    oembed_url = "https://www.youtube.com/oembed"
    try:
        response = requests.get(
            oembed_url, params={"url": url, "format": "json"}, timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        return {
            "title": data.get("title", ""),
            "author_name": data.get("author_name", ""),
            "thumbnail_url": data.get("thumbnail_url", ""),
        }
    except requests.RequestException as exc:
        raise YouTubeUtilsError(
            f"Gagal mengambil metadata video (cek koneksi internet / URL valid?): {exc}"
        ) from exc
    except ValueError as exc:
        raise YouTubeUtilsError(f"Respons metadata video tidak valid: {exc}") from exc


@dataclass
class ProxySetting:
    """Konfigurasi proxy untuk mengatasi IP block YouTube saat mengambil transkrip.

    mode:
        - "none"     : tidak pakai proxy (default).
        - "generic"  : proxy HTTP/HTTPS biasa (http_url / https_url).
        - "webshare" : rotating residential proxy dari Webshare (rekomendasi resmi
                        youtube-transcript-api untuk mengatasi IP block secara konsisten).
    """

    mode: str = "none"
    http_url: Optional[str] = None
    https_url: Optional[str] = None
    webshare_username: Optional[str] = None
    webshare_password: Optional[str] = None
    webshare_locations: Optional[List[str]] = None
    webshare_retries_when_blocked: int = 10


def build_proxy_config(setting: Optional[ProxySetting]):
    """Mengubah ProxySetting menjadi objek proxy_config youtube-transcript-api, atau None."""
    if setting is None or setting.mode == "none":
        return None

    if setting.mode == "webshare":
        if not _PROXY_CLASSES_AVAILABLE or WebshareProxyConfig is None:
            raise YouTubeUtilsError(
                "Versi 'youtube-transcript-api' yang terinstal tidak mendukung WebshareProxyConfig. "
                "Jalankan: pip install -U youtube-transcript-api"
            )
        if not setting.webshare_username or not setting.webshare_password:
            raise YouTubeUtilsError("Username/password Webshare belum diisi.")
        kwargs = {
            "proxy_username": setting.webshare_username,
            "proxy_password": setting.webshare_password,
            "retries_when_blocked": setting.webshare_retries_when_blocked,
        }
        if setting.webshare_locations:
            kwargs["filter_ip_locations"] = setting.webshare_locations
        return WebshareProxyConfig(**kwargs)

    if setting.mode == "generic":
        if not _PROXY_CLASSES_AVAILABLE or GenericProxyConfig is None:
            raise YouTubeUtilsError(
                "Versi 'youtube-transcript-api' yang terinstal tidak mendukung GenericProxyConfig. "
                "Jalankan: pip install -U youtube-transcript-api"
            )
        if not setting.http_url and not setting.https_url:
            raise YouTubeUtilsError("Isi minimal salah satu dari HTTP Proxy URL / HTTPS Proxy URL.")
        return GenericProxyConfig(
            http_url=setting.http_url or setting.https_url,
            https_url=setting.https_url or setting.http_url,
        )

    raise YouTubeUtilsError(f"Mode proxy tidak dikenal: '{setting.mode}'")


def _build_cookie_session(cookie_path: str):
    """
    Membangun `requests.Session` dengan cookie dari file Netscape/Mozilla
    (hasil ekstensi "Get cookies.txt LOCALLY") dimuat ke dalamnya.

    Ini menggantikan parameter `cookies=` lama pada YouTubeTranscriptApi
    (sudah dihapus sejak v1.0+) dengan parameter resmi yang masih didukung:
    `http_client=<requests.Session>`.

    Catatan: fitur ini tetap "best effort" — YouTube dapat menolak sesi
    yang diekspor browser kapan saja terlepas dari implementasi ini, karena
    autentikasi cookie untuk transkrip memang belum sepenuhnya stabil di
    sisi youtube-transcript-api sendiri. Jika cookie tetap gagal, proxy
    (mis. Webshare) adalah alternatif yang lebih stabil untuk deployment
    di server cloud.
    """
    import http.cookiejar
    from requests import Session

    jar = http.cookiejar.MozillaCookieJar()
    try:
        jar.load(cookie_path, ignore_discard=True, ignore_expires=True)
    except Exception as exc:
        raise YouTubeUtilsError(
            f"File cookies.txt tidak valid atau rusak: {exc}. "
            "Pastikan diekspor lewat ekstensi \"Get cookies.txt LOCALLY\" dalam format Netscape."
        ) from exc

    if len(jar) == 0:
        raise YouTubeUtilsError(
            "File cookies.txt yang diupload kosong (tidak ada cookie di dalamnya)."
        )

    session = Session()
    session.cookies = jar
    return session


def _is_rate_limit_error(exc: Exception) -> bool:
    """Mendeteksi apakah exception adalah 429 / IP block dari YouTube."""
    msg = str(exc).lower()
    keywords = [
        "429",
        "too many",
        "rate limit",
        "blocking requests",
        "ipblocked",
        "requestblocked",
        "max retries exceeded",
    ]
    return any(kw in msg for kw in keywords)


def _fetch_transcript_with_retry(
    ytt_api,
    video_id: str,
    preferred_languages: List[str],
    max_retries: int = 3,
    base_delay: float = 3.0,
) -> "VideoTranscript":
    """
    Mencoba mengambil transkrip dengan retry + exponential backoff jika kena 429.

    Delay antar retry: base_delay * 2^attempt + jitter acak 0-2 detik.
    Contoh: retry 1 → ~3 detik, retry 2 → ~6 detik, retry 3 → ~12 detik.
    """
    last_exc = None

    for attempt in range(max_retries + 1):
        try:
            transcript_list = ytt_api.list(video_id)
            transcript = None

            try:
                transcript = transcript_list.find_transcript(preferred_languages)
            except NoTranscriptFound:
                # Fallback: ambil transkrip apa pun yang ada
                for t in transcript_list:
                    transcript = t
                    break

            if transcript is None:
                raise YouTubeUtilsError("Tidak ada transkrip yang tersedia untuk video ini.")

            fetched = transcript.fetch()
            segments = [
                TranscriptSegment(start=item.start, duration=item.duration, text=item.text)
                for item in fetched
            ]
            return VideoTranscript(
                video_id=video_id,
                language=transcript.language_code,
                segments=segments,
            )

        except YouTubeUtilsError:
            raise  # jangan retry error yang kita buat sendiri

        except (TranscriptsDisabled, VideoUnavailable, NoTranscriptFound):
            raise  # jangan retry error yang memang permanen

        except (RequestBlocked, IpBlocked) as exc:
            last_exc = exc
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 2)
                logger.warning(
                    "Transkrip: IP block/request blocked (attempt %d/%d), retry setelah %.1f detik...",
                    attempt + 1, max_retries, delay,
                )
                time.sleep(delay)
                continue
            # Semua retry habis
            raise YouTubeUtilsError(_BLOCKED_HELP) from exc

        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if _is_rate_limit_error(exc):
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 2)
                    logger.warning(
                        "Transkrip: 429/rate limit (attempt %d/%d), retry setelah %.1f detik...",
                        attempt + 1, max_retries, delay,
                    )
                    time.sleep(delay)
                    continue
                # Semua retry habis — tampilkan panduan solusi lengkap
                raise YouTubeUtilsError(_BLOCKED_HELP) from exc
            # Error lain yang tidak diketahui, langsung raise
            raise YouTubeUtilsError(
                f"Gagal mengambil transkrip otomatis: {exc}\n\n"
                "Silakan unggah transkrip manual sebagai alternatif."
            ) from exc

    # Seharusnya tidak pernah dicapai, tapi untuk keamanan:
    raise YouTubeUtilsError(_BLOCKED_HELP) from last_exc


def get_video_transcript(
    video_id: str,
    preferred_languages: Optional[List[str]] = None,
    proxy_config=None,
    cookie_path: Optional[str] = None,
    max_retries: int = 3,
) -> VideoTranscript:
    """
    Mengambil transkrip video YouTube menggunakan youtube-transcript-api.

    Args:
        video_id: 11-karakter video ID.
        preferred_languages: urutan prioritas bahasa, default ["id", "en"].
        proxy_config: objek proxy_config (GenericProxyConfig/WebshareProxyConfig) dari
                       build_proxy_config(), opsional.
        cookie_path: path ke file cookies Netscape/Mozilla (dari browser) untuk
                      menghindari rate limiting YouTube. Paling efektif untuk IP residensial.
                      Export via ekstensi "Get cookies.txt LOCALLY" di Chrome/Firefox.
        max_retries: jumlah retry otomatis jika kena 429 (default 3, dengan backoff).

    Raises:
        YouTubeUtilsError: jika transkrip tidak tersedia / IP diblokir / semua retry gagal.
    """
    if not _YTT_AVAILABLE:
        raise YouTubeUtilsError(
            "Paket 'youtube-transcript-api' belum terinstal. Jalankan: pip install -r requirements.txt"
        )

    preferred_languages = preferred_languages or ["id", "en"]

    # Bangun instance API dengan proxy dan/atau cookie.
    #
    # CATATAN PENTING: sejak youtube-transcript-api v1.0+, parameter `cookies=`
    # pada constructor SUDAH TIDAK ADA (maintainer menonaktifkan cookie auth
    # bawaan karena tidak stabil dengan perubahan YouTube terbaru — lihat
    # source _api.py: "# Cookie auth has been temporarily disabled"). Memberi
    # `cookies=cookie_path` akan selalu melempar TypeError, membuat fitur
    # upload cookie di UI diam-diam TIDAK PERNAH terpakai walau tampak sukses.
    #
    # Solusi: bangun `requests.Session` sendiri, muat cookie Netscape/Mozilla
    # ke dalamnya, lalu suntikkan sebagai `http_client=` (parameter ini yang
    # resmi didukung untuk "share cookies" ke instance YouTubeTranscriptApi).
    try:
        kwargs = {}
        if proxy_config is not None:
            kwargs["proxy_config"] = proxy_config
        if cookie_path:
            http_client = _build_cookie_session(cookie_path)
            kwargs["http_client"] = http_client
        ytt_api = YouTubeTranscriptApi(**kwargs) if kwargs else YouTubeTranscriptApi()
    except YouTubeUtilsError:
        raise
    except Exception as exc:
        raise YouTubeUtilsError(f"Gagal menginisialisasi YouTubeTranscriptApi: {exc}") from exc

    try:
        return _fetch_transcript_with_retry(
            ytt_api=ytt_api,
            video_id=video_id,
            preferred_languages=preferred_languages,
            max_retries=max_retries,
        )

    except TranscriptsDisabled as exc:
        raise YouTubeUtilsError(
            "Transkrip dinonaktifkan oleh pemilik video ini. Silakan unggah transkrip manual."
        ) from exc
    except VideoUnavailable as exc:
        raise YouTubeUtilsError("Video tidak tersedia, privat, atau sudah dihapus.") from exc
    except NoTranscriptFound as exc:
        raise YouTubeUtilsError(
            "Tidak ditemukan transkrip dalam bahasa yang didukung. "
            "Silakan unggah transkrip manual."
        ) from exc
    except YouTubeUtilsError:
        raise  # pesan sudah jelas, teruskan langsung


def transcript_from_raw_text(raw_text: str, video_id: str = "manual") -> VideoTranscript:
    """Membungkus teks transkrip yang diunggah manual (tanpa timestamp) menjadi VideoTranscript."""
    cleaned = raw_text.strip()
    segment = TranscriptSegment(start=0.0, duration=0.0, text=cleaned)
    return VideoTranscript(video_id=video_id, language="manual", segments=[segment])
