"""
parser.py

Mem-parsing keluaran AI (yang diharapkan berupa JSON murni sesuai output_format.md)
menjadi dict Python, dengan beberapa lapis fallback untuk menangani kasus
AI menambahkan code fence ``` atau teks pembuka/penutup yang tidak diminta.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


class AIResponseParseError(Exception):
    """Dilempar saat respons AI gagal diparsing menjadi JSON yang valid."""


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    # Hilangkan ```json ... ``` atau ``` ... ```
    fence_pattern = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)
    match = fence_pattern.match(text)
    if match:
        return match.group(1).strip()
    return text


def _extract_first_json_object(text: str) -> str:
    """Ekstrak substring objek JSON pertama `{...}` menggunakan pencocokan kurung kurawal."""
    start = text.find("{")
    if start == -1:
        raise AIResponseParseError("Tidak ditemukan karakter '{' pada respons AI.")

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        char = text[i]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    raise AIResponseParseError("Objek JSON pada respons AI tidak lengkap/tidak seimbang kurung kurawalnya.")


def _repair_common_json_issues(text: str) -> str:
    """
    Memperbaiki kesalahan JSON kecil yang umum dilakukan model AI:
    - trailing comma sebelum `}` atau `]`
    - karakter kontrol mentah (newline/tab literal) di dalam string
    Ini BUKAN parser JSON penuh, hanya perbaikan ringan sebelum dicoba parse ulang.
    """
    # Hapus trailing comma: ",}" -> "}" dan ",]" -> "]"
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


def parse_mmss_to_seconds(value: Any) -> Optional[int]:
    """Mengubah string 'mm:ss' atau 'hh:mm:ss' menjadi total detik. None jika gagal parse."""
    if not isinstance(value, str):
        return None
    parts = value.strip().split(":")
    try:
        parts_int = [int(p) for p in parts]
    except ValueError:
        return None

    if len(parts_int) == 2:
        minutes, seconds = parts_int
        return minutes * 60 + seconds
    if len(parts_int) == 3:
        hours, minutes, seconds = parts_int
        return hours * 3600 + minutes * 60 + seconds
    return None


def enforce_shot_count(result: Dict[str, Any], shot_count: Optional[int]) -> Dict[str, Any]:
    """
    Memastikan `shots` (array paket per-shot, lihat output_format.md) tidak melebihi
    jumlah shots yang diminta pengguna.

    - Jika AI mengembalikan LEBIH dari `shot_count`: potong ke `shot_count` teratas
      (AI diinstruksikan mengurutkan dari paling kuat, jadi yang dipotong adalah yang terlemah).
    - Jika AI mengembalikan KURANG: dibiarkan apa adanya (video sumber mungkin memang
      tidak punya cukup momen kuat) — peringatan ditangani terpisah di app.py.
    - Tidak melakukan apa pun jika `shot_count` tidak diset atau key tidak ada/bukan list.
    """
    if not shot_count:
        return result

    shots = result.get("shots")
    if isinstance(shots, list) and len(shots) > shot_count:
        result["shots"] = shots[: int(shot_count)]

    return result


def get_shot_segment_list(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Mengambil daftar `segmen` dari tiap elemen `shots[]` (skema baru, lihat output_format.md),
    dalam bentuk list of dict yang sama dengan field `segmen_terbaik` versi lama, agar
    fungsi-fungsi lain (mis. check_segment_duration_mismatch) tetap bisa dipakai ulang.
    """
    shots = result.get("shots")
    if not isinstance(shots, list):
        return []
    segments: List[Dict[str, Any]] = []
    for shot in shots:
        if isinstance(shot, dict) and isinstance(shot.get("segmen"), dict):
            segments.append(shot["segmen"])
    return segments


def check_segment_duration_mismatch(
    segments: List[Dict[str, Any]],
    target_min_seconds: Optional[int],
    target_max_seconds: Optional[int],
    tolerance_seconds: int = 8,
) -> List[str]:
    """
    Membandingkan durasi tiap segmen/shot (`start_time`/`end_time`) terhadap target durasi
    yang diminta pengguna. Mengembalikan list pesan peringatan (bisa kosong) — TIDAK
    mengubah data, hanya untuk ditampilkan sebagai info ke pengguna.

    `segments` diharapkan berupa list of dict (mis. hasil `get_shot_segment_list(result)`
    untuk Output Type = Shorts), masing-masing punya key `start_time`/`end_time`.
    """
    warnings: List[str] = []
    if target_min_seconds is None and target_max_seconds is None:
        return warnings

    if not isinstance(segments, list):
        return warnings

    lo = (target_min_seconds or target_max_seconds or 0) - tolerance_seconds
    hi = (target_max_seconds or target_min_seconds or 0) + tolerance_seconds

    for idx, seg in enumerate(segments, start=1):
        if not isinstance(seg, dict):
            continue
        start_s = parse_mmss_to_seconds(seg.get("start_time"))
        end_s = parse_mmss_to_seconds(seg.get("end_time"))
        if start_s is None or end_s is None:
            continue
        actual_duration = end_s - start_s
        if actual_duration <= 0:
            warnings.append(f"Shot #{idx}: start_time/end_time tidak valid (durasi ≤ 0 detik).")
            continue
        if actual_duration < lo or actual_duration > hi:
            warnings.append(
                f"Shot #{idx}: durasi aktual ~{actual_duration} detik, di luar target "
                f"yang diminta (~{lo + tolerance_seconds}-{hi - tolerance_seconds} detik)."
            )

    return warnings


def parse_ai_response(raw_text: str) -> Dict[str, Any]:
    """
    Mem-parsing teks respons AI menjadi dict.

    Strategi (berurutan):
    1. Coba json.loads langsung.
    2. Hilangkan code fence ``` lalu coba lagi.
    3. Ekstrak substring objek JSON pertama (untuk kasus ada teks tambahan di luar JSON).
    4. Terapkan perbaikan ringan (trailing comma, dll) lalu coba lagi.

    Raises:
        AIResponseParseError jika semua strategi gagal. Jika respons tampak terpotong
        (kurung kurawal tidak seimbang), pesan error akan menyebutkan kemungkinan tersebut
        secara eksplisit.
    """
    if not raw_text or not raw_text.strip():
        raise AIResponseParseError("Respons AI kosong.")

    candidates = [raw_text, _strip_code_fences(raw_text)]

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue

    stripped = _strip_code_fences(raw_text)

    # FIX: sebelumnya, kasus "stripped kosong total" (mis. AI cuma mengembalikan
    # blok kode kosong seperti ```json\n``` tanpa isi) ikut masuk ke cabang yang
    # sama dengan "JSON terpotong di tengah", sehingga json.loads("") melempar
    # "Expecting value: line 1 column 1 (char 0)" dan pesan errornya SALAH
    # menuduh "kena batas max_tokens" — padahal stop_reason bukan max_tokens
    # sama sekali (kalau itu penyebabnya, ai_client.py sudah menangkapnya lebih
    # dulu dengan pesan yang berbeda, sebelum sampai ke parser ini). Dipisah
    # jadi pesan yang jujur soal apa yang sebenarnya terjadi.
    if not stripped:
        raise AIResponseParseError(
            "Respons AI KOSONG setelah menghapus code fence — sepertinya AI hanya "
            "mengembalikan blok kode kosong (```json ... ```) tanpa isi JSON sama sekali. "
            "Ini BUKAN kasus max_tokens terpotong. Penyebab paling umum: AI 'kehilangan giliran' "
            "menulis jawaban akhir setelah memakai skill tambahan (Web Search / Code Execution / "
            "Extended Thinking) sehingga tidak sempat menulis JSON-nya. Coba: (1) jalankan ulang — "
            "ini seringkali tidak konsisten, (2) matikan sementara skill tambahan di sidebar untuk "
            "isolasi penyebab, atau (3) ganti model jika terus berulang pada model yang sama."
        )

    try:
        extracted = _extract_first_json_object(stripped)
    except AIResponseParseError:
        # Kemungkinan respons terpotong sebelum `}` penutup pertama tercapai.
        repaired_full = _repair_common_json_issues(stripped)
        try:
            return json.loads(repaired_full)
        except json.JSONDecodeError as exc:
            raise AIResponseParseError(
                f"Gagal mem-parsing respons AI sebagai JSON: {exc}. "
                "Respons sepertinya TERPOTONG (kurung kurawal/siku tidak seimbang) — "
                "kemungkinan besar karena batas max_tokens tercapai. Coba kurangi jumlah "
                "shots/segmen, atau pilih durasi output yang lebih pendek."
            ) from exc

    try:
        return json.loads(extracted)
    except json.JSONDecodeError:
        pass

    try:
        repaired = _repair_common_json_issues(extracted)
        return json.loads(repaired)
    except json.JSONDecodeError as exc:
        raise AIResponseParseError(
            f"Gagal mem-parsing respons AI sebagai JSON: {exc}"
        ) from exc


def get_safe(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Ambil nilai dari dict bersarang dengan path dipisah titik, contoh: 'skor_growth.ctr.score'.
    Mengembalikan `default` jika path tidak ditemukan, tanpa melempar exception.
    """
    current: Any = data
    for key in path.split("."):
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current
