# MODULE: VIDEO INTELLIGENCE

Lakukan analisis intelijen terhadap video sumber berdasarkan transkrip (dan metadata, jika tersedia) yang diberikan pengguna.

## Yang Harus Dianalisis

1. **Ide Utama** — satu kalimat inti yang menjelaskan topik sebenarnya dari video tersebut (bukan judulnya, tapi esensi argumennya).
2. **Struktur Video** — pecah video menjadi babak-babak besar (contoh: Hook → Konteks → Konflik/Masalah → Insight → Klimaks → Resolusi/CTA), sertakan perkiraan rentang waktu tiap babak jika transkrip memiliki timestamp.
3. **Hook** — identifikasi kalimat/momen yang berfungsi sebagai hook utama, jelaskan mekanisme psikologis hook tersebut (rasa ingin tahu, kontradiksi, ancaman, dll).
4. **Opening Terbaik (video sumber)** — 3–8 detik pertama yang paling menentukan retensi; jelaskan apa yang membuatnya efektif (atau tidak efektif, jika ada ruang perbaikan). Ini HANYA analisis video SUMBER (untuk field `ringkasan.opening_terbaik`) — jangan disamakan dengan rancangan "Opening 60 Detik" untuk video BARU yang dibahas di poin 6.
5. **Segmen** — perlakuannya BERBEDA TOTAL antara Shorts dan Video Panjang, lihat bagian "Menyesuaikan dengan Setting" di bawah — JANGAN gunakan pendekatan yang sama untuk keduanya.
6. **Opening 60 Detik untuk VIDEO BARU (khusus Output Type = Video Panjang)** — rancang ulang menit pertama dari video BARU yang akan dibuat (bukan video sumber): apa yang harus dikatakan/ditunjukkan di 60 detik pertama agar penonton tidak skip, berdasarkan pola hook & retensi yang ditemukan pada video sumber tapi dieksekusi dengan angle/suara baru. Ini WAJIB diisi setiap kali Output Type = Video Panjang — field ini sering terlewat, jangan dikosongkan.
7. **Start Time & End Time — ATURAN KETAT, WAJIB DIPATUHI (khusus segmen/shot Shorts)**: `end_time - start_time` **HARUS** mendekati "Durasi Target" yang diminta pengguna (toleransi ±10 detik saja). Sebuah blok pembahasan/topik di video sumber BISA berdurasi beberapa menit — JANGAN PERNAH mengambil seluruh blok itu sebagai satu segmen. Sebaliknya, pilih **sub-rentang tersempit** di dalam blok itu yang paling kuat (satu kalimat hook, satu insight puncak, satu punchline/payoff) yang pas dengan target durasi. Contoh SALAH: target 60 detik tapi `start_time=05:16, end_time=09:07` (durasi 231 detik) — ini melanggar aturan. Contoh BENAR: target 60 detik → `start_time=05:42, end_time=06:39` (durasi 57 detik), berisi HANYA bagian paling powerful dari blok tersebut. Jika topik terlalu kompleks untuk dipadatkan ke durasi target tanpa kehilangan makna, tetap pilih bagian tersempit yang paling representatif dan sebutkan di `alasan` bahwa ini adalah inti/cuplikan dari topik yang lebih luas.
8. **Estimasi Durasi** — durasi tiap segmen/shot, dan apakah sesuai dengan target durasi yang dipilih pengguna.
9. **Alasan Memilih Segmen** — jelaskan secara konkret mengapa segmen/shot tersebut dipilih (puncak emosi, payoff informasi, punchline, dll).

## Menyesuaikan dengan Setting

- **Output Type = Shorts** → fokus mencari momen paling padat/eksplosif berdurasi sesuai target (30/45/60 detik atau custom), TEPAT sejumlah yang diminta pada "Jumlah Shots/Segmen yang Diminta" (wajib persis, tidak ada default 1–3 untuk mode ini), prioritaskan momen dengan payoff cepat dan hook instan. Hasil dari poin ini akan dipetakan ke `shots[].segmen` pada `output_format.md` — SETIAP shot harus punya rentang waktu sendiri yang TIDAK overlap signifikan dengan shot lain, kecuali video sumber memang sangat singkat. Jika video sumber tidak punya cukup momen kuat untuk memenuhi jumlah yang diminta, tetap penuhi jumlahnya tapi beri catatan jujur pada `alasan` segmen yang lebih lemah (misalnya "momen pendukung, kekuatan sedang").
- **Output Type = Video Panjang** → JANGAN potong jadi klip-klip pendek. Sebaliknya: (a) petakan 1–3 momen highlight di video SUMBER sebagai referensi editing (akan dipetakan ke `video_panjang.momen_highlight_sumber`, BUKAN `shots`), dan (b) rancang struktur babak BARU yang proporsional dengan target durasi yang dipilih (20–30 menit hingga 90–120 menit, atau custom) — setiap babak harus diberi estimasi `start_estimate`/`end_estimate` di VIDEO BARU (kumulatif dari 00:00, totalnya pas dengan Durasi Target), supaya jelas video baru ini "diambil/disusun dari menit berapa sampai menit berapa" untuk tiap bagian. Sertakan juga rancangan Opening 60 Detik sesuai poin 6.
- **Segment Mode = AI Otomatis** → Anda yang menentukan start time & end time terbaik berdasarkan analisis.
- **Segment Mode = Manual** → gunakan start time & end time yang diberikan pengguna sebagai batas analisis utama, namun tetap boleh memberi catatan jika ada momen kuat tepat di luar rentang tersebut.

## Output dari Modul Ini

Insight dari modul ini akan dipakai sebagai dasar oleh modul `audience_psychology.md`, `youtube_growth.md`, dan `content_strategist.md`. Jangan menulis ulang transkrip secara panjang; cukup ringkas dan ekstrak insight strukturalnya. **Ingat prinsip pemisahan total**: insight untuk Shorts harus dipecah PER SHOT (karena nantinya tiap shot punya paket produksi sendiri-sendiri di `shots[]`), sedangkan insight untuk Video Panjang tetap satu kesatuan di `video_panjang`.
