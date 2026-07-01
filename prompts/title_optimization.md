# MODULE: TITLE OPTIMIZATION (BERDASARKAN DATA ANALYTICS CHANNEL-SPECIFIC)

## Prinsip Utama

**⚠️ WAJIB: Setiap judul HARUS unik dan disesuaikan dengan pola viral yang SUDAH TERBUKTI dari data analytics CHANNEL ITU SENDIRI. DILARANG menyamakan strategi judul antar channel.**

Contoh:
- **Suara Filsuf** → Judul top performer: pertanyaan retoris + paradoks (6.2% CTR) → Opsi judul WAJIB mengikuti pola ini
- **Nalar Senyap** → Judul top performer: pernyataan kontras + data (7.1% CTR) → Opsi judul WAJIB BERBEDA dari Suara Filsuf
- **Tutur Kyai** → Judul top performer: pertanyaan praktis + solusi (5.8% CTR) → Opsi judul WAJIB BERBEDA dari kedua channel lain

---

## Input Wajib dari AI

**Sebelum mengoptimasi judul, HARUS ada:**

1. **Channel ID** yang dipilih pengguna (misal: "suara_filsuf", "nalar_senyap", "tutur_kyai")
2. **Data Analytics untuk Channel ITU SPESIFIK** (dari `ChannelAnalyticsSummary`):
   - `channel_id` (harus match dengan channel yang dipilih)
   - `top_videos_by_views` — lihat judul + metriks (views, CTR, retensi)
   - `top_videos_by_ctr` — judul mana yang paling viral
   - `top_videos_by_retention` — judul mana yang paling retensi
   - `avg_ctr_pct` — baseline CTR channel ini
   - `avg_retention_pct` — baseline retensi channel ini
   - `notes` — pola yang sudah terdeteksi otomatis

3. **DNA Channel yang Dipilih** (dari `prompts/channels/<channel_id>.md`):
   - Gaya bahasa, tone, target audience
   - Larangan spesifik channel
   - Kata yang sering digunakan

---

## Proses Optimasi: Channel-Specific Pattern Analysis

### Step 1: EKSTRAK POLA JUDUL UNIK PER CHANNEL

**Ini adalah KUNCI — setiap channel punya pola judul yang berbeda.**

#### Contoh Analisis Suara Filsuf:

```
TOP VIDEOS BY VIEWS (Channel: Suara Filsuf):
1. "Mengapa Takut Akan Kematian Padahal Tahu Itu Pasti?" 
   → Views: 480K | CTR: 6.2% | Retensi: 52%
   → Pattern: Pertanyaan retoris + paradoks

2. "Kesuksesan Palsu: Apa Yang Orang-Orang Salah Pahami"
   → Views: 320K | CTR: 5.8% | Retensi: 48%
   → Pattern: Pernyataan + penjelasan

3. "Stoikisme di Era Modern: Filosofi Praktis Untuk Hidup Tenang"
   → Views: 290K | CTR: 5.1% | Retensi: 45%
   → Pattern: Topik : benefit/aplikasi

TOP VIDEOS BY CTR (Channel: Suara Filsuf):
1. "Mengapa Semakin Kita Mencari Bahagia, Semakin Ia Menjauh?"
   → CTR: 7.9% | Views: 290K | Retensi: 51%
   → Pattern: Pertanyaan retoris + paradoks PALING EFEKTIF

2. "Diam Itu Bukti Kekuatan, Bukan Kelemahan"
   → CTR: 7.2% | Views: 210K | Retensi: 49%
   → Pattern: Pernyataan kontras

POLA UNIK SUARA FILSUF:
✅ CTR Tertinggi: Pertanyaan retoris + paradoks eksistensial
✅ Durasi Ideal: 8–12 kata (tidak terlalu panjang, tidak terlalu pendek)
✅ Struktur: "Mengapa... padahal..." atau "Semakin... semakin..."
✅ Vocabulary: Menggunakan kata-kata filosofis tapi relatable (takut, bahagia, diam, kekuatan)
❌ Hindari: Angka/list, call-to-action langsung, kata "HARUS", "WAJIB"
```

#### Contoh Analisis Nalar Senyap (BERBEDA):

```
TOP VIDEOS BY CTR (Channel: Nalar Senyap - ASUMSI):
1. "5 Kesalahan Berpikir Logis Anda Masih Lakukan (Data Membuktikan)"
   → CTR: 7.1% | Views: 520K | Retensi: 46%
   → Pattern: Angka + investigasi + data/bukti

2. "Anda Tertipu Logika Fake ini Setiap Hari (Tapi Tidak Sadar)"
   → CTR: 6.9% | Views: 450K | Retensi: 44%
   → Pattern: Kejutan + investigasi tersembunyi

POLA UNIK NALAR SENYAP:
✅ CTR Tertinggi: Angka + revelasi/investigasi + bukti konkret
✅ Durasi Ideal: 12–15 kata (lebih panjang, karena ada daftar + bukti)
✅ Struktur: "[Angka] Hal yang... (Data/Bukti)" atau "Anda... Tapi..."
✅ Vocabulary: Data, bukti, investigasi, logical fallacy, kesalahan, tidak tahu
❌ Hindari: Pertanyaan retoris abstrak, filosofis murni (itu Suara Filsuf!)
```

**→ KESIMPULAN: Nalar Senyap ≠ Suara Filsuf. Jangan campur polanya!**

---

### Step 2: BUAT 3 OPSI JUDUL YANG MENGIKUTI POLA CHANNEL ITU

**Untuk setiap channel, HARUS dihasilkan 3 judul yang:**
1. Mengikuti pola judul top performer CHANNEL ITU SENDIRI (bukan template generic)
2. Menggunakan vocabulary + struktur yang sudah terbukti viral DI CHANNEL ITU
3. Tetap mematuhi DNA + larangan CHANNEL ITU
4. Disesuaikan dengan Big Idea, Angle, Hook yang baru (dari content_strategist.md)

#### Contoh: Membuat 3 Judul untuk Suara Filsuf

**Input dari content_strategist:**
- Big Idea: Kebebasan sejati bukan absensi batasan, tapi pilihan sadar atas batasan
- Angle: Perspektif Camus tentang absurditas hidup + kebebasan eksistensial
- Hook: Pertanyaan pembuka tentang kebebasan palsu vs kebebasan nyata

**3 Opsi Judul (mengikuti pola Suara Filsuf):**

1. **Judul Opsi 1 (Pola: Pertanyaan retoris + paradoks)**
   ```
   "Mengapa Semakin Kita Ingin Bebas, Semakin Kita Terikat?"
   → Mengikuti struktur top CTR video (#1: "Mengapa... Padahal..."; #7: "Semakin... Semakin...")
   → Panjang: 9 kata ✓ (sesuai 8-12 kata ideal Suara Filsuf)
   → Vocabulary: bebas, terikat (familiar untuk audience Suara Filsuf)
   ```

2. **Judul Opsi 2 (Pola: Pernyataan kontras)**
   ```
   "Kebebasan Palsu vs Kebebasan Sejati: Apa Bedanya?"
   → Mengikuti struktur top CTR video #2: "Diam Itu Bukti Kekuatan, Bukan Kelemahan"
   → Panjang: 9 kata ✓
   → Vocabulary: palsu, sejati, bedanya (familiar)
   ```

3. **Judul Opsi 3 (Pola: Pertanyaan + insight)**
   ```
   "Haruskah Kita Takut Akan Kebebasan?"
   → Mengikuti pola hybrid: pertanyaan + emotion (takut)
   → Panjang: 6 kata ✓
   → Vocabulary: takut, kebebasan (emotional anchor)
   ```

**Jangan buat ini untuk Suara Filsuf (violation pola):**
```
❌ "5 Jenis Kebebasan yang Harus Kamu Ketahui" 
   → Ini pola Nalar Senyap (angka + list), bukan Suara Filsuf (pertanyaan/paradoks)

❌ "Cara Memilih Kebebasan Dalam 3 Langkah Mudah"
   → Ini pola motivasi/tutorial, bukan filosofis + reflektif (violation DNA Suara Filsuf)
```

---

#### Contoh: Membuat 3 Judul untuk Nalar Senyap (BERBEDA)

**Input dari content_strategist:**
- Big Idea: Kebebasan sejati bukan absensi batasan, tapi pilihan sadar atas batasan
- Angle: Analisis logis + cognitive bias dalam memahami kebebasan

**3 Opsi Judul (mengikuti pola Nalar Senyap):**

1. **Judul Opsi 1 (Pola: Angka + investigasi + data)**
   ```
   "3 Ilusi Logika Tentang Kebebasan yang Membuat Anda Tersesat"
   → Mengikuti struktur top CTR Nalar Senyap: "[Angka] Hal yang... (investigasi)"
   → Panjang: 11 kata ✓
   → Vocabulary: ilusi, logika, tersesat (analytical)
   ```

2. **Judul Opsi 2 (Pola: Kejutan + investigasi)**
   ```
   "Kebebasan yang Anda Rasakan Mungkin Adalah Jebakan Pikiran"
   → Mengikuti pola: "Anda... Tapi..."
   → Panjang: 11 kata ✓
   → Vocabulary: jebakan, pikiran (revelation tone)
   ```

3. **Judul Opsi 3 (Pola: Angka + benefit + bukti)**
   ```
   "2 Batasan Palsu Tentang Kebebasan (Dan Mengapa Neuroscience Setuju)"
   → Mengikuti pola: "[Angka] + benefit + bukti ilmiah"
   → Panjang: 12 kata ✓
   → Vocabulary: batasan, neuroscience, bukti (credible + analytical)
   ```

**Jangan buat ini untuk Nalar Senyap (violation pola):**
```
❌ "Mengapa Semakin Kita Mencari Kebebasan, Semakin Ia Menjauh?"
   → Ini pola Suara Filsuf (paradoks filosofis), bukan Nalar Senyap (investigasi logis)

❌ "Kebebasan dalam Konteks Modern: Refleksi Mendalam"
   → Ini terlalu filosofis, bukan analytical/investigatif (violation DNA Nalar Senyap)
```

---

### Step 3: EVALUASI KETIGA JUDUL TERHADAP BASELINE ANALYTICS CHANNEL

**Untuk SETIAP dari 3 judul, prediksi berdasarkan data channel yang SPESIFIK:**

| Metrik | Judul Opsi 1 | Judul Opsi 2 | Judul Opsi 3 |
|--------|--------------|--------------|--------------|
| **Pattern Match** | ⭐⭐⭐ Pola pertanyaan + paradoks (top CTR: 7.9%) | ⭐⭐ Pola pernyataan kontras (top CTR: 7.2%) | ⭐⭐ Hybrid pola |
| **Potensi CTR** | 6.8–7.5% (di atas baseline 5.2%) | 6.2–7.0% | 5.8–6.5% |
| **Potensi Retensi** | 49–53% (sejalan top retention) | 47–51% | 46–50% |
| **Durasi Ideal Match** | ✓ 9 kata | ✓ 9 kata | ✓ 6 kata |
| **Vocabulary Relevance** | ✓ Familiar untuk audience | ✓ Familiar | ✓ Familiar |

---

### Step 4: PILIH BEST CHOICE + REFERENSI DATA

**Pilih 1 judul TERBAIK dengan alasan konkret berbasis DATA ANALYTICS CHANNEL:**

#### Contoh Alasan untuk Suara Filsuf:

```
BEST CHOICE: "Mengapa Semakin Kita Ingin Bebas, Semakin Kita Terikat?"

Alasan (berbasis data analytics Suara Filsuf):

[1] POLA MATCH TERTINGGI
    - Struktur "Mengapa... Semakin... Semakin..." PERSIS seperti top CTR video 
      "#7: 'Mengapa Semakin Kita Mencari Bahagia, Semakin Ia Menjauh?' (7.9% CTR, 290K views)"
    - Ini adalah pola TOP PERFORMER Suara Filsuf untuk mendorong klik

[2] POTENSI CTR OPTIMAL
    - Baseline CTR channel: 5.2%
    - Judul ini memiliki 94% kesamaan struktur dengan top CTR video
    - Prediksi CTR: 6.8–7.5% (naik 30–44% dari baseline)
    - Referensi: Top CTR video dengan pola sama → 7.9% CTR

[3] POTENSI RETENSI SESUAI AUDIENS
    - Baseline Retensi: 48%
    - Top video dengan pola ini → 51% retensi
    - Topik kebebasan vs takatan → relatable bagi target audience Suara Filsuf (usia 20-40, 
      suka refleksi diri)

[4] VIRAL POTENTIAL: EVERGREEN + HIGH POTENTIAL
    - Topik kebebasan vs keterikataan = timeless, tidak bound ke trend
    - Pola pertanyaan eksistensial = share-worthy (audience suka diskusi filosofis)
    - Predicted viral score: 8/10

[5] KONSISTENSI DNA CHANNEL
    - Tetap reflektif, bukan menggurui ✓
    - Menggunakan kata-kata channel (bebas, terikat, ingin) ✓
    - Panjang 9 kata = optimal untuk tidak terpotong di thumbnail ✓

KESIMPULAN: 
Judul ini OPTIMAL untuk channel Suara Filsuf karena mengikuti pola yang SUDAH TERBUKTI viral 
(7.9% CTR top performer), sambil tetap menjaga konsistensi DNA channel dan relevansi baru dengan 
angle Camus tentang kebebasan eksistensial.
```

#### Contoh Alasan untuk Nalar Senyap (BERBEDA):

```
BEST CHOICE: "3 Ilusi Logika Tentang Kebebasan yang Membuat Anda Tersesat"

Alasan (berbasis data analytics NALAR SENYAP - BERBEDA dari Suara Filsuf):

[1] POLA MATCH TERTINGGI (CHANNEL-SPECIFIC)
    - Struktur "[Angka] + Hal yang... (investigasi)" PERSIS seperti top CTR video 
      "#1 Nalar Senyap: '5 Kesalahan Berpikir Logis Anda Masih Lakukan (Data Membuktikan)' (7.1% CTR, 520K views)"
    - BEDA TOTAL dari Suara Filsuf yang menggunakan pertanyaan retoris

[2] POTENSI CTR OPTIMAL (BASELINE NALAR SENYAP BERBEDA)
    - Baseline CTR channel Nalar Senyap: 6.0% (LEBIH TINGGI dari Suara Filsuf karena audience 
      lebih responsif ke angka/data)
    - Judul ini mengikuti pola top CTR
    - Prediksi CTR: 6.8–7.3% (sesuai range top performer Nalar Senyap)

[3] INVESTIGATIVE + DATA-DRIVEN TONE
    - Channel Nalar Senyap fokus pada logical analysis, bukan philosophy
    - Judul ini menjanjikan "ilusi logika" (investigasi) + "tersesat" (consequence)
    - Audience Nalar Senyap akan lebih tertarik dengan ini daripada "Mengapa... Semakin..." 
      (yang pola Suara Filsuf)

[4] EVERGREEN + HIGH SHAREABILITY FOR NALAR SENYAP AUDIENCE
    - Audience Nalar Senyap (usia 20-40, suka critical thinking) akan share di grup diskusi 
      filosofi/science
    - Predicted viral score: 8.2/10 (audience Nalar Senyap lebih aktif share analytical content)

KESIMPULAN:
Judul ini OPTIMAL untuk channel NALAR SENYAP karena mengikuti pola UNIK channel ini 
(angka + investigasi), yang BERBEDA dari Suara Filsuf (pertanyaan retoris). Setiap channel 
punya audience + pola viral yang BERBEDA, jadi strategi judul HARUS channel-specific.
```

---

## Output ke JSON

```json
{
  "judul": {
    "opsi": [
      "Judul Opsi 1 (mengikuti pola top CTR channel ini)",
      "Judul Opsi 2 (mengikuti pola alternatif channel ini)",
      "Judul Opsi 3 (mengikuti pola retention channel ini)"
    ],
    "best_choice": "Judul Opsi 1",
    "alasan_best_choice": "[1] Pola: mengikuti top CTR video channel (struktur UNIK channel ini, BUKAN generic). [2] Potensi CTR: X–Y% vs baseline Z% (data: top performer dengan pola sama → W% CTR). [3] Retensi: predicted M–N% (sejalan top retention video). [4] Evergreen + viral score K/10. [5] Konsistensi DNA channel + target audience SPESIFIK channel. [6] Referensi konkret: '[Top Performer Video Title]' (VVV views, CCC% CTR, RRR% retensi) ← JUDUL OPSI 1 mengikuti pola ini."
  }
}
```

---

## ⚠️ INSTRUKSI WAJIB

1. **SETIAP channel punya pola UNIK** — jangan pernah copy-paste strategi dari channel lain
2. **Data analytics WAJIB digunakan** — jika tidak ada, nyatakan: "Data analytics tidak tersedia; menggunakan heuristik DNA channel + best practice"
3. **Selalu referensi data konkret** — "Top video: [judul] ([views] views, [CTR]% CTR, [retensi]% retensi)" ← jangan vague
4. **Per-channel analysis** — bandingkan judul baru dengan top performers CHANNEL ITU, bukan generic benchmark
5. **Hindari menyamakan antar channel** — Suara Filsuf ≠ Nalar Senyap ≠ Tutur Kyai dalam hal pola judul

