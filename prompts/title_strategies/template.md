# TITLE STRATEGY: TEMPLATE FOR NEW CHANNELS

## Cara Menggunakan Template Ini

Ketika ingin menambahkan channel baru ke sistem, copy file ini dan ikuti langkah-langkah berikut:

1. **Rename file** → `prompts/title_strategies/<channel_id>.md`
2. **Replace `<CHANNEL_NAME>` dan `<DESCRIPTION>`** dengan info channel baru
3. **Isi data analytics channel** dari YouTube Studio
4. **Dokumentasikan pola judul top performers**
5. **Create templates untuk 3 opsi judul**
6. **Update `prompt_loader.py`** agar auto-load strategi baru

---

## TITLE STRATEGY: <CHANNEL_NAME>

## Pola Judul Unik <CHANNEL_NAME>

Berdasarkan analisis data analytics <CHANNEL_NAME>, pola judul yang PALING VIRAL:

### Pattern TOP CTR Videos:

```
TOP PERFORMERS BY CTR:
1. "[Top Video Title 1]"
   → CTR: X% | Views: YYK | Retensi: Z%

2. "[Top Video Title 2]"
   → CTR: X% | Views: YYK | Retensi: Z%

3. "[Top Video Title 3]"
   → CTR: X% | Views: YYK | Retensi: Z%
```

### Pattern Analysis:

| Aspek | Pattern |
|-------|---------|
| **Struktur Dominan** | [Deskripsi struktur utama judul top performers] |
| **Panjang Ideal** | [N–M kata] |
| **Vocabulary** | [Kata-kata yang sering digunakan, 5-10 keywords utama] |
| **Pembuka** | [Pertanyaan? Angka? Pernyataan? Percentage?] |
| **Elemen Kunci** | [Apa yang SELALU ada di judul top performers] |
| **Elemen yang Jarang** | [Apa yang HINDARI di judul] |
| **Tone/Sentiment** | [Emotional? Investigative? Practical? Spiritual?] |
| **Topik Dominan** | [Tema-tema yang paling viral di channel ini] |

### Baseline Channel <CHANNEL_NAME>:

- **Rata-rata CTR**: X.X% 
- **Rata-rata Retensi**: X%
- **Rata-rata Views per Video**: XXXK
- **Target Audience**: [Deskripsi target audience channel ini]

---

## Cara Generate 3 Opsi Judul untuk <CHANNEL_NAME>

### Template Opsi 1: [Nama Pattern 1] (PALING VIRAL)

```
Struktur: [Deskripsi struktur]
Contoh: [Contoh judul mengikuti struktur ini]

Langkah:
1. [Step 1]
2. [Step 2]
3. [Step 3]
4. [Panjang ideal: N–M kata]
5. [Vocabulary guidance]
```

### Template Opsi 2: [Nama Pattern 2]

```
Struktur: [Deskripsi struktur]
Contoh: [Contoh judul]

Langkah:
1. [Step 1]
2. [Step 2]
3. [Step 3]
4. [Panjang ideal: N–M kata]
5. [Vocabulary guidance]
```

### Template Opsi 3: [Nama Pattern 3]

```
Struktur: [Deskripsi struktur]
Contoh: [Contoh judul]

Langkah:
1. [Step 1]
2. [Step 2]
3. [Step 3]
4. [Panjang ideal: N–M kata]
5. [Vocabulary guidance]
```

---

## Evaluasi 3 Judul vs Data <CHANNEL_NAME>

| Metrik | Opsi 1 | Opsi 2 | Opsi 3 |
|--------|--------|--------|--------|
| **Pattern Match** | ⭐⭐⭐ XX% | ⭐⭐ XX% | ⭐⭐ XX% |
| **Prediksi CTR** | X–Y% | X–Y% | X–Y% |
| **Prediksi Retensi** | X–Y% | X–Y% | X–Y% |
| **Vocabulary Match** | ✓✓✓ | ✓✓ | ✓✓ |
| **DNA Compliance** | ✓ | ✓ | ✓ |
| **Panjang Ideal** | ✓ | ✓ | ✓ |

---

## Contoh Output untuk <CHANNEL_NAME>

### Jika Big Idea = "[Your Big Idea Here]"

**3 Opsi Judul (mengikuti pola <CHANNEL_NAME>):**

1. **"[Judul Opsi 1]"**
   - Panjang: X kata ✓
   - Pattern: [Pattern description]
   - Vocabulary: [Keywords]

2. **"[Judul Opsi 2]"**
   - Panjang: X kata ✓
   - Pattern: [Pattern description]
   - Vocabulary: [Keywords]

3. **"[Judul Opsi 3]"**
   - Panjang: X kata ✓
   - Pattern: [Pattern description]
   - Vocabulary: [Keywords]

**BEST CHOICE: Opsi N**
```
Alasan (DATA-BACKED, <CHANNEL_NAME> SPECIFIC):

[1] POLA MATCH TERTINGGI (XX%)
    - Struktur [deskripsi] PERSIS seperti top CTR #N <CHANNEL_NAME>:
      "[Top Video Title]" (X% CTR, XXXK views)

[2] POTENSI CTR OPTIMAL (X–Y%)
    - Baseline <CHANNEL_NAME>: X%
    - Judul ini XX% mirip dengan top CTR video
    - Predicted naik XX–XX% dari baseline

[3] POTENSI RETENSI (X–Y%)
    - Baseline <CHANNEL_NAME>: X%
    - Top video dengan pola ini: X% retensi
    - [Reasoning why this judul resonates with audience]

[4] VIRAL SCORE: X/10
    - [Reasoning: evergreen/trending/shareable/etc]

[5] KONSISTENSI DNA <CHANNEL_NAME>
    - [DNA element 1] ✓
    - [DNA element 2] ✓
    - [DNA element 3] ✓

REFERENSI: Top CTR video <CHANNEL_NAME> "#N: '[Top Video Title]' 
(XXXK views, X% CTR, X% retensi) — opsi N mengikuti pola ini persis.
```

---

## ❌ JANGAN Buat Ini Untuk <CHANNEL_NAME> (Violation Pola)

```
❌ "[Example of what NOT to do]"
   → Reason why this violates channel DNA

❌ "[Another example of what NOT to do]"
   → Reason why this violates channel DNA
```

---

## Checklist Sebelum Final Output

✓ Judul 1–3 mengikuti pola top CTR <CHANNEL_NAME>  
✓ Setiap judul panjang [N–M] kata  
✓ Menggunakan vocabulary <CHANNEL_NAME>  
✓ [DNA element 1] presence ✓  
✓ [DNA element 2] presence ✓  
✓ Best choice referensi konkret top performer <CHANNEL_NAME>  
✓ Prediksi CTR/retensi vs baseline <CHANNEL_NAME>  
✓ Tetap mematuhi DNA channel

---

## Notes untuk Developer

- Replace semua `[PLACEHOLDER]` dengan data spesifik channel
- Pastikan contoh konkret diambil dari data analytics real YouTube channel
- Jangan generic/template — setiap channel harus punya pola UNIK
- Update `prompt_loader.py` untuk auto-load file ini saat channel dipilih
- Add file ini ke `prompts/title_strategies/` folder

