"""
analytics_parser.py

Membaca file CSV export dari YouTube Studio Analytics dan menghasilkan
ringkasan terstruktur yang bisa diinjeksikan ke prompt AI sebagai konteks
channel-specific untuk prediksi performa yang lebih akurat.

## Format CSV yang Didukung

YouTube Studio menyediakan beberapa tipe export. Parser ini mendeteksi dan
mendukung tipe-tipe berikut secara otomatis:

1. **Overview / Ringkasan Channel** — tab "Overview" di YouTube Analytics
   Kolom umum: Video title, Views, Watch time (hours), Subscribers, Impressions,
   Impressions click-through rate (%), Average view duration

2. **Content Report / Per Video** — tab "Content" → export semua video
   Kolom umum: Video title, Views, Watch time (hours), Impressions CTR (%),
   Average view duration, Likes, Comments

3. **Audience / Demografis** — tab "Audience"
   Biasanya berisi info age/gender/geography (format berbeda, diparse secara best-effort)

4. **Reach / Jangkauan** — tab "Reach"
   Kolom: Impressions, Impressions CTR, Views, Watch time

Cara export dari YouTube Studio:
- Buka studio.youtube.com → Analytics
- Pilih tab (Overview / Content / Reach / Audience)
- Klik tombol "Export current view" (ikon ↓) → Download .csv
- Bisa export beberapa tab sekaligus dan upload semua ke aplikasi

Parser ini toleran terhadap variasi format: header dengan karakter ekstra,
baris kosong, koma desimal yang berbeda (1,234.5 vs 1.234,5), dan nama kolom
yang sedikit berbeda antar bahasa YouTube Studio (ID / EN).
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ── Normalisasi nama kolom ────────────────────────────────────────────────────

# Map dari berbagai variasi nama kolom (EN/ID, YouTube Studio versi berbeda)
# ke nama internal yang konsisten.
_COL_MAP: Dict[str, str] = {
    # Judul video
    "video title": "title",
    "judul video": "title",
    "content": "title",
    "konten": "title",

    # Views
    "views": "views",
    "tayangan": "views",
    "penayangan": "views",

    # Watch time
    "watch time (hours)": "watch_time_hours",
    "watch time": "watch_time_hours",
    "waktu tonton (jam)": "watch_time_hours",
    "waktu tonton": "watch_time_hours",

    # Impressions
    "impressions": "impressions",
    "tayangan thumbnail": "impressions",
    "impresi": "impressions",

    # CTR
    "impressions click-through rate (%)": "ctr_pct",
    "impressions ctr (%)": "ctr_pct",
    "impressions click-through rate": "ctr_pct",
    "ctr (%)": "ctr_pct",
    "rasio klik tayang (%)": "ctr_pct",
    "rasio klik-tayang (%)": "ctr_pct",
    "click through rate (%)": "ctr_pct",

    # Average view duration
    "average view duration": "avg_duration",
    "average view duration (hh:mm:ss)": "avg_duration",
    "durasi tonton rata-rata": "avg_duration",
    "rata-rata durasi tonton": "avg_duration",

    # Average percentage viewed
    "average percentage viewed (%)": "avg_pct_viewed",
    "persentase tonton rata-rata (%)": "avg_pct_viewed",

    # Subscribers
    "subscribers": "subscribers_gained",
    "subscribers gained": "subscribers_gained",
    "subscribers lost": "subscribers_lost",
    "pelanggan": "subscribers_gained",
    "pelanggan baru": "subscribers_gained",

    # Likes
    "likes": "likes",
    "suka": "likes",

    # Comments
    "comments": "comments",
    "komentar": "comments",

    # Revenue (opsional)
    "estimated revenue (usd)": "revenue_usd",
    "revenue (usd)": "revenue_usd",
}


def _normalize_col(raw: str) -> str:
    """Normalisasi nama kolom: lowercase, strip whitespace & karakter BOM."""
    return raw.strip().lower().lstrip("\ufeff").strip('"').strip()


def _parse_number(val: str) -> Optional[float]:
    """
    Parse angka dari string dengan toleransi format:
    - 1,234.56  (EN locale)
    - 1.234,56  (ID/EU locale)
    - 1234.56
    - --  (placeholder kosong)
    """
    if not val:
        return None
    val = val.strip().strip('"').replace("%", "").replace("−", "-")
    if val in ("--", "-", "N/A", "n/a", ""):
        return None
    # Deteksi locale: jika ada koma setelah titik, itu EN (1,234.56)
    # Jika ada titik setelah koma, itu ID/EU (1.234,56)
    if "," in val and "." in val:
        if val.index(".") > val.index(","):
            # EN: 1,234.56 → hapus koma
            val = val.replace(",", "")
        else:
            # ID/EU: 1.234,56 → hapus titik, ganti koma dengan titik
            val = val.replace(".", "").replace(",", ".")
    elif "," in val:
        # Mungkin desimal ID: 4,5 → 4.5
        val = val.replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return None


def _parse_duration_to_seconds(val: str) -> Optional[float]:
    """Parse HH:MM:SS atau MM:SS ke detik."""
    if not val:
        return None
    val = val.strip().strip('"')
    parts = val.split(":")
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        return None
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return None


def _fmt(val: Optional[float], decimals: int = 1, suffix: str = "") -> str:
    if val is None:
        return "N/A"
    return f"{val:.{decimals}f}{suffix}"


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class VideoStat:
    title: str
    views: Optional[float] = None
    watch_time_hours: Optional[float] = None
    impressions: Optional[float] = None
    ctr_pct: Optional[float] = None
    avg_duration_seconds: Optional[float] = None
    avg_pct_viewed: Optional[float] = None
    subscribers_gained: Optional[float] = None
    likes: Optional[float] = None
    comments: Optional[float] = None


@dataclass
class ChannelAnalyticsSummary:
    """Ringkasan terstruktur analytics satu channel, siap diinjeksi ke prompt."""

    channel_id: str = ""
    source_files: List[str] = field(default_factory=list)
    total_videos_analyzed: int = 0

    # Rata-rata channel
    avg_ctr_pct: Optional[float] = None
    avg_retention_pct: Optional[float] = None          # dari avg_pct_viewed
    avg_view_duration_seconds: Optional[float] = None
    avg_views_per_video: Optional[float] = None
    avg_impressions_per_video: Optional[float] = None

    # Top performers (5 video terbaik berdasarkan views)
    top_videos_by_views: List[VideoStat] = field(default_factory=list)

    # Top performers berdasarkan CTR
    top_videos_by_ctr: List[VideoStat] = field(default_factory=list)

    # Top performers berdasarkan retensi
    top_videos_by_retention: List[VideoStat] = field(default_factory=list)

    # Pola yang dideteksi
    notes: List[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return self.total_videos_analyzed == 0

    def to_prompt_text(self) -> str:
        """
        Menghasilkan teks yang siap diinjeksikan ke dalam prompt AI.
        Format dirancang agar mudah dibaca oleh LLM dan informatif bagi
        prediksi CTR, retensi, viral potential, dll.
        """
        if self.is_empty():
            return ""

        lines = [
            "## DATA ANALYTICS CHANNEL (REAL DATA — GUNAKAN UNTUK KALIBRASI PREDIKSI PERFORMA)",
            "",
            f"Data ini berasal dari {len(self.source_files)} file analytics yang diupload pengguna "
            f"({self.total_videos_analyzed} video dianalisis).",
            "",
            "### Rata-Rata Performa Channel",
        ]

        if self.avg_ctr_pct is not None:
            lines.append(f"- **CTR rata-rata channel:** {_fmt(self.avg_ctr_pct)}%")
        if self.avg_retention_pct is not None:
            lines.append(f"- **Retensi rata-rata (% ditonton):** {_fmt(self.avg_retention_pct)}%")
        if self.avg_view_duration_seconds is not None:
            m = int(self.avg_view_duration_seconds // 60)
            s = int(self.avg_view_duration_seconds % 60)
            lines.append(f"- **Durasi tonton rata-rata:** {m}:{s:02d} menit")
        if self.avg_views_per_video is not None:
            lines.append(f"- **Views rata-rata per video:** {int(self.avg_views_per_video):,}")
        if self.avg_impressions_per_video is not None:
            lines.append(f"- **Impressions rata-rata per video:** {int(self.avg_impressions_per_video):,}")

        if self.top_videos_by_views:
            lines += ["", "### 5 Video Terbaik (berdasarkan Views)"]
            for i, v in enumerate(self.top_videos_by_views[:5], 1):
                parts = [f"{i}. \"{v.title}\""]
                if v.views is not None:
                    parts.append(f"Views: {int(v.views):,}")
                if v.ctr_pct is not None:
                    parts.append(f"CTR: {_fmt(v.ctr_pct)}%")
                if v.avg_pct_viewed is not None:
                    parts.append(f"Retensi: {_fmt(v.avg_pct_viewed)}%")
                elif v.avg_duration_seconds is not None:
                    m = int(v.avg_duration_seconds // 60)
                    s = int(v.avg_duration_seconds % 60)
                    parts.append(f"Avg duration: {m}:{s:02d}")
                lines.append(" | ".join(parts))

        if self.top_videos_by_ctr and any(
            v.ctr_pct != (self.top_videos_by_views[i].ctr_pct if i < len(self.top_videos_by_views) else None)
            for i, v in enumerate(self.top_videos_by_ctr[:3])
        ):
            lines += ["", "### 3 Video CTR Tertinggi"]
            for i, v in enumerate(self.top_videos_by_ctr[:3], 1):
                ctr_str = _fmt(v.ctr_pct, 2) + "%" if v.ctr_pct is not None else "N/A"
                views_str = f"{int(v.views):,}" if v.views is not None else "N/A"
                lines.append(f"{i}. \"{v.title}\" — CTR: {ctr_str}, Views: {views_str}")

        if self.top_videos_by_retention:
            lines += ["", "### 3 Video Retensi Tertinggi"]
            for i, v in enumerate(self.top_videos_by_retention[:3], 1):
                ret_str = _fmt(v.avg_pct_viewed, 1) + "%" if v.avg_pct_viewed is not None else "N/A"
                lines.append(f"{i}. \"{v.title}\" — Retensi: {ret_str}")

        if self.notes:
            lines += ["", "### Pola yang Terdeteksi dari Data"]
            for note in self.notes:
                lines.append(f"- {note}")

        lines += [
            "",
            "### Instruksi Kalibrasi untuk AI",
            "Gunakan data di atas sebagai **baseline konkret** saat mengisi `prediksi_performa` dan `skor_growth`:",
            "- Jika CTR prediksi di atas rata-rata channel, jelaskan MENGAPA thumbnail/judul ini lebih kuat dari pola yang ada.",
            "- Jika retensi prediksi di atas rata-rata, sebutkan elemen spesifik (hook, struktur, durasi) yang mendorong retensi lebih tinggi.",
            "- Prediksi views/impressions harus mengacu pada skala channel ini (bukan angka generik).",
            "- Kalau tidak ada data relevan untuk aspek tertentu, nyatakan secara eksplisit.",
            "",
        ]

        return "\n".join(lines)


# ── CSV Parser ────────────────────────────────────────────────────────────────

class AnalyticsParseError(Exception):
    pass


def _detect_csv_delimiter(sample: str) -> str:
    """Deteksi delimiter: koma atau titik koma (Excel ID biasanya pakai ;)."""
    comma_count = sample.count(",")
    semicolon_count = sample.count(";")
    return ";" if semicolon_count > comma_count else ","


def _parse_csv_to_rows(text: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Parse CSV YouTube Studio menjadi (header_list, rows_list).

    YouTube Studio kadang menambahkan:
    - Baris metadata di awal (judul tabel, periode, dll.) sebelum header kolom
    - Baris total/aggregate di akhir (biasanya baris pertama setelah header)
    - BOM character di awal file

    Strategi: scan baris dari atas, cari baris pertama yang berisi ≥2 kolom
    yang bisa dikenali sebagai header. Abaikan baris sebelumnya.
    """
    # Strip BOM
    text = text.lstrip("\ufeff")

    lines = text.splitlines()
    if not lines:
        raise AnalyticsParseError("File CSV kosong.")

    # Deteksi delimiter dari beberapa baris pertama
    sample = "\n".join(lines[:10])
    delim = _detect_csv_delimiter(sample)

    # Cari baris header: baris pertama yang punya ≥1 kolom yang dikenali
    header_line_idx = None
    header_cols: List[str] = []

    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        cols = [c.strip().strip('"') for c in line.split(delim)]
        normalized = [_COL_MAP.get(_normalize_col(c), "") for c in cols]
        recognized = sum(1 for n in normalized if n)
        if recognized >= 1 and len(cols) >= 2:
            header_line_idx = idx
            header_cols = [_normalize_col(c) for c in cols]
            break

    if header_line_idx is None:
        raise AnalyticsParseError(
            "Tidak bisa menemukan header kolom yang dikenali di file CSV ini. "
            "Pastikan file ini adalah export langsung dari YouTube Studio Analytics."
        )

    # Parse baris data setelah header
    rows: List[Dict[str, str]] = []
    for line in lines[header_line_idx + 1:]:
        if not line.strip():
            continue
        vals = [v.strip().strip('"') for v in line.split(delim)]
        # Pad atau crop ke panjang header
        while len(vals) < len(header_cols):
            vals.append("")
        row = {header_cols[i]: vals[i] for i in range(len(header_cols))}
        rows.append(row)

    return header_cols, rows


def parse_analytics_csv(
    file_content: bytes,
    filename: str = "analytics.csv",
) -> List[VideoStat]:
    """
    Parse satu file CSV YouTube Studio Analytics.

    Args:
        file_content: isi file dalam bytes (UTF-8 atau UTF-8 BOM).
        filename: nama file (dipakai hanya untuk pesan error).

    Returns:
        List[VideoStat] — satu entry per baris data.
        List bisa kosong jika file tidak berisi data per-video yang dikenali.

    Raises:
        AnalyticsParseError jika file tidak bisa diparsing sama sekali.
    """
    try:
        text = file_content.decode("utf-8-sig", errors="replace")
    except Exception as exc:
        raise AnalyticsParseError(f"Gagal membaca file '{filename}': {exc}") from exc

    try:
        header_cols, rows = _parse_csv_to_rows(text)
    except AnalyticsParseError:
        raise
    except Exception as exc:
        raise AnalyticsParseError(f"Error saat parse CSV '{filename}': {exc}") from exc

    # Map header ke internal names
    col_internal = {col: _COL_MAP.get(col, col) for col in header_cols}

    stats: List[VideoStat] = []

    for row in rows:
        # Cari kolom title
        title = ""
        for col, internal in col_internal.items():
            if internal == "title":
                title = row.get(col, "").strip().strip('"')
                break

        # Lewati baris aggregate/total (YouTube Studio sering taruh "Total" di baris pertama)
        if not title or title.lower() in ("total", "totals", "-", "--"):
            continue

        stat = VideoStat(title=title)

        for col, internal in col_internal.items():
            raw = row.get(col, "")
            if not raw:
                continue

            if internal == "views":
                stat.views = _parse_number(raw)
            elif internal == "watch_time_hours":
                stat.watch_time_hours = _parse_number(raw)
            elif internal == "impressions":
                stat.impressions = _parse_number(raw)
            elif internal == "ctr_pct":
                stat.ctr_pct = _parse_number(raw)
            elif internal == "avg_duration":
                stat.avg_duration_seconds = _parse_duration_to_seconds(raw)
            elif internal == "avg_pct_viewed":
                stat.avg_pct_viewed = _parse_number(raw)
            elif internal == "subscribers_gained":
                stat.subscribers_gained = _parse_number(raw)
            elif internal == "likes":
                stat.likes = _parse_number(raw)
            elif internal == "comments":
                stat.comments = _parse_number(raw)

        stats.append(stat)

    return stats


# ── Aggregator ────────────────────────────────────────────────────────────────

def _safe_avg(values: List[Optional[float]]) -> Optional[float]:
    valid = [v for v in values if v is not None]
    return sum(valid) / len(valid) if valid else None


def build_channel_summary(
    channel_id: str,
    parsed_files: List[Tuple[str, List[VideoStat]]],
) -> ChannelAnalyticsSummary:
    """
    Menggabungkan data dari satu atau lebih file CSV yang sudah diparsing
    menjadi satu ChannelAnalyticsSummary yang siap diinjeksi ke prompt.

    Args:
        channel_id: ID channel (misal "suara_filsuf").
        parsed_files: list of (filename, list_of_VideoStat).
    """
    summary = ChannelAnalyticsSummary(channel_id=channel_id)
    summary.source_files = [fname for fname, _ in parsed_files]

    # Gabungkan semua VideoStat, deduplikasi berdasarkan judul
    all_stats: Dict[str, VideoStat] = {}
    for _fname, stats in parsed_files:
        for stat in stats:
            key = stat.title.lower().strip()
            if key not in all_stats:
                all_stats[key] = stat
            else:
                # Merge: isi field yang kosong dari file sebelumnya
                existing = all_stats[key]
                if existing.views is None:
                    existing.views = stat.views
                if existing.ctr_pct is None:
                    existing.ctr_pct = stat.ctr_pct
                if existing.avg_pct_viewed is None:
                    existing.avg_pct_viewed = stat.avg_pct_viewed
                if existing.avg_duration_seconds is None:
                    existing.avg_duration_seconds = stat.avg_duration_seconds
                if existing.impressions is None:
                    existing.impressions = stat.impressions

    stats_list = list(all_stats.values())
    summary.total_videos_analyzed = len(stats_list)

    if not stats_list:
        return summary

    # Rata-rata channel
    summary.avg_ctr_pct = _safe_avg([s.ctr_pct for s in stats_list])
    summary.avg_retention_pct = _safe_avg([s.avg_pct_viewed for s in stats_list])
    summary.avg_view_duration_seconds = _safe_avg([s.avg_duration_seconds for s in stats_list])
    summary.avg_views_per_video = _safe_avg([s.views for s in stats_list])
    summary.avg_impressions_per_video = _safe_avg([s.impressions for s in stats_list])

    # Top by views
    by_views = sorted(
        [s for s in stats_list if s.views is not None],
        key=lambda s: s.views,
        reverse=True,
    )
    summary.top_videos_by_views = by_views[:5]

    # Top by CTR
    by_ctr = sorted(
        [s for s in stats_list if s.ctr_pct is not None],
        key=lambda s: s.ctr_pct,
        reverse=True,
    )
    summary.top_videos_by_ctr = by_ctr[:3]

    # Top by retensi
    by_retention = sorted(
        [s for s in stats_list if s.avg_pct_viewed is not None],
        key=lambda s: s.avg_pct_viewed,
        reverse=True,
    )
    summary.top_videos_by_retention = by_retention[:3]

    # Deteksi pola otomatis
    notes: List[str] = []

    if summary.avg_ctr_pct is not None:
        if summary.avg_ctr_pct >= 8:
            notes.append(
                f"CTR channel sangat tinggi ({_fmt(summary.avg_ctr_pct)}%) — thumbnail dan judul yang ada "
                "terbukti sangat menarik klik; pertahankan pola visual dan copywriting yang sudah berhasil."
            )
        elif summary.avg_ctr_pct >= 5:
            notes.append(
                f"CTR channel di atas rata-rata industri ({_fmt(summary.avg_ctr_pct)}%) — ada ruang untuk "
                "eksperimen judul/thumbnail yang lebih berani tanpa risiko besar."
            )
        elif summary.avg_ctr_pct < 3:
            notes.append(
                f"CTR channel masih rendah ({_fmt(summary.avg_ctr_pct)}%) — prioritaskan eksperimen judul "
                "dengan angka/kejutan/pertanyaan, dan thumbnail dengan wajah ekspresi kuat atau kontras tinggi."
            )

    if summary.avg_retention_pct is not None:
        if summary.avg_retention_pct >= 50:
            notes.append(
                f"Retensi sangat tinggi ({_fmt(summary.avg_retention_pct)}%) — audiens channel ini sangat "
                "engaged; konten dengan struktur naratif panjang dan in-depth berpeluang besar."
            )
        elif summary.avg_retention_pct < 30:
            notes.append(
                f"Retensi masih rendah ({_fmt(summary.avg_retention_pct)}%) — fokus pada hook 0-15 detik "
                "yang lebih kuat, potong bagian pembuka yang panjang, dan tambahkan pattern interrupt setiap 60 detik."
            )

    if by_views and summary.avg_views_per_video:
        top_views = by_views[0].views or 0
        avg_views = summary.avg_views_per_video or 1
        if top_views > avg_views * 3:
            notes.append(
                f"Video terbaik (\"{by_views[0].title[:50]}\") punya views {top_views/avg_views:.1f}x "
                "di atas rata-rata — analisis pola hook, topik, dan thumbnail video ini untuk direplikasi."
            )

    if by_ctr and summary.avg_ctr_pct:
        top_ctr = by_ctr[0].ctr_pct or 0
        if top_ctr > (summary.avg_ctr_pct or 0) * 1.5:
            notes.append(
                f"CTR tertinggi dicapai oleh \"{by_ctr[0].title[:50]}\" ({_fmt(top_ctr)}%) — "
                "jauh di atas rata-rata; replikasi pola judul/thumbnail video ini."
            )

    summary.notes = notes
    return summary


# ── Public API ────────────────────────────────────────────────────────────────

def process_uploaded_analytics(
    channel_id: str,
    uploaded_files: List[Tuple[str, bytes]],
) -> Tuple[ChannelAnalyticsSummary, List[str]]:
    """
    Entry point utama: terima list file yang diupload user, parse, dan
    kembalikan ChannelAnalyticsSummary + list pesan error/warning.

    Args:
        channel_id: ID channel yang dipilih user.
        uploaded_files: list of (filename, file_bytes).

    Returns:
        (ChannelAnalyticsSummary, list_of_warnings)
    """
    parsed: List[Tuple[str, List[VideoStat]]] = []
    warnings: List[str] = []

    for fname, fbytes in uploaded_files:
        try:
            stats = parse_analytics_csv(fbytes, fname)
            if not stats:
                warnings.append(
                    f"⚠️ File '{fname}' berhasil dibaca tapi tidak mengandung data video yang dikenali. "
                    "Pastikan ini adalah export 'Content' atau 'Overview' dari YouTube Studio."
                )
            else:
                parsed.append((fname, stats))
        except AnalyticsParseError as exc:
            warnings.append(f"❌ Gagal parse '{fname}': {exc}")

    summary = build_channel_summary(channel_id, parsed)
    return summary, warnings
