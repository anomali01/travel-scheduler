# 🗺️ Travel Scheduler AI

Sistem penjadwalan perjalanan wisata otomatis menggunakan  
**Constraint Satisfaction Problem (CSP)** dengan Google OR-Tools.  
Dataset bersumber dari **OpenStreetMap** via Overpass API.

---

## 📁 Struktur Proyek

```
travel-scheduler/
│
├── app.py                        ← Aplikasi utama Streamlit
│
├── ai/
│   └── csp_solver.py             ← AI engine (CSP + OR-Tools)
│
├── data/
│   ├── osm_collector.py          ← Ambil data dari OpenStreetMap
│   ├── preprocessing.py          ← Cleaning & transformasi data
│   ├── raw/
│   │   └── wisata_surabaya_raw.csv   (dibuat otomatis)
│   └── processed/
│       └── wisata_surabaya_clean.csv (dibuat otomatis)
│
├── utils/
│   └── map_utils.py              ← Visualisasi peta Folium
│
├── requirements.txt
└── README.md
```

---

## 🚀 Cara Menjalankan

### 1. Clone / Download proyek
```bash
# Jika pakai git
git clone <url-repo>
cd travel-scheduler

# Atau ekstrak ZIP lalu masuk ke folder
cd travel-scheduler
```

### 2. Buat virtual environment (disarankan)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Jalankan aplikasi
```bash
streamlit run app.py
```

Aplikasi akan terbuka di browser: **http://localhost:8501**

---

## 🧪 Testing Modul Terpisah

```bash
# Test ambil data dari OSM
python data/osm_collector.py

# Test preprocessing
python data/preprocessing.py

# Test CSP solver
python ai/csp_solver.py
```

---

## 🧠 Cara Kerja AI (CSP)

```
Input User
(budget, durasi, jam mulai, kategori)
         │
         ▼
Filter Dataset
(kategori & jam buka)
         │
         ▼
Definisi CSP
- Variabel: visit[i] ∈ {0,1}
- Domain  : setiap tempat wisata
- Constraint: budget, durasi, jam operasional
         │
         ▼
CP-SAT Solver (OR-Tools)
Objektif: Maksimalkan Σ rating
         │
         ▼
Susun Jadwal Waktu
(berdasarkan urutan & travel time)
         │
         ▼
Output: Itinerary + Peta + Metrik
```

---

## 📊 Sumber Data

- **OpenStreetMap** (openstreetmap.org)
- Diakses via **Overpass API** (overpass-api.de)
- Lisensi: ODbL — bebas digunakan untuk riset

---

## 📋 Dependencies Utama

| Library | Versi | Fungsi |
|---|---|---|
| streamlit | 1.35.0 | Web UI |
| ortools | 9.10 | CSP Solver |
| pandas | 2.2 | Data processing |
| folium | 0.16 | Peta interaktif |
| plotly | 5.20 | Grafik |
| geopy | 2.4 | Hitung jarak |
| requests | 2.31 | HTTP ke OSM API |
