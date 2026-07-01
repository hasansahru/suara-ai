import json
import re

class AIResponseParseError(ValueError):
    """Exception khusus saat parsing respons AI gagal."""
    pass

def parse_ai_response(raw_text: str) -> dict:
    """
    Ekstrak dan parse JSON dari respons AI. 
    Dilengkapi dengan fitur auto-repair jika respons terpotong (truncated).
    """
    start_obj = raw_text.find('{')
    start_arr = raw_text.find('[')
    
    if start_obj == -1 and start_arr == -1:
        raise AIResponseParseError("Gagal menemukan struktur awal JSON ('{' atau '[') pada respons AI.")
    
    valid_indices = [idx for idx in (start_obj, start_arr) if idx != -1]
    first_bracket_idx = min(valid_indices)
    
    json_str = raw_text[first_bracket_idx:]
    
    # Bersihkan trailing markdown (```) di akhir teks yang sering membuat parsing gagal
    json_str = json_str.strip()
    json_str = re.sub(r'`+$', '', json_str).strip()
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as original_error:
        return _repair_and_parse_json(json_str, original_error)

def _repair_and_parse_json(json_str: str, original_error: Exception) -> dict:
    """
    Memperbaiki JSON yang terpotong dengan menutup string dan kurung yang terbuka,
    serta membersihkan trailing comma.
    """
    stack = []
    in_string = False
    escape_char = False
    
    for char in json_str:
        if in_string:
            if escape_char:
                escape_char = False
            elif char == '\\':
                escape_char = True
            elif char == '"':
                in_string = False
        else:
            if char == '"':
                in_string = True
            elif char in '{[':
                stack.append(char)
            elif char in '}]':
                if stack:
                    last = stack[-1]
                    if (char == '}' and last == '{') or (char == ']' and last == '['):
                        stack.pop()

    if in_string:
        json_str += '"'
        
    json_str = re.sub(r',\s*$', '', json_str)

    while stack:
        last = stack.pop()
        if last == '{':
            json_str = re.sub(r',\s*$', '', json_str)
            if json_str.strip().endswith(':'):
                json_str += ' null'
            json_str += '}'
        elif last == '[':
            json_str = re.sub(r',\s*$', '', json_str)
            json_str += ']'

    try:
        repaired_json = json.loads(json_str)
        if isinstance(repaired_json, dict):
            repaired_json['_is_repaired_partial_result'] = True
        return repaired_json
    except json.JSONDecodeError as repair_error:
        error_msg = (
            f"Gagal mem-parsing JSON. Teks terpotong terlalu parah untuk diselamatkan. "
            f"Error asli: {original_error}. Error setelah repair: {repair_error}."
        )
        raise AIResponseParseError(error_msg)

def enforce_shot_count(result: dict, shot_count: int) -> dict:
    """Potong array shots jika AI mengembalikan lebih dari yang diminta."""
    if "shots" in result and isinstance(result["shots"], list):
        if len(result["shots"]) > shot_count:
            result["shots"] = result["shots"][:shot_count]
    return result

def get_shot_segment_list(result: dict) -> list:
    """Ambil daftar informasi segmen waktu dari hasil."""
    segments = []
    if "shots" in result and isinstance(result["shots"], list):
        for shot in result["shots"]:
            if isinstance(shot, dict) and "segmen" in shot:
                segments.append(shot["segmen"])
    return segments

def check_segment_duration_mismatch(segments: list, target_min, target_max) -> list:
    """Verifikasi apakah durasi segmen di dalam target. Mengembalikan pesan peringatan jika melenceng."""
    warnings = []
    if target_min is None or target_max is None:
        return warnings
    
    def parse_time(t_str):
        parts = str(t_str).strip().split(":")
        try:
            parts = [float(p) for p in parts]
        except ValueError:
            return 0
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        return 0

    for i, seg in enumerate(segments):
        start_time = seg.get("start_time", "")
        end_time = seg.get("end_time", "")
        if start_time and end_time:
            start_s = parse_time(start_time)
            end_s = parse_time(end_time)
            duration = end_s - start_s
            
            if duration > 0:
                if duration < (target_min - 10) or duration > (target_max + 10):
                    warnings.append(
                        f"Durasi segmen shot #{i+1} ({duration} detik) di luar rentang target "
                        f"({target_min}-{target_max} detik)."
                    )
    
    return warnings
