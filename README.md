# 🎬 AI YouTube Content Intelligence Pro

Aplikasi web (Streamlit) untuk **reverse-engineer** strategi konten video YouTube dan menghasilkan **paket produksi YouTube baru yang orisinal** — judul, thumbnail, deskripsi, SEO, segmen terbaik, rekomendasi editing, prediksi performa, hingga checklist siap upload — disesuaikan dengan DNA channel pilihan Anda.

> ⚠️ Aplikasi ini **tidak menyalin** video sumber. Setiap insight ditransformasikan menjadi angle baru sesuai prinsip orisinalitas pada `prompts/system_prompt.md`.

---

## ✨ Fitur Utama

- 🔗 Analisis dari URL YouTube (transkrip diambil otomatis) atau upload transkrip manual.
- 🧠 Pipeline AI 5 modul: Video Intelligence → Audience Psychology → YouTube Growth → Content Strategist → Channel DNA.
- 🎭 3 karakter channel siap pakai: **Suara Filsuf**, **Nalar Senyap**, **Tutur Kyai** (mudah ditambah sendiri).
- 📦 Output Type: Shorts atau Video Panjang, dengan banyak pilihan durasi (termasuk Custom).
- 🎯 Segment Mode: AI Otomatis atau Manual (Start/End Time).
- 📊 Tampilan hasil modern: tabs, accordion, progress bar, badge, copy button, dan JSON mentah.
- 🧠✨ **Skill Claude tambahan (opsional, khusus provider Anthropic langsung):**
  - **🔍 Web Search** — Claude mencari tren judul, kata kunci SEO, dan pola kompetitor terkini di internet sebelum menyusun strategi, alih-alih hanya menebak dari data pelatihan.
  - **🧩 Extended Thinking** — Claude bernalar lebih panjang & terstruktur sebelum menjawab, berguna untuk pipeline 5-modul yang kompleks. Toggle keduanya ada di sidebar → expander "🧠 Skill Claude Tambahan".

---

## 📁 Struktur Project

```text
AI-YouTube-Content-Intelligence/
│
├── app.py                     # Entry point Streamlit
├── requirements.txt
├── .env.example
│
├── prompts/
│   ├── system_prompt.md
│   ├── video_intelligence.md
│   ├── audience_psychology.md
│   ├── youtube_growth.md
│   ├── content_strategist.md
│   ├── thumbnail_prompt.md
│   ├── seo_prompt.md
│   ├── output_format.md
│   └── channels/
│       ├── suara_filsuf.md
│       ├── nalar_senyap.md
│       └── tutur_kyai.md
│
├── settings/
│   ├── channel_setting.json
│   ├── duration_setting.json
│   ├── output_setting.json
│   └── ui_setting.json
│
├── utils/
│   ├── prompt_loader.py       # Gabungkan modul prompt sesuai channel terpilih
│   ├── youtube_utils.py       # Ekstrak video ID, metadata, transkrip
│   ├── ai_client.py           # Wrapper Anthropic API
│   ├── parser.py              # Parsing JSON dari respons AI (dengan fallback)
│   └── ui_components.py       # Badge, copy button, progress bar, dll.
│
└── assets/
```

---

## 🚀 Cara Menjalankan

### 1. Buat virtual environment (opsional tapi disarankan)

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Pilih & siapkan API Key Provider AI

Aplikasi ini mendukung beberapa provider AI, dipilih lewat dropdown **"AI Provider"** di sidebar:

| Provider | Keterangan | Env Var |
|---|---|---|
| 🟣 Anthropic (Claude langsung) | Default, lewat Anthropic API | `ANTHROPIC_API_KEY` |
| 🟢 9Router Proxy | Proxy self-hosted ([github.com/decolua/9router](https://github.com/decolua/9router)) yang merutekan ke 40+ provider (Claude/GPT/Gemini/GLM/DeepSeek/dll) lewat satu endpoint OpenAI-compatible lokal | `NINEROUTER_API_KEY` + `NINEROUTER_BASE_URL` (default `http://localhost:20128/v1`) |
| 🔵 OpenAI (GPT langsung) | Lewat OpenAI API | `OPENAI_API_KEY` |
| 🟡 Google Gemini (langsung) | Lewat endpoint OpenAI-compatible Google | `GEMINI_API_KEY` |
| ⚪ Custom OpenAI-Compatible | Untuk provider/proxy lain apa pun yang mengikuti format OpenAI (OpenRouter, Groq, DeepSeek, LiteLLM, dst) | `CUSTOM_AI_API_KEY` + `CUSTOM_AI_BASE_URL` |

Daftar model & deskripsi tiap provider bisa diatur/ditambah lewat `settings/ai_provider_setting.json`.

Anda bisa memilih salah satu cara mengisi API key:

**Opsi A — file `.env`:**

```bash
cp .env.example .env
# lalu edit .env dan isi API key + base URL untuk provider yang Anda pilih
```

**Opsi B — langsung di sidebar aplikasi** (paling mudah, tidak perlu file apa pun). Field "API Key" dan "Base URL Endpoint" di sidebar akan menimpa nilai dari `.env`.

Khusus **9Router**: jalankan 9Router terlebih dahulu di komputer/server Anda (`npm run dev` atau `docker run -p 20128:20128 ...`), lalu ambil API key dari dashboard-nya (Dashboard → Endpoint → API Key), dan pastikan Base URL di sidebar sesuai (default `http://localhost:20128/v1`).

Dapatkan API key Anthropic di [console.anthropic.com](https://console.anthropic.com/).

### 4. Jalankan aplikasi

```bash
streamlit run app.py
```

Aplikasi akan terbuka otomatis di browser, biasanya di `http://localhost:8501`.

---

## 🧩 Cara Kerja Pipeline AI

Saat tombol **"Jalankan Analisis"** ditekan, `utils/prompt_loader.py` menggabungkan modul prompt secara berurutan menjadi satu `system_prompt`:

```
system_prompt.md
  → video_intelligence.md
  → audience_psychology.md
  → youtube_growth.md
  → content_strategist.md
  → channels/<channel_terpilih>.md   ← hanya channel yang dipilih, channel lain TIDAK dimuat
  → thumbnail_prompt.md
  → seo_prompt.md
  → output_format.md
```

`system_prompt` ini lalu dikirim ke Anthropic API bersama transkrip video + setting pengguna sebagai pesan `user`. AI diinstruksikan untuk membalas **hanya** dalam format JSON (lihat skema lengkap di `prompts/output_format.md`), yang kemudian di-parse oleh `utils/parser.py` dan dirender oleh `app.py` ke dalam tabs (Ringkasan, Strategi, Segmen, Judul, Thumbnail, Deskripsi, SEO, Editing, Prediksi Performa, Checklist).

---

## ➕ Menambah Channel Baru

1. Buat file baru di `prompts/channels/nama_channel_anda.md` berisi DNA channel (karakter, gaya bahasa, larangan, dll — ikuti format 3 contoh yang sudah ada).
2. Tambahkan entri baru di `settings/channel_setting.json`:

```json
{
  "id": "nama_channel_anda",
  "name": "Nama Channel Anda",
  "file": "channels/nama_channel_anda.md",
  "emoji": "🔥",
  "description": "Deskripsi singkat channel Anda."
}
```

3. Channel baru otomatis muncul di dropdown sidebar — tidak perlu mengubah kode apa pun.

---

## 🛠️ Troubleshooting

| Masalah | Solusi |
|---|---|
| `API key belum diatur untuk provider ini` | Isi API key di sidebar, atau di file `.env` sesuai provider yang dipilih. |
| `Base URL belum diisi` / `Gagal terhubung ke endpoint` | Khusus 9Router/Custom: pastikan proxy sudah berjalan dan Base URL di sidebar benar (mis. `http://localhost:20128/v1`). |
| `YouTube is blocking requests from your IP` | Umum terjadi saat app dijalankan di VPS/cloud (AWS/GCP/Azure dsb — IP-nya sering diblokir YouTube). Buka expander **"🌐 Proxy YouTube"** di sidebar dan aktifkan mode **Webshare** (rotating residential proxy, paling andal) atau **Generic** (proxy HTTP/HTTPS milik Anda). Bisa juga diisi lewat `.env` (`YOUTUBE_WEBSHARE_USERNAME`/`YOUTUBE_WEBSHARE_PASSWORD` atau `YOUTUBE_HTTP_PROXY`/`YOUTUBE_HTTPS_PROXY`). Sebagai jalan pintas sementara, unggah transkrip manual lewat field "📄 Upload Transkrip". |
| Transkrip gagal diambil otomatis | YouTube terkadang membatasi/menonaktifkan transkrip untuk video tertentu. Gunakan fitur **Upload Transkrip Manual** sebagai alternatif. |
| `URL YouTube tidak valid` | Pastikan format URL benar, contoh: `https://www.youtube.com/watch?v=XXXXXXXXXXX`, `https://youtu.be/XXXXXXXXXXX`, atau `https://www.youtube.com/shorts/XXXXXXXXXXX`. |
| Respons AI gagal di-parse sebagai JSON | Coba ulangi analisis (model kadang menyisipkan teks tambahan). Anda bisa cek respons mentah AI di expander error untuk debugging. |
| Model API error / rate limit | Coba ganti model di sidebar, atau tunggu beberapa saat sebelum mencoba lagi. |

---

## 📌 Catatan Penting

- Estimasi performa (CTR, retensi, viral potential, dll.) adalah **prediksi berbasis pola**, bukan data analytics resmi YouTube maupun garansi hasil.
- Aplikasi ini dirancang untuk **inspirasi & strategi produksi**, bukan untuk menjiplak/menyalin konten kreator lain. Selalu gunakan hasilnya sebagai bahan baku kreatif, bukan produk akhir tanpa sentuhan manusia.
