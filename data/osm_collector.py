# data/osm_collector.py
"""
Modul pengambilan data tempat wisata dari OpenStreetMap
menggunakan Overpass API.

Sumber data: OpenStreetMap Contributors (openstreetmap.org)
Lisensi     : ODbL (Open Database License) — legal & gratis

Cara kerja:
  1. Kirim query Overpass QL ke server OSM
  2. Parse respons JSON menjadi DataFrame
  3. Simpan ke file CSV sebagai raw dataset
"""

import requests
import pandas as pd
import time
import os
import sys

# Force UTF-8 for standard output streams to prevent UnicodeEncodeError on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ──────────────────────────────────────────────
# KONFIGURASI
# ──────────────────────────────────────────────
OVERPASS_URL  = "http://overpass-api.de/api/interpreter"
TIMEOUT_SEC   = 30          # batas waktu request
RETRY_MAX     = 3           # maksimal retry jika gagal
RETRY_DELAY   = 5           # detik tunggu antar retry

# Mapping tag OSM → kategori sistem kita
CATEGORY_MAP = {
    "attraction"      : "Wisata Umum",
    "museum"          : "Museum",
    "theme_park"      : "Hiburan",
    "zoo"             : "Kebun Binatang",
    "aquarium"        : "Kebun Binatang",
    "artwork"         : "Wisata Umum",
    "viewpoint"       : "Wisata Alam",
    "park"            : "Taman",
    "garden"          : "Taman",
    "nature_reserve"  : "Wisata Alam",
    "beach"           : "Pantai",
    "place_of_worship": "Religi",
    "theatre"         : "Hiburan",
    "cinema"          : "Hiburan",
}

# Estimasi durasi kunjungan (menit) berdasarkan kategori
DURATION_MAP = {
    "Wisata Umum"   : 90,
    "Museum"        : 90,
    "Hiburan"       : 240,
    "Kebun Binatang": 180,
    "Taman"         : 90,
    "Pantai"        : 120,
    "Wisata Alam"   : 120,
    "Religi"        : 60,
}

# Estimasi jam operasional default per kategori
HOURS_MAP = {
    "Wisata Umum"   : (8, 17),
    "Museum"        : (9, 16),
    "Hiburan"       : (9, 21),
    "Kebun Binatang": (8, 16),
    "Taman"         : (6, 21),
    "Pantai"        : (6, 18),
    "Wisata Alam"   : (7, 17),
    "Religi"        : (6, 21),
}

# Estimasi harga tiket (Rp) per kategori
PRICE_MAP = {
    "Wisata Umum"   : 10000,
    "Museum"        : 15000,
    "Hiburan"       : 75000,
    "Kebun Binatang": 20000,
    "Taman"         : 0,
    "Pantai"        : 5000,
    "Wisata Alam"   : 5000,
    "Religi"        : 0,
}


def _build_overpass_query(kota: str) -> str:
    """
    Membangun query Overpass QL untuk mengambil
    semua node bertag tourism/leisure/amenity di kota tertentu.
    """
    return f"""
    [out:json][timeout:{TIMEOUT_SEC}];
    area[name="{kota}"]["admin_level"~"4|5|6|7|8"]->.searchArea;
    (
      node["tourism"~"attraction|museum|theme_park|zoo|aquarium|artwork|viewpoint"]
          (area.searchArea);
      node["leisure"~"park|garden|nature_reserve|beach"]
          (area.searchArea);
      node["amenity"~"place_of_worship|theatre|cinema"]
          (area.searchArea);
    );
    out body;
    """


def _fetch_with_retry(query: str) -> dict:
    """
    Kirim query ke Overpass API dengan mekanisme retry
    jika server sedang sibuk (HTTP 429 / timeout).
    """
    for attempt in range(1, RETRY_MAX + 1):
        try:
            print(f"  🌐 Request ke Overpass API (percobaan {attempt}/{RETRY_MAX})...")
            headers = {
                "User-Agent": "TravelSchedulerAI/1.0 (contact: travel-scheduler-ai@uisi.ac.id)",
                "Accept": "application/json"
            }
            resp = requests.post(
                OVERPASS_URL,
                data={"data": query},
                headers=headers,
                timeout=TIMEOUT_SEC
            )
            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.Timeout:
            print(f"  ⏱️  Timeout. Tunggu {RETRY_DELAY}s sebelum retry...")
            time.sleep(RETRY_DELAY)

        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                wait = RETRY_DELAY * attempt
                print(f"  🚦 Rate limit (429). Tunggu {wait}s...")
                time.sleep(wait)
            else:
                raise e

    raise ConnectionError(
        "❌ Gagal menghubungi Overpass API setelah "
        f"{RETRY_MAX} percobaan."
    )


def _parse_element(el: dict) -> dict | None:
    """
    Mengubah satu elemen OSM menjadi dict record dataset.
    Kembalikan None jika elemen tidak valid (tidak ada nama / koordinat).
    """
    tags = el.get("tags", {})
    name = tags.get("name", "").strip()

    # Wajib ada nama dan koordinat
    if not name or not el.get("lat") or not el.get("lon"):
        return None

    # Tentukan kategori berdasarkan tag OSM
    raw_cat = (
        tags.get("tourism")
        or tags.get("leisure")
        or tags.get("amenity")
        or "other"
    )
    category = CATEGORY_MAP.get(raw_cat, "Wisata Umum")

    return {
        "name"        : name,
        "category"    : category,
        "lat"         : el["lat"],
        "lon"         : el["lon"],
        "open_hour"   : HOURS_MAP[category][0],
        "close_hour"  : HOURS_MAP[category][1],
        "duration_min": DURATION_MAP[category],
        "price_idr"   : PRICE_MAP[category],
        "rating"      : 4.0,           # akan diisi saat preprocessing
        "osm_id"      : el.get("id"),
        "source"      : "OpenStreetMap",
        "raw_tag"     : raw_cat,
    }


def fetch_wisata(kota: str = "Surabaya",
                 save_path: str | None = None) -> pd.DataFrame:
    """
    Fungsi utama: ambil data wisata dari OSM untuk kota tertentu.

    Parameter
    ---------
    kota      : nama kota dalam Bahasa Indonesia (sesuai OSM)
    save_path : path CSV untuk menyimpan raw data (opsional)

    Return
    ------
    DataFrame berisi tempat wisata hasil parsing
    """
    print(f"\n{'='*50}")
    print(f"  OSM Data Collector — Kota: {kota}")
    print(f"{'='*50}")

    query   = _build_overpass_query(kota)
    raw     = _fetch_with_retry(query)
    elems   = raw.get("elements", [])

    print(f"  📦 Total elemen diterima dari OSM: {len(elems)}")

    records = []
    for el in elems:
        parsed = _parse_element(el)
        if parsed:
            records.append(parsed)

    df = pd.DataFrame(records)

    if df.empty:
        print(f"  ⚠️  Tidak ada data valid untuk kota '{kota}'.")
        return df

    # Hapus duplikat nama
    df = df.drop_duplicates(subset=["name"]).reset_index(drop=True)

    print(f"  ✅ Data valid     : {len(df)} tempat wisata")
    print(f"  📂 Kategori       : {df['category'].value_counts().to_dict()}")

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        df.to_csv(save_path, index=False)
        print(f"  💾 Disimpan ke    : {save_path}")

    return df


# ──────────────────────────────────────────────
# JALANKAN LANGSUNG (testing)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    df = fetch_wisata(
        kota="Surabaya",
        save_path="data/raw/wisata_surabaya_raw.csv"
    )
    print("\n📋 Preview 5 baris pertama:")
    print(df.head())
