# data/preprocessing.py
"""
Modul preprocessing dataset wisata.

Tahapan preprocessing yang dilakukan:
  1. Hapus duplikat berdasarkan nama tempat
  2. Hapus data dengan koordinat tidak valid
  3. Isi missing value (median/default)
  4. Validasi jam operasional (open < close)
  5. Normalisasi rating (skala 0–5)
  6. Tambah kolom estimasi rating berbasis kategori & popularitas
  7. Simpan dataset bersih ke CSV

Output akhir digunakan langsung oleh CSP Solver.
"""

import pandas as pd
import numpy as np
import os
import sys

# Force UTF-8 for standard output streams to prevent UnicodeEncodeError on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ──────────────────────────────────────────────
# KONSTANTA
# ──────────────────────────────────────────────

# Batas koordinat seluruh Indonesia (Sabang – Merauke)
LAT_MIN, LAT_MAX = -11.0, 6.0
LON_MIN, LON_MAX = 94.0, 142.0

# Rating default per kategori (estimasi wajar)
RATING_DEFAULT = {
    "Museum"        : 4.2,
    "Hiburan"       : 4.3,
    "Kebun Binatang": 4.1,
    "Taman"         : 4.3,
    "Pantai"        : 4.2,
    "Wisata Alam"   : 4.4,
    "Wisata Umum"   : 4.0,
    "Religi"        : 4.5,
}


def load_raw(filepath: str) -> pd.DataFrame:
    """Baca raw CSV dari hasil OSM collector."""
    df = pd.read_csv(filepath)
    print(f"📂 Raw data dimuat  : {len(df)} baris dari '{filepath}'")
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Hapus baris dengan nama tempat duplikat (case-insensitive)."""
    before = len(df)
    df["_name_lower"] = df["name"].str.lower().str.strip()
    df = df.drop_duplicates(subset=["_name_lower"]).drop(columns=["_name_lower"])
    removed = before - len(df)
    print(f"🧹 Duplikat dihapus : {removed} baris → tersisa {len(df)}")
    return df


def validate_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Hapus baris dengan koordinat di luar bounding box Indonesia."""
    before = len(df)
    mask = (
        df["lat"].between(LAT_MIN, LAT_MAX) &
        df["lon"].between(LON_MIN, LON_MAX)
    )
    df = df[mask].reset_index(drop=True)
    removed = before - len(df)
    print(f"📍 Koordinat invalid: {removed} baris → tersisa {len(df)}")
    return df


def fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Isi nilai kosong dengan default yang masuk akal."""
    # Jam operasional
    df["open_hour"]    = pd.to_numeric(df["open_hour"],    errors="coerce").fillna(8).astype(int)
    df["close_hour"]   = pd.to_numeric(df["close_hour"],   errors="coerce").fillna(17).astype(int)

    # Durasi & harga
    df["duration_min"] = pd.to_numeric(df["duration_min"], errors="coerce").fillna(90).astype(int)
    df["price_idr"]    = pd.to_numeric(df["price_idr"],    errors="coerce").fillna(0).astype(int)

    # Rating: isi dengan default per kategori
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    for cat, default_val in RATING_DEFAULT.items():
        mask = df["rating"].isna() & (df["category"] == cat)
        df.loc[mask, "rating"] = default_val
    df["rating"] = df["rating"].fillna(4.0)

    print(f"🔧 Missing values diisi")
    return df


def validate_hours(df: pd.DataFrame) -> pd.DataFrame:
    """Hapus baris di mana jam buka >= jam tutup (tidak valid)."""
    before = len(df)
    df = df[df["open_hour"] < df["close_hour"]].reset_index(drop=True)
    removed = before - len(df)
    print(f"⏰ Jam tidak valid  : {removed} baris → tersisa {len(df)}")
    return df


def add_computed_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tambah kolom turunan yang dibutuhkan CSP Solver:
    - duration_slot : durasi dalam satuan slot 30 menit
    - is_free       : boolean, apakah tiket gratis
    """
    df["duration_slot"] = np.ceil(df["duration_min"] / 30).astype(int)
    df["is_free"]       = (df["price_idr"] == 0).astype(int)
    return df


def generate_report(df_raw: pd.DataFrame,
                    df_clean: pd.DataFrame) -> dict:
    """Buat laporan ringkas untuk ditampilkan di paper."""
    report = {
        "raw_total"         : len(df_raw),
        "clean_total"       : len(df_clean),
        "removed_total"     : len(df_raw) - len(df_clean),
        "missing_before"    : int(df_raw.isnull().sum().sum()),
        "missing_after"     : int(df_clean.isnull().sum().sum()),
        "category_dist"     : df_clean["category"].value_counts().to_dict(),
        "avg_rating"        : round(df_clean["rating"].mean(), 2),
        "avg_price"         : round(df_clean["price_idr"].mean(), 0),
        "attributes"        : list(df_clean.columns),
    }
    return report


def preprocess(raw_path: str,
               clean_path: str | None = None) -> pd.DataFrame:
    """
    Pipeline preprocessing lengkap.

    Parameter
    ---------
    raw_path   : path ke file CSV raw dari OSM collector
    clean_path : path untuk menyimpan hasil preprocessing

    Return
    ------
    DataFrame bersih siap digunakan CSP Solver
    """
    print(f"\n{'='*50}")
    print("  PREPROCESSING PIPELINE")
    print(f"{'='*50}")

    df_raw   = load_raw(raw_path)
    df       = df_raw.copy()

    df       = remove_duplicates(df)
    df       = validate_coordinates(df)
    df       = fill_missing_values(df)
    df       = validate_hours(df)
    df       = add_computed_columns(df)

    # Reset index final
    df = df.reset_index(drop=True)
    df["id"] = df.index  # ID numerik untuk solver

    report = generate_report(df_raw, df)

    print(f"\n📊 LAPORAN PREPROCESSING")
    print(f"  Data awal     : {report['raw_total']} records")
    print(f"  Data bersih   : {report['clean_total']} records")
    print(f"  Dihapus       : {report['removed_total']} records")
    print(f"  Missing (awal): {report['missing_before']}")
    print(f"  Missing (akhir): {report['missing_after']}")
    print(f"  Distribusi    : {report['category_dist']}")
    print(f"  Rata-rata rating : {report['avg_rating']}")
    print(f"  Atribut final : {report['attributes']}")

    if clean_path:
        os.makedirs(os.path.dirname(clean_path), exist_ok=True)
        df.to_csv(clean_path, index=False)
        print(f"\n  💾 Disimpan ke: {clean_path}")

    return df


# ──────────────────────────────────────────────
# JALANKAN LANGSUNG
# ──────────────────────────────────────────────
if __name__ == "__main__":
    df_clean = preprocess(
        raw_path   = "data/raw/wisata_surabaya_raw.csv",
        clean_path = "data/processed/wisata_surabaya_clean.csv"
    )
    print("\n📋 Preview:")
    print(df_clean[["name", "category", "open_hour",
                     "close_hour", "duration_min",
                     "price_idr", "rating"]].head(10))
