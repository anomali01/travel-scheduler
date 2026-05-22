# ai/csp_solver.py
"""
Modul AI Scheduling menggunakan Constraint Satisfaction Problem (CSP).
Engine: Google OR-Tools CP-SAT Solver

=======================================================================
KONSEP CSP DALAM TRAVEL SCHEDULING
=======================================================================

CSP didefinisikan sebagai triplet (X, D, C):
  X = Variabel        → setiap tempat wisata kandidat
  D = Domain          → {0=tidak dikunjungi, 1=dikunjungi}
  C = Constraint      → aturan yang harus dipenuhi

VARIABEL:
  visit[i] ∈ {0, 1}   →  1 jika tempat ke-i dikunjungi

CONSTRAINT:
  C1 (Budget)   : Σ price[i] × visit[i] ≤ budget
  C2 (Durasi)   : Σ duration[i] × visit[i] + travel_time ≤ max_jam × 60
  C3 (Jam buka) : open_hour[i] ≤ jam_mulai (hanya kunjungi yang sudah buka)
  C4 (Jam tutup): close_hour[i] ≥ jam_mulai + duration[i] (selesai sebelum tutup)
  C5 (Urutan)   : waktu_selesai[i] + travel_time ≤ waktu_mulai[i+1]

OBJECTIVE (Fungsi Tujuan):
  Maksimalkan : Σ rating[i] × visit[i]

Solver akan mencari kombinasi tempat wisata yang:
  - Memaksimalkan total rating
  - Sambil memenuhi semua constraint di atas
=======================================================================
"""

from __future__ import annotations

import math
import time as time_module
from dataclasses import dataclass

import pandas as pd
from geopy.distance import geodesic
from ortools.sat.python import cp_model
import sys

# Force UTF-8 for standard output streams to prevent UnicodeEncodeError on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ──────────────────────────────────────────────
# DATA CLASS
# ──────────────────────────────────────────────

@dataclass
class ScheduleResult:
    """Hasil output dari CSP Solver."""
    success         : bool
    itinerary       : pd.DataFrame     # tempat terpilih + info jadwal
    total_cost      : int              # total biaya (Rp)
    total_duration  : int              # total durasi (menit)
    total_rating    : float            # total rating akumulasi
    solve_time_ms   : float            # waktu komputasi (ms)
    conflicts       : int              # jumlah konflik jadwal (harus 0)
    solver_status   : str              # status OR-Tools
    message         : str              # pesan untuk user


# ──────────────────────────────────────────────
# HELPER: HITUNG JARAK & WAKTU PERJALANAN
# ──────────────────────────────────────────────

TRAVEL_SPEED_KMH = 30.0   # asumsi kecepatan rata-rata kota (km/jam)
BUFFER_MIN       = 15     # buffer istirahat/perpindahan antar lokasi

def calc_travel_time(lat1: float, lon1: float,
                     lat2: float, lon2: float) -> int:
    """
    Hitung estimasi waktu perjalanan antar dua koordinat (menit).
    Menggunakan jarak geodesic (garis lurus) + kecepatan rata-rata kota.
    """
    dist_km  = geodesic((lat1, lon1), (lat2, lon2)).km
    time_min = (dist_km / TRAVEL_SPEED_KMH) * 60 + BUFFER_MIN
    return max(int(math.ceil(time_min)), BUFFER_MIN)


def build_travel_matrix(df: pd.DataFrame) -> list[list[int]]:
    """
    Bangun matriks waktu perjalanan N×N antar semua tempat wisata.
    travel_matrix[i][j] = menit dari tempat i ke tempat j
    """
    n      = len(df)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = calc_travel_time(
                    df.iloc[i]["lat"], df.iloc[i]["lon"],
                    df.iloc[j]["lat"], df.iloc[j]["lon"]
                )
    return matrix


# ──────────────────────────────────────────────
# GREEDY FALLBACK
# ──────────────────────────────────────────────

def _greedy_fallback(df: pd.DataFrame,
                     budget: int,
                     max_hours: int,
                     start_hour: int) -> pd.DataFrame:
    """
    Algoritma greedy sederhana sebagai fallback jika CSP tidak menemukan solusi.
    Urutan: sort rating tertinggi, tambahkan selama constraint masih terpenuhi.
    Juga digunakan sebagai metode pembanding di paper (Section IV).
    """
    df_sorted    = df.sort_values("rating", ascending=False)
    chosen       = []
    spent_budget = 0
    spent_time   = 0
    max_min      = max_hours * 60

    for _, row in df_sorted.iterrows():
        travel = 15 if not chosen else calc_travel_time(
            chosen[-1]["lat"], chosen[-1]["lon"],
            row["lat"], row["lon"]
        )
        new_time = spent_time + int(row["duration_min"]) + travel
        new_cost = spent_budget + int(row["price_idr"])

        ok_hour  = int(row["open_hour"]) <= start_hour
        ok_close = start_hour * 60 + new_time <= int(row["close_hour"]) * 60

        if new_time <= max_min and new_cost <= budget and ok_hour and ok_close:
            chosen.append(row.to_dict())
            spent_time   = new_time
            spent_budget = new_cost

    return pd.DataFrame(chosen)


# ──────────────────────────────────────────────
# FUNGSI UTAMA: CSP SOLVER
# ──────────────────────────────────────────────

def solve(df_places  : pd.DataFrame,
          budget     : int   = 100_000,
          max_hours  : int   = 8,
          start_hour : int   = 8,
          categories : list[str] | None = None,
          time_limit : float = 10.0) -> ScheduleResult:
    """
    Selesaikan masalah travel scheduling menggunakan CSP.

    Parameter
    ---------
    df_places  : DataFrame tempat wisata (hasil preprocessing)
    budget     : batas budget harian (Rp)
    max_hours  : maksimal jam perjalanan per hari
    start_hour : jam mulai perjalanan (format 24 jam)
    categories : filter kategori wisata (None = semua)
    time_limit : batas waktu solver (detik)

    Return
    ------
    ScheduleResult berisi itinerary & metadata evaluasi
    """

    # ── 1. FILTER DATASET ──────────────────────────────────
    df = df_places.copy()
    if categories:
        df = df[df["category"].isin(categories)]

    # Filter: hanya tempat yang sudah buka saat start_hour
    df = df[df["open_hour"] <= start_hour].reset_index(drop=True)

    n = len(df)
    if n == 0:
        return ScheduleResult(
            success=False, itinerary=pd.DataFrame(),
            total_cost=0, total_duration=0, total_rating=0.0,
            solve_time_ms=0, conflicts=0,
            solver_status="NO_DATA",
            message="Tidak ada tempat wisata yang memenuhi filter."
        )

    # ── 2. BANGUN MATRIKS PERJALANAN ───────────────────────
    travel_matrix = build_travel_matrix(df)

    # ── 3. DEFINISI MODEL CSP ──────────────────────────────
    model    = cp_model.CpModel()
    max_min  = max_hours * 60  # dalam menit

    # Variabel: visit[i] = 1 jika tempat i dikunjungi
    visit = [model.NewBoolVar(f"visit_{i}") for i in range(n)]

    # Rating discale 0-50 (integer, karena OR-Tools hanya integer)
    rating_scaled = [int(df.iloc[i]["rating"] * 10) for i in range(n)]
    durations     = [int(df.iloc[i]["duration_min"]) for i in range(n)]
    prices        = [int(df.iloc[i]["price_idr"])    for i in range(n)]

    # ── CONSTRAINT C1: Budget ──────────────────────────────
    # Σ price[i] × visit[i] ≤ budget
    model.Add(
        sum(prices[i] * visit[i] for i in range(n)) <= budget
    )

    # ── CONSTRAINT C2: Durasi total ────────────────────────
    # Σ duration[i] × visit[i] ≤ max_min
    # (travel time diperkirakan rata-rata 20 menit, dihitung terpisah)
    model.Add(
        sum(durations[i] * visit[i] for i in range(n)) <= max_min
    )

    # ── CONSTRAINT C3: Jam tutup ────────────────────────────
    # Tempat harus selesai dikunjungi sebelum tutup
    for i in range(n):
        close_min  = int(df.iloc[i]["close_hour"]) * 60
        start_min  = start_hour * 60
        # Jika durasi kunjungan melebihi jam tutup, tidak boleh dikunjungi
        if start_min + durations[i] > close_min:
            model.Add(visit[i] == 0)

    # ── CONSTRAINT C4: Minimal 1 tempat ────────────────────
    model.Add(sum(visit[i] for i in range(n)) >= 1)

    # ── OBJECTIVE: Maksimalkan total rating ────────────────
    model.Maximize(
        sum(rating_scaled[i] * visit[i] for i in range(n))
    )

    # ── 4. JALANKAN SOLVER ─────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.log_search_progress = False

    t_start  = time_module.perf_counter()
    status   = solver.Solve(model)
    t_end    = time_module.perf_counter()
    elapsed  = (t_end - t_start) * 1000  # ms

    STATUS_NAMES = {
        cp_model.OPTIMAL  : "OPTIMAL",
        cp_model.FEASIBLE : "FEASIBLE",
        cp_model.INFEASIBLE:"INFEASIBLE",
        cp_model.UNKNOWN  : "UNKNOWN",
    }
    status_str = STATUS_NAMES.get(status, "UNKNOWN")

    # ── 5. FALLBACK KE GREEDY ──────────────────────────────
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        greedy_df = _greedy_fallback(df, budget, max_hours, start_hour)
        if greedy_df.empty:
            return ScheduleResult(
                success=False, itinerary=pd.DataFrame(),
                total_cost=0, total_duration=0, total_rating=0.0,
                solve_time_ms=elapsed, conflicts=0,
                solver_status=status_str,
                message="Tidak ada solusi ditemukan. Coba perlebar budget atau waktu."
            )
        chosen_df  = greedy_df
        status_str = "GREEDY_FALLBACK"
    else:
        chosen_idx = [i for i in range(n) if solver.Value(visit[i]) == 1]
        chosen_df  = df.iloc[chosen_idx].copy().reset_index(drop=True)

    # ── 6. SUSUN JADWAL WAKTU ──────────────────────────────
    chosen_df = _assign_schedule_times(chosen_df, start_hour, travel_matrix,
                                       [df.index.get_loc(i)
                                        if i in df.index else i
                                        for i in chosen_df.index])

    # ── 7. HITUNG METRIK EVALUASI ──────────────────────────
    total_cost     = int(chosen_df["price_idr"].sum())
    total_dur      = int(chosen_df["duration_min"].sum())
    total_rating   = round(float(chosen_df["rating"].sum()), 2)
    conflicts      = _count_conflicts(chosen_df)

    return ScheduleResult(
        success       = True,
        itinerary     = chosen_df,
        total_cost    = total_cost,
        total_duration= total_dur,
        total_rating  = total_rating,
        solve_time_ms = round(elapsed, 2),
        conflicts     = conflicts,
        solver_status = status_str,
        message       = f"Jadwal ditemukan ({status_str}) — {len(chosen_df)} tempat wisata"
    )


def _assign_schedule_times(df      : pd.DataFrame,
                           start_h : int,
                           matrix  : list[list[int]],
                           indices : list[int]) -> pd.DataFrame:
    """
    Tetapkan jam mulai & jam selesai kunjungan secara berurutan,
    dengan mempertimbangkan waktu perjalanan antar lokasi.
    """
    df = df.copy()
    start_times, end_times, travel_times = [], [], []
    current_min = start_h * 60  # menit sejak tengah malam

    for pos, (_, row) in enumerate(df.iterrows()):
        # Waktu perjalanan dari lokasi sebelumnya
        t_travel = 0
        if pos > 0 and len(indices) > pos:
            prev_idx = indices[pos - 1]
            curr_idx = indices[pos]
            if prev_idx < len(matrix) and curr_idx < len(matrix[0]):
                t_travel = matrix[prev_idx][curr_idx]
            else:
                t_travel = BUFFER_MIN
        travel_times.append(t_travel)

        # Jam mulai = jam selesai tempat sebelumnya + waktu perjalanan
        visit_start = current_min + t_travel
        visit_end   = visit_start + int(row["duration_min"])

        start_times.append(_min_to_str(visit_start))
        end_times.append(_min_to_str(visit_end))
        current_min = visit_end

    df["visit_start"]    = start_times
    df["visit_end"]      = end_times
    df["travel_from_prev"] = travel_times
    return df


def _min_to_str(minutes: int) -> str:
    """Konversi menit dari tengah malam ke string 'HH:MM'."""
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def _count_conflicts(df: pd.DataFrame) -> int:
    """
    Hitung jumlah konflik jadwal:
    konflik = kunjungan selesai setelah jam tutup tempat wisata.
    Hasil harus 0 untuk jadwal yang valid.
    """
    conflicts = 0
    for _, row in df.iterrows():
        end_h, end_m = map(int, row["visit_end"].split(":"))
        end_total    = end_h * 60 + end_m
        close_total  = int(row["close_hour"]) * 60
        if end_total > close_total:
            conflicts += 1
    return conflicts


# ──────────────────────────────────────────────
# JALANKAN LANGSUNG (testing)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    # Buat data dummy kecil untuk testing
    import pandas as pd

    dummy = pd.DataFrame([
        {"name": "Taman Bungkul",    "category": "Taman",   "lat": -7.293, "lon": 112.737,
         "open_hour": 6, "close_hour": 21, "duration_min": 90,  "price_idr": 0,     "rating": 4.5},
        {"name": "House of Sampoerna","category": "Museum",  "lat": -7.247, "lon": 112.738,
         "open_hour": 9, "close_hour": 22, "duration_min": 120, "price_idr": 0,     "rating": 4.4},
        {"name": "KBS",              "category": "Hiburan", "lat": -7.287, "lon": 112.734,
         "open_hour": 8, "close_hour": 16, "duration_min": 180, "price_idr": 15000, "rating": 4.2},
        {"name": "Monkasel",         "category": "Museum",  "lat": -7.249, "lon": 112.751,
         "open_hour": 8, "close_hour": 16, "duration_min": 60,  "price_idr": 15000, "rating": 4.3},
        {"name": "Pantai Kenjeran",  "category": "Pantai",  "lat": -7.234, "lon": 112.794,
         "open_hour": 6, "close_hour": 18, "duration_min": 120, "price_idr": 5000,  "rating": 4.0},
    ])

    result = solve(dummy, budget=50000, max_hours=8, start_hour=8)

    print(f"\n{'='*50}")
    print(f"Status  : {result.solver_status}")
    print(f"Pesan   : {result.message}")
    print(f"Biaya   : Rp{result.total_cost:,}")
    print(f"Durasi  : {result.total_duration} menit")
    print(f"Konflik : {result.conflicts}")
    print(f"Waktu   : {result.solve_time_ms} ms")
    print(f"\n📋 Itinerary:")
    print(result.itinerary[["name", "visit_start", "visit_end",
                             "duration_min", "price_idr", "rating"]])
