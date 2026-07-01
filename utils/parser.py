import json
import re

def parse_ai_response(raw_text: str) -> dict:
    """
    Ekstrak dan parse JSON dari respons AI. 
    Dilengkapi dengan fitur auto-repair jika respons terpotong (truncated).
    """
    # 1. Cari kurung buka pertama untuk mengabaikan teks pengantar (markdown, dsb.)
    start_obj = raw_text.find('{')
    start_arr = raw_text.find('[')
    
    if start_obj == -1 and start_arr == -1:
        raise ValueError("Gagal menemukan struktur awal JSON ('{' atau '[') pada respons AI.")
    
    # Ambil indeks kurung kurawal/siku yang muncul lebih dulu
    valid_indices = [idx for idx in (start_obj, start_arr) if idx != -1]
    first_bracket_idx = min(valid_indices)
    
    # Potong teks mulai dari bracket pertama hingga akhir
    json_str = raw_text[first_bracket_idx:]
    
    # 2. Coba parsing langsung (Happy path)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as original_error:
        # 3. Masuk ke fase Auto-Repair jika gagal (kemungkinan terpotong)
        return _repair_and_parse_json(json_str, original_error)

def _repair_and_parse_json(json_str: str, original_error: Exception) -> dict:
    """
    Memperbaiki JSON yang terpotong dengan menutup string dan kurung yang terbuka,
    serta membersihkan trailing comma.
    """
    stack = []
    in_string = False
    escape_char = False
    
    # Parsing karakter per karakter untuk melacak struktur yang terbuka
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
                    # Pop stack jika kurung tutup sesuai dengan kurung buka terakhir
                    if (char == '}' and last == '{') or (char == ']' and last == '['):
                        stack.pop()

    # Repair 1: Tutup string literal yang terpotong di tengah jalan
    if in_string:
        json_str += '"'
        
    # Repair 2: Bersihkan trailing comma sebelum kita menambahkan kurung tutup paksa
    # (JSON standar tidak mengizinkan koma di akhir elemen terakhir)
    json_str = re.sub(r',\s*$', '', json_str)

    # Repair 3: Tutup semua bracket yang masih ada di dalam stack (LIFO / mundur)
    while stack:
        last = stack.pop()
        if last == '{':
            # Opsional: Jika terpotong pas di key (misal: {"key": ), kita set value default
            # Agar lebih aman, pastikan tidak ada trailing comma lagi
            json_str = re.sub(r',\s*$', '', json_str)
            # Jika berakhir dengan titik dua, tambahkan null agar valid
            if json_str.strip().endswith(':'):
                json_str += ' null'
            json_str += '}'
        elif last == '[':
            json_str = re.sub(r',\s*$', '', json_str)
            json_str += ']'

    # Coba parse ulang hasil perbaikan
    try:
        repaired_json = json.loads(json_str)
        # Opsional: Tambahkan flag internal agar sistem/UI tahu ini hasil repair
        if isinstance(repaired_json, dict):
            repaired_json['_is_repaired_partial_result'] = True
        return repaired_json
    except json.JSONDecodeError as repair_error:
        # Jika tetap gagal, berikan pesan error yang lebih akurat
        error_msg = (
            f"Gagal mem-parsing JSON. Teks terpotong terlalu parah untuk diselamatkan. "
            f"Error asli: {original_error}. Error setelah repair: {repair_error}."
        )
        raise ValueError(error_msg)
